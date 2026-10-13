# 小红书收藏

小红书分享文字、短链或带签名链接统一交给 `scripts/xhs_feed.py`。它调用上游 OpenCLI 获取正文与媒体，负责批量归档和文件检查；内容消化交给 agent。

## 调用

从本 Skill 目录执行，使用 Python 3.11+、OpenCLI、ffmpeg。新批次必须在 `$INBOX_DIR/webclip/` 下，默认 INBOX_DIR 为 `/mnt/e/OBSIDIAN/inbox`。CLI 读取进程环境，不自动加载 .env。

```bash
python scripts/xhs_feed.py capture --input <分享文字.txt> --run-dir <inbox/webclip/新批次>
python scripts/xhs_feed.py status --run-dir <批次>
python scripts/xhs_feed.py resume --run-dir <批次>
```

`--input -` 从标准输入读分享文字。默认下载图片和视频；仅需正文时加 `--media skip`，交付时注明未抓媒体。paste 引用按用户指定范围追踪，原样保留签名参数；裸 noteId 不够，须提供完整签名 URL。短链只允许受限域名的 HTTP 重定向，不解析 HTML。

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
- 评论是否需要抓遵循 inbox 主规则。需要时先查 `opencli xiaohongshu comments --help`，调用上游 comments，将 JSON 保存到批次目录。记录顶层评论限额、是否包含回复和覆盖范围；未抓、失败和成功零条分开说明。采集脚本不提供评论占位命令。
- 发现论文时叠加 `paper-pdf.md`，PDF 入 Zotero。GitHub 等一手链接采用前核验；配色、prompt 等按主规则内联。digest 与原料清理遵循 inbox 主规则。

## 维护

只维护一个脚本 `scripts/xhs_feed.py`。页面解析、图片/视频下载和评论获取复用上游 OpenCLI；不维护平行抓取后端。修复先补 CLI 行为测试：`python -B -m unittest discover -s tests -v`。离线测试不证明网站当前可用；真实采集失败应报告真实错误，不扩大为已完整取得。
