# 论文 PDF profile

触发：arXiv / ACL Anthology / OpenReview / HuggingFace Papers 链接，或纯文字论文标题。入库 Zotero → obsidian-research skill。

## venue URL 模式

| 来源 | 可用模式 | 备注 |
|---|---|---|
| arXiv | `arxiv.org/abs/<id>` → `arxiv.org/pdf/<id>` | curl 直下 |
| ACL Anthology | `aclanthology.org/<year>.<conf>-long.<n>/` 拼 `.pdf` | |
| OpenReview | `openreview.net/pdf?id=<id>` | curl 403（Cloudflare）→ 走下节 |
| HuggingFace | `huggingface.co/papers/<arxiv-id>` | `<arxiv-id>` 即 arXiv 号 |

**代理方向**：arXiv/B站直连，OpenReview/HF API/GitHub API 走 7897。（详见 memory）

## OpenReview 403 破解

OpenReview 有 Cloudflare challenge：curl/pdf/attachment 全 403，Referer/Origin 无效。**唯一可行路径：opencli 真实浏览器会话过 challenge → 页面上下文 fetch → 分块 base64 取回。**

```bash
# 1. 打开 pdf 页（真实 Chrome 能过 challenge）
opencli browser tmp open "https://openreview.net/pdf?id=<ID>" --window background
sleep 6   # 等 challenge 自动过 + PDF 加载

# 2. 页面上下文 fetch 存 window 变量（期望 stored:<bytes>；ERR: = session 挂了重开）
opencli browser tmp eval --window background \
  'fetch("https://openreview.net/pdf?id=<ID>").then(r=>r.arrayBuffer()).then(b=>{window.__pdf=new Uint8Array(b);return "stored:"+b.byteLength;}).catch(e=>"ERR:"+e.message)' \
  2>&1 | tail -1

# 3. 分块取回（每块 ~530KB，整块 2.8MB 超 eval 输出限制；块数 Math.ceil(len/530000) 按实际算）
#    每块 JS：subarray + 8192 步进 String.fromCharCode + btoa，JSON.stringify({i,n,d}) 返回
#    输出 2>&1 | tail -1 只取最后一行 JSON（node UNDICI 警告行污染），python 解出 d 拼成 chunk_N.b64

# 4. 拼装 + 校验
cat chunk_*.b64 | base64 -d > paper.pdf
head -c 5 paper.pdf | od -c    # 期望 %PDF-；<50KB 是错误页
strings paper.pdf | grep -oE '/Title \(.*\)'   # 核对内嵌标题防串篇
```

批量：每篇重新 open pdf 页（上下文刷新后 `window.__pdf` 清空），challenge cookie 会话内持续有效后续直接过。元数据先试 API，403 就直接走浏览器。

## 无链接论文定位

1. 从正文提取独特框架名/方法名 → arXiv API `ti:"..."`（拿标题 `grep -oE "<title>[^<]*</title>"`，第一条是查询本身）
2. API 限流 → web_search 拿 ID → `arxiv.org/abs/<id>` 验证标题（abs 页不受限）→ `/pdf/<id>` 下载
3. 会议论文（ICML/ICLR/AAAI）arXiv 常未收录 → OpenReview 是主战场（API 先试，403 走浏览器）→ Google/Bing 兜底
4. 对不上标"未定位"

## 校验铁律

- `head -c 5 file.pdf | od -c` = `%PDF-`；<50KB 基本是错误页
- arXiv ID 一律入库前 API `id_list` 核对真实标题（文件名里的号可能被 OCR/vision 读错）
- arXiv 元数据走 curl 直连
- OpenReview 论文（无 arXiv 号）手动建 meta 字典，作者列表以 API 为准（比手抄全）
- PDF 文件名：`论文名-会议年份-arxivXXXX.XXXXX.pdf`（后缀供导入脚本识别），存 `webclip/pdfs/`，md 里 `[[pdfs/xxx.pdf]]` 引用
