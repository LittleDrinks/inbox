# X / Twitter profile

触发：`x.com/<user>/status/<id>`、`twitter.com/...`。
主用 **xitter skill**（x-cli 走官方 API）。深度用法（发帖/时间线/书签）加载 xitter skill 本体。

```bash
x-cli tweet get <post_url_or_id>      # 读单条帖（接受完整 URL，自动提取 ID）
x-cli user get <handle>               # 用户信息
x-cli tweet search "关键词" --max 10   # 搜帖
```

- 图片媒体：X API v2 expansions 取 URL（`/2/tweets/<id>?expansions=attachments.media_keys`）
- 凭据走环境变量，agent 只执行已配置好的命令
- 帖子里的论文链接/arXiv 号 → paper-pdf profile
