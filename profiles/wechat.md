# 微信公众号 profile

触发：`mp.weixin.qq.com/s/`。识别出论文 → 叠加 paper-pdf profile。

## 主路（2026-09-17 起，curl 直抓已失效）

文章页改 JS 渲染，curl 拿到 3MB JS 外壳（换 UA 也一样）。可用路径是复用用户 Chrome 会话的 opencli，**必须关图片下载**：

```bash
opencli weixin download --url "https://mp.weixin.qq.com/s/<id>" \
  --output ~/.cache/<项目>/wxdl --download-images false --window background -f json
```

输出 `{title, author, publish_time, status, size, saved}`，`saved` 是现成 md 路径。「点击下方原文」是平台话术，引用以提取出的纯 URL 为准。

## 备用：curl 直抓（旧格式文章仍可用）

```bash
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36" \
  "https://mp.weixin.qq.com/s/<id>" -o /tmp/wx/<id>.html
```

HTML 要点（2026 实测）：整页 2-4MB，图片 base64 内嵌；标题 `<h1 id="activity-name">`；正文 `<div id="js_content">`。

## 解析骨架（curl 路径用）

```python
import re, html
def parse(path):
    raw = open(path, encoding='utf-8', errors='ignore').read()
    title = re.search(r'<h1[^>]*id="activity-name"[^>]*>(.*?)</h1>', raw, re.S)
    title = html.unescape(re.sub(r'<[^>]+>', '', title.group(1))).strip() if title else ''
    nick = (re.search(r'var nickname\s*=\s*htmlDecode\("(.*?)"\)', raw)
            or re.search(r"var nickname\s*=\s*['\"](.*?)['\"]", raw))   # 新文 htmlDecode 包裹，老文裸引号
    content = re.search(r'id="js_content"[^>]*>(.*?)</div>\s*<script', raw, re.S)
    s = content.group(1) if content else ''
    s = re.sub(r'<script.*?</script>|<style.*?</style>', '', s, flags=re.S)
    s = re.sub(r'<img[^>]+data-src="(https:[^"]+)"[^>]*>', r'\n![img](\1)\n', s)  # data-src 懒加载才是真 URL，src 是占位符
    s = re.sub(r'<(p|section|div|br|li|h\d|blockquote)[^>]*>', '\n', s)
    s = html.unescape(re.sub(r'<[^>]+>', '', s))
    body = '\n'.join(ln.strip() for ln in s.split('\n') if ln.strip())
    urls = re.findall(r'https?://[^\s<>"\'）)】\]]+', body)   # 链接是纯文本不是 <a>
    return {'title': title, 'account': nick.group(1) if nick else '', 'body': body, 'urls': urls}
```

- `</div>\s*<script` 结尾锚点必须带，否则贪婪吞全页
- **OpenReview 链接被换行截断**（`pdf?` + `id` + `=XXX` 三截）：原始 HTML 上正则 `https://openreview\.net/pdf\?.*?id.*?=([A-Za-z0-9]{8,14})` 跨标签恢复；综述类每篇独立 ID，按出现顺序与论文序号对齐
- 长文（1.2 万字符级）全文写进 md；串行下载 `time.sleep(1)` 即可，微信不封 curl
