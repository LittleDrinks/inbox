#!/usr/bin/env python3
"""
Ego-Lite 原生驱动的 Inbox 抓取脚本。
替代原有脆弱的扩展桥接模式，直接通过 Windows Ego-Lite 原生 Chromium 内核与 CDP 上下文抓取。
"""

import sys
import json
import os
import subprocess
import time
from pathlib import Path

EGO_BIN = "/mnt/c/Program Files/Citro Labs/ego lite/Application/0.6.0.16/ego-browser.exe"

def run_ego_fetch(mode: str, url: str, options: dict = None) -> dict:
    if options is None:
        options = {}

    pid = os.getpid()
    win_temp = Path("/mnt/c/Users/q2635/AppData/Local/Temp")
    payload_file = win_temp / f"ego_p_{pid}.json"
    output_file = win_temp / f"ego_o_{pid}.json"

    win_payload_path = f"C:/Users/q2635/AppData/Local/Temp/{payload_file.name}"
    win_output_path = f"C:/Users/q2635/AppData/Local/Temp/{output_file.name}"

    payload = {
        "mode": mode,
        "url": url,
        "options": options
    }

    # 动态生成包含固定路径的执行脚本，规避 Windows 环境变量传递丢失
    script_content = f"""
import {{ readFileSync, writeFileSync }} from 'node:fs';

const payloadPath = '{win_payload_path}';
const outputPath = '{win_output_path}';

let config = {{}};
try {{
  config = JSON.parse(readFileSync(payloadPath, 'utf8'));
}} catch (e) {{
  writeFileSync(outputPath, JSON.stringify({{ ok: false, error: 'Read payload failed: ' + e.message }}), 'utf8');
  process.exit(1);
}}

const {{ mode, url, options = {{}} }} = config;
const task = await taskSpace(`inbox-${{mode}}-${{Date.now()}}`);
const page = task.page("p1");

try {{
  await page.goto(url);
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(3000);

  let data = {{}};

  if (mode === 'xhs') {{
    if (options.withComments) {{
      for (let i = 0; i < (options.commentScrolls || 3); i++) {{
        await page.evaluate(() => window.scrollBy(0, 1000));
        await page.waitForTimeout(1000);
      }}
    }}

    data = await page.evaluate((withComments) => {{
      const state = window.__INITIAL_STATE__;
      const noteMap = state?.note?.noteDetailMap || {{}};
      const firstKey = Object.keys(noteMap)[0];
      const note = noteMap[firstKey]?.note;

      const title = note?.title || document.querySelector('#detail-title, .title')?.innerText || document.title;
      const desc = note?.desc || document.querySelector('#detail-desc, .desc')?.innerText || '';
      const author = note?.user?.nickname || document.querySelector('.author-wrapper .name')?.innerText || '';
      const time = note?.time ? new Date(note.time).toISOString() : (document.querySelector('.date')?.innerText || '');

      const images = (note?.imageList || []).map(img => img.urlDefault || img.url);

      let videoUrls = [];
      if (note?.video) {{
        const stream = note.video.media?.stream || {{}};
        for (const codec of Object.keys(stream)) {{
          for (const item of (stream[codec] || [])) {{
            if (item.masterUrl) {{
              videoUrls.push({{
                format: item.format,
                quality: item.qualityType || item.streamDesc,
                url: item.masterUrl
              }});
            }}
          }}
        }}
      }}

      let comments = [];
      if (withComments) {{
        const commentItems = document.querySelectorAll('.comment-item, [class*="comment-item"]');
        commentItems.forEach(el => {{
          const cAuthor = el.querySelector('.author, .user-name, [class*="author"], [class*="name"]')?.innerText?.trim();
          const cContent = el.querySelector('.content, .note-text, [class*="content"]')?.innerText?.trim();
          const cDate = el.querySelector('.date, [class*="date"]')?.innerText?.trim();
          const cLike = el.querySelector('.like, [class*="like"]')?.innerText?.trim();
          if (cContent && !comments.some(item => item.content === cContent && item.author === cAuthor)) {{
            comments.push({{ author: cAuthor, content: cContent, date: cDate, like: cLike }});
          }}
        }});
      }}

      return {{
        type: videoUrls.length > 0 ? 'video' : 'normal',
        title,
        author,
        desc,
        time,
        images,
        videoUrls,
        comments
      }};
    }}, Boolean(options.withComments));

  }} else if (mode === 'wechat') {{
    data = await page.evaluate(() => {{
      const title = document.querySelector('#activity-name')?.innerText?.trim() || document.title;
      const author = document.querySelector('#js_name')?.innerText?.trim() || '';
      const date = document.querySelector('#publish_time')?.innerText?.trim() || '';
      const contentEl = document.querySelector('#js_content');
      const content = contentEl ? contentEl.innerText?.trim() : '';
      const images = Array.from(document.querySelectorAll('#js_content img[data-src]')).map(img => img.getAttribute('data-src'));

      return {{
        title,
        author,
        date,
        content,
        images
      }};
    }});

  }} else if (mode === 'bilibili') {{
    data = await page.evaluate(() => {{
      const playinfo = window.__playinfo__;
      const initialState = window.__INITIAL_STATE__;
      const title = initialState?.videoData?.title || document.title;
      const desc = initialState?.videoData?.desc || '';
      const audioStreams = playinfo?.data?.dash?.audio || [];
      const videoStreams = playinfo?.data?.dash?.video || [];

      return {{
        title,
        desc,
        duration: initialState?.videoData?.duration,
        audioStreams: audioStreams.map(a => ({{ id: a.id, bandwidth: a.bandwidth, baseUrl: a.baseUrl }})),
        videoStreams: videoStreams.map(v => ({{ id: v.id, bandwidth: v.bandwidth, baseUrl: v.baseUrl }}))
      }};
    }});
  }}

  writeFileSync(outputPath, JSON.stringify({{ ok: true, data }}, null, 2), 'utf8');
}} catch (err) {{
  writeFileSync(outputPath, JSON.stringify({{ ok: false, error: err.message }}), 'utf8');
}} finally {{
  await completeTaskSpace(task.spaceId, {{ keep: false }});
}}
"""

    script_file = win_temp / f"ego_run_{pid}.mjs"
    try:
        payload_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        script_file.write_text(script_content, encoding="utf-8")

        cmd = [EGO_BIN, "nodejs"]
        with open(script_file, "rb") as f_in:
            proc = subprocess.run(
                cmd,
                stdin=f_in,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120
            )

        if not output_file.exists():
            return {"ok": False, "error": f"Output file not generated. stderr: {proc.stderr}"}

        res = json.loads(output_file.read_text(encoding="utf-8"))
        return res
    finally:
        for f in [payload_file, script_file, output_file]:
            if f.exists():
                try:
                    f.unlink()
                except Exception:
                    pass

def main():
    if len(sys.argv) < 3:
        print("Usage: ego_inbox.py <xhs|wechat|bilibili> <url> [--comments]")
        sys.exit(1)

    mode = sys.argv[1]
    url = sys.argv[2]
    with_comments = "--comments" in sys.argv

    print(f"[*] 启动 Ego-Lite 原生引擎抓取: [{mode}] {url} ...")
    res = run_ego_fetch(mode, url, {"withComments": with_comments})

    if not res.get("ok"):
        print(f"[!] 抓取失败: {res.get('error')}", file=sys.stderr)
        sys.exit(1)

    data = res["data"]
    print(json.dumps(data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
