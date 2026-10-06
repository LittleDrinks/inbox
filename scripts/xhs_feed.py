#!/usr/bin/env python3
"""
xhs-feed: 小红书链接 → webclip md 的一键流水线
用法: python3 xhs_feed.py <url_or_shortcode> [--outdir DIR] [--download-images] [--transcribe]

实现笔记（踩坑记录，换实现时参考）:
- xsec_token 与 noteId 严格一对一绑定，跨笔记借用触发 SECURITY_BLOCK
- 短链 HTML 内嵌完整 noteData，双层转义（\\\\ → \\，\\uXXXX → 字符）
- token 有两种写法：CB...= 和 CB...%3D，喂 opencli 时 = 编码成 %3D
- title 紧跟在 "noteId":"<nid>" 之后 300 字符内取，之前出现的是推荐位
- opencli note 必须加 --trace retain-on-failure，否则报 Navigation rejected
- opencli title 偶发抓错，以 curl HTML 的 title 为准
- desc 用 json.loads(f'"{raw}"') 解，不要用 unicode_escape（会 mojibake）
- 连续 curl 16+ 条触发登录页（HTML <20k），每 3-5 条 sleep 0.5-1s
- masterUrl 是双层转义，直接字符串替换 \\\\u002F→/
- 图片 URL 结尾 !h5_1080jpg 后缀要保留，漏掉 curl 到 0 字节
- curl 图片必带 -e "https://www.xiaohongshu.com/"
- 签名 URL 会过期，ThreadPoolExecutor(4) + --max-time 20
- 无音轨视频 ffmpeg 抽音频报错属正常（BGM-only/纯图轮播），跳过
"""
import re, json, sys, os, subprocess, time
from pathlib import Path
from urllib.parse import unquote

UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
INBOX = os.environ.get("INBOX_DIR", "/mnt/e/OBSIDIAN/inbox")

def log(msg):
    print(f"[xhs-feed] {msg}", file=sys.stderr)

def resolve_url(raw: str) -> tuple[str, str]:
    """输入任意形态（短链/长链/noteId），返回 (noteId, 完整带token的explore URL)"""
    raw = raw.strip()
    # 裸 noteId
    if re.fullmatch(r'[0-9a-f]{24}', raw):
        return raw, ""
    # 短链
    m = re.search(r'xhslink\.c[n|om]/o/(\w+)', raw)
    if m:
        code = m.group(1)
        html = curl(f"http://xhslink.cn/o/{code}")
        nid = extract_field(html, r'"noteId\\?":\\?"([0-9a-f]{24})')
        token = extract_token(html)
        return nid, build_url(nid, token)
    # 长链
    m = re.search(r'(?:explore|search_result)/([0-9a-f]{24})', raw)
    if m:
        nid = m.group(1)
        token = extract_token(raw)
        return nid, build_url(nid, token)
    raise ValueError(f"无法识别的输入: {raw}")

def curl(url: str, referer: str = None) -> str:
    cmd = ["curl", "-sL", "-A", UA, "--max-time", "20"]
    if referer:
        cmd += ["-e", referer]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout

def extract_field(html: str, pattern: str) -> str:
    """从双层转义的 HTML 中提取字段"""
    # 先解一层转义
    raw = html.replace("\\\\u002F", "/").replace("\\u002F", "/")
    raw = raw.replace("\\\\", "\\")
    m = re.search(pattern, raw)
    if m:
        val = m.group(1)
        # 解 unicode 转义
        try:
            val = json.loads(f'"{val}"')
        except:
            pass
        return val
    return ""

def extract_token(text: str) -> str:
    m = re.search(r'xsec_token=([A-Za-z0-9_%-]+)', text)
    if m:
        return m.group(1).replace("=", "%3D")  # URL-encode trailing =
    return ""

def build_url(nid: str, token: str) -> str:
    if token:
        return f"https://www.xiaohongshu.com/explore/{nid}?xsec_token={token}&xsec_source=app_share"
    return f"https://www.xiaohongshu.com/explore/{nid}"

def fetch_via_html(short_code: str) -> dict:
    """路径1: curl 短链 HTML 直取"""
    html = curl(f"http://xhslink.cn/o/{short_code}")
    if len(html) < 20000:
        log("⚠️ HTML 过短，可能触发风控")
        return {}
    
    raw = html.replace("\\\\u002F", "/").replace("\\u002F", "/")
    
    # title: noteId 后 300 字符内
    nid_m = re.search(r'"noteId\\?":\\?"([0-9a-f]{24})', raw)
    nid = nid_m.group(1) if nid_m else ""
    title = ""
    if nid:
        idx = raw.find(nid)
        snippet = raw[idx:idx+300]
        t = re.search(r'"title\\?":\\?"([^"\\]+)', snippet)
        if t:
            title = t.group(1)
    
    # desc
    desc = extract_field(html, r'"desc\\?":\\?"((?:[^"\\]|\\.)*)"')
    
    # images
    images = list(dict.fromkeys(re.findall(
        r'http://sns-webpic-qc\.xhscdn\.com/[^"\\]*', raw
    )))
    images = [u for u in images if len(u) > 10]
    
    # video
    video_url = extract_field(html, r'"masterUrl\\?":\\?"([^"\\]+)"')
    
    # author
    author = extract_field(html, r'"nickname\\?":\\?"([^"\\]+)"')
    
    return {
        "nid": nid,
        "title": title,
        "desc": desc,
        "author": author,
        "images": images,
        "video_url": video_url,
        "html_len": len(html),
    }

def fetch_via_opencli(url: str) -> dict:
    """路径2: opencli note 兜底"""
    try:
        r = subprocess.run(
            ["opencli", "xiaohongshu", "note", url, "--window", "background", "-f", "json", "--trace", "retain-on-failure"],
            capture_output=True, text=True, timeout=60
        )
        if r.returncode == 0 and r.stdout.strip():
            data = json.loads(r.stdout)
            if isinstance(data, list):
                return {x.get("field",""): x.get("value","") for x in data if isinstance(x, dict)}
            return data
    except Exception as e:
        log(f"opencli 失败: {e}")
    return {}

def write_webclip(data: dict, url: str, outdir: str = None) -> str:
    """生成 webclip md"""
    nid = data.get("nid", "unknown")
    title = data.get("title", "无标题")
    desc = data.get("desc", "")
    author = data.get("author", data.get("nickname", ""))
    
    # 清理标题
    title = re.sub(r'[\\/:*?"<>|]', '', title)[:50]
    
    today = time.strftime("%Y-%m-%d")
    filename = f"{today}-webclip-小红书-{title}.md"
    out = Path(outdir or INBOX) / "webclip" / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    
    # 防冲突
    v = 2
    while out.exists():
        out = out.parent / f"{today}-webclip-小红书-{title}-v{v}.md"
        v += 1
    
    content = f"""#status/todo

---
date: {today}
source: 小红书 / {author}
url: {url}
type: 图文笔记
title: "{title}"
---

{desc}
"""
    
    if data.get("images"):
        content += f"\n## 图片（{len(data['images'])} 张）\n\n"
        for i, img in enumerate(data["images"], 1):
            content += f"{i}. {img}\n"
    
    if data.get("video_url"):
        content += f"\n## 视频\n\n{data['video_url']}\n"
    
    out.write_text(content, encoding="utf-8")
    log(f"✓ 写入 {out}")
    return str(out)

def main():
    if len(sys.argv) < 2:
        print("用法: python3 xhs_feed.py <url_or_shortcode> [--outdir DIR]")
        sys.exit(1)
    
    raw = sys.argv[1]
    outdir = None
    if "--outdir" in sys.argv:
        outdir = sys.argv[sys.argv.index("--outdir") + 1]
    
    log(f"解析: {raw}")
    nid, url = resolve_url(raw)
    log(f"noteId: {nid}")
    log(f"URL: {url}")
    
    # 优先 curl HTML
    code_m = re.search(r'xhslink\.c[n|om]/o/(\w+)', raw)
    data = {}
    if code_m:
        log("路径1: curl 短链 HTML")
        data = fetch_via_html(code_m.group(1))
    
    # 兜底 opencli
    if not data.get("title") and url:
        log("路径2: opencli note")
        cli_data = fetch_via_opencli(url)
        # 合并，HTML 优先
        for k, v in cli_data.items():
            if k not in data or not data[k]:
                data[k] = v
    
    if not data.get("nid"):
        data["nid"] = nid
    
    if not data.get("title") and not data.get("desc"):
        log("✗ 两条路径都没拿到内容")
        sys.exit(1)
    
    path = write_webclip(data, url or raw, outdir)
    print(path)  # stdout 输出文件路径

if __name__ == "__main__":
    main()
