# X / Twitter profile

触发：`x.com/<user>/status/<id>`、`twitter.com/...`。
用户指定 opencli 时优先使用 OpenCLI；先加载 opencli-usage，检查 doctor 和子命令 --help，不先假定 x-cli 已安装。

```bash
opencli twitter thread '<帖子URL>' -f json
opencli twitter download --tweet-url '<帖子URL>' --output '<绝对目录>' -f json
```

- thread 是有限回复，不代表全量评论。stdout 可能夹警告或更新通知，捕获后用 JSONDecoder.raw_decode 解析，不直接 json.load 原始输出。
- 长视频下载明确指定目录，background+notify 执行；必要时提高 OPENCLI_BROWSER_COMMAND_TIMEOUT。超时也可能已落盘，核对文件、ffprobe 音轨/时长，并抽帧确认目标内容，不凭日志宣称成功。
- 文案数字与视频标题页冲突时分别保留。OpenCLI Chrome 与 browser_exec 登录态不混同。

x-cli 已安装且用户明确选择时，按 `x-cli --help` 使用官方 API；默认继续使用 OpenCLI。

```bash
x-cli tweet get <post_url_or_id>      # 读单条帖（接受完整 URL，自动提取 ID）
x-cli user get <handle>               # 用户信息
x-cli tweet search "关键词" --max 10   # 搜帖
```

- 图片媒体：X API v2 expansions 取 URL（`/2/tweets/<id>?expansions=attachments.media_keys`）
- 凭据走环境变量，agent 只执行已配置好的命令
- 帖子里的论文链接/arXiv 号 → paper-pdf profile
