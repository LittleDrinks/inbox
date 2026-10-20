# 小红书收藏

小红书分享文字、短链或带签名链接统一交给 `scripts/ego_inbox.py xhs <URL>`。已弃用原有脆弱的 OpenCLI 桥接模式，全面使用 Windows 宿主原生的 **Ego-Lite 独立 Chromium 引擎**（TaskSpace 隔离运行，自动穿透设备指纹与风控验证）。

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

## 结果与失败

- stdout 是计数、状态文件和 Markdown 路径的 JSON。`state.json` 为批次记录，`clips/<noteId>.md` 为原料；正文和媒体在 `attempt-*` 中。成功只表示请求范围内的采集完成，不表示读图、转录或消化完成。
- 笔记 ID 来自输入链接，用于归档与去重，不声称独立核验网站身份。官方正文输出无需 noteId 补丁。
- 下载必须与 OpenCLI 返回清单对应，并通过文件签名和 ffmpeg 完整解码。HTML、空文件、损坏媒体不算成功。正文已取得但媒体失败时保留 partial 原料，说明缺失。
- `status` / `resume` 对新下载的媒体只检查文件存在与大小，不重读内容；Markdown 和正文 JSON 保留哈希检查，旧版仅有哈希的媒体记录沿用原检查。大小未变的后续媒体损坏不在检查范围内。`resume` 跳过检查通过的完整笔记，其余整篇重试；旧 attempt 保留，不复用失败媒体，不做字节续传。人工修改的 Markdown 保留并报冲突；已有批次不能用 capture 覆盖。
- `status` 只检查本地文件，不启动浏览器。旧 schema=1 批次保持原样，重新采集使用新目录，不自动迁移或删除旧文件。
- 退出码：0 请求范围内完成；1 部分失败、无效输入或文件缺失/变化；2 参数、路径或状态错误；3 需要用户处理浏览器、登录或风控。
- Bridge 断连且 Windows Chrome 没运行时，脚本启动正常 Chrome 一次，最多等 20 秒确认连接再重试。Chrome 已运行却断连、登录失效或风控时交用户处理。采集继续使用上游 OpenCLI，不另起浏览器抓取或 curl 媒体兜底。

## 内容消化

- 正文已自足就保留信息，核实其中要采用的一手链接。区分正文声称、媒体实际展示、评论补充和推断。
- 图文按 `image.md` 处理本地图片；覆盖内容图，说明跳过的封面、装饰和重复图。配色保留名称、HEX 和用途，模糊值标存疑。
- 视频按 `video.md` 处理实际下载文件；有讲话则转录，有独立画面信息则抽帧。无音轨或仅配乐记录依据；长录音分段后台处理。缺少视频时保留待补，正文或封面不能冒充视频内容。
- 评论是否需要抓遵循 inbox 主规则。需要时在执行 `ego_inbox.py` 时传入 `--comments` 标志，直接解析评论数组并保存。记录顶层评论限额、是否包含回复和覆盖范围；未抓、失败和成功零条分开说明。
- 发现论文时叠加 `paper-pdf.md`，PDF 入 Zotero。GitHub 等一手链接采用前核验；配色、prompt 等按主规则内联。digest 与原料清理遵循 inbox 主规则。

## 维护

统一维护 `scripts/ego_inbox.py`。页面解析、图片/视频下载和评论获取直接通过 Windows 宿主 Ego-Lite 原生引擎处理，不再维护逆向 API 抓取后端。真实采集失败应报告真实错误，不扩大为已完整取得。
