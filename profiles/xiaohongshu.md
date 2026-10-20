# 小红书收藏

小红书分享文字、短链或带签名链接统一交给 `scripts/ego_inbox.py xhs <URL>`，使用 Windows 宿主原生的 Ego-Lite 引擎（TaskSpace 隔离运行）。

## 调用

从本 Skill 目录执行，环境要求：WSL 访问宿主 `/mnt/c/Program Files/Citro Labs/ego lite/Application/0.6.0.16/ego-browser.exe`。

```bash
# 1. 抓取小红书笔记（支持图文正文、高清大图、多码率原画视频 URL）
python3 scripts/ego_inbox.py xhs "<URL>"

# 2. 如果需要抓取评论层（如精选技巧、一手链接贴）
python3 scripts/ego_inbox.py xhs "<URL>" --comments
```

输出标准 JSON 结构：
- `type`: `normal` (图文) 或 `video` (视频)
- `title`: 笔记标题
- `author`: 发布者昵称
- `desc`: 完整笔记正文内容（带话题与排版）
- `images`: 高清原图直链数组
- `videoUrls`: 包含多种分辨率与编码（EF4/EF5 等、720P/1080P/2K）且已带签名的 CDN 直链 `masterUrl`
- `comments`: 评论列表数组（含作者、评论正文、发布时间及 IP 属地、点赞数）

## 媒体下载

- **视频原画**：直接利用提取出的 `videoUrls[].url` 下载（支持 curl 或 Python 直连，无需附带 Cookie，仅需原生 CDN 签名）。
- **图片**：直接并发拉取 `images` 数组中的 WebP/JPG 资源。

## 结果与归档

- 采集完成后输出 JSON 结果；若指定 `--out-dir`，脚本自动将笔记正文与提取的评论保存为 `note.json`，并自动下载最高画质视频 `video.mp4` 与全套高清图片。
- 视频有讲话内容则按 `video.md` 走本地语音转写；图文按 `image.md` 提取有效视觉/配色信息。
- 提取失败或页面受限时直接报错退出，不生成虚假或损坏数据。

## 内容消化

- 正文已自足就保留信息，核实其中要采用的一手链接。区分正文声称、媒体实际展示、评论补充和推断。
- 图文按 `image.md` 处理本地图片；覆盖内容图，说明跳过的封面、装饰和重复图。配色保留名称、HEX 和用途，模糊值标存疑。
- 视频按 `video.md` 处理实际下载文件；有讲话则转录，有独立画面信息则抽帧。无音轨或仅配乐记录依据；长录音分段后台处理。缺少视频时保留待补，正文或封面不能冒充视频内容。
- 评论是否需要抓遵循 inbox 主规则。需要时在执行 `ego_inbox.py` 时传入 `--comments` 标志，直接解析评论数组并保存。记录顶层评论限额、是否包含回复和覆盖范围；未抓、失败和成功零条分开说明。
- 发现论文时叠加 `paper-pdf.md`，PDF 入 Zotero。GitHub 等一手链接采用前核验；配色、prompt 等按主规则内联。digest 与原料清理遵循 inbox 主规则。

## 维护

统一维护 `scripts/ego_inbox.py`。页面解析、图片/视频下载和评论获取直接通过 Windows 宿主 Ego-Lite 原生引擎处理，不再维护逆向 API 抓取后端。真实采集失败应报告真实错误，不扩大为已完整取得。
