# inbox

Hermes skill：把用户丢进来的链接/截图/文字路由到本地 inbox 目录，按来源平台分别处理。

## 干什么用

刷到一个有意思的东西——小红书帖子、微信文章、B站视频、X 推文、论文 PDF、截图——丢给 agent 说"放进 inbox"。agent 判断来源、抓取内容、写成 md 落进 `inbox/webclip/`。

几天后你想"用"之前收藏的东西，agent 从 inbox 存量里检索、汇总成 digest。

两个动词：**喂**（capture）和**取**（recall）。

## 安装

```bash
git clone https://github.com/LittleDrinks/inbox.git ~/.hermes/skills/note-taking/inbox
export INBOX_DIR=/mnt/e/OBSIDIAN/inbox
# CLI 读取进程环境，不自动加载 .env。
```

## 结构

```
SKILL.md            # 路由器：判动词 → 加载对应 profile
profiles/           # 按来源平台的抓取规则（通用，不含实现细节）
  xiaohongshu.md    # 小红书：场景要点、批量、营销号溯源
  wechat.md         # 微信：mp.weixin.qq.com 文章
  bilibili.md       # B站：BV 号视频
  x.md              # X/Twitter
  paper-pdf.md      # 论文 PDF（arXiv/ACL/OpenReview/HF）
  image.md          # 本地截图/图片
  video.md          # 视频文件/链接
adapters/           # 依赖的契约与默认实现，换工具只改这里
  pdf-digital.md    # 数字版 PDF → markdown
  pdf-scanned.md    # 扫描版 PDF → markdown
  transcribe.md     # 音频/视频 → 文本
  paper-store.md    # 论文 → 文献管理器
scripts/            # 可执行脚本，adapter 的默认实现
  ego_inbox.py      # 单一入口：调用 Ego-Lite 原生引擎、落地媒体与正文
  ego_fetch.mjs     # 注入 Ego-Lite TaskSpace 的原生 DOM/CDP 抓取逻辑
```

## 许可证

MIT
