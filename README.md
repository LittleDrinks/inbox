# inbox

Hermes skill：把用户丢进来的链接/截图/文字路由到本地 inbox 目录，按来源平台分别处理。

## 干什么用

刷到一个有意思的东西——小红书帖子、微信文章、B站视频、X 推文、论文 PDF、截图——丢给 agent 说"放进 inbox"。agent 判断来源、抓取内容、写成 md 落进 `inbox/webclip/`。

几天后你想"用"之前收藏的东西，agent 从 inbox 存量里检索、汇总成 digest。

两个动词：**喂**（capture）和**取**（recall）。

## 安装

```bash
git clone https://github.com/LittleDrinks/inbox.git ~/.hermes/skills/note-taking/inbox
cp .env.example .env
# 编辑 .env，设置 INBOX_DIR 为你的 inbox 路径（如 /mnt/e/OBSIDIAN/inbox）
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
  xiaohongshu.md    # 小红书链接 → webclip md
  pdf-digital.md    # 数字版 PDF → markdown
  pdf-scanned.md    # 扫描版 PDF → markdown
  transcribe.md     # 音频/视频 → 文本
  paper-store.md    # 论文 → 文献管理器
scripts/            # 可执行脚本，adapter 的默认实现
  xhs_feed.py       # 小红书一键流水线
```

## 换依赖

所有外部工具都通过 `adapters/` 解耦。每个文件定义输入→输出契约和默认实现。不用 Zotero？改 `adapters/paper-store.md`。本地跑不动 Logics Parser？改 `adapters/pdf-scanned.md` 换成你的 VLM 方案。不用 opencli 抓小红书？改 `adapters/xiaohongshu.md`。SKILL.md 不需要动。

## 许可证

MIT
