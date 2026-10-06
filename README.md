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
profiles/
  xiaohongshu.md    # 小红书：xsec_token 风控绕过、opencli 抓取
  wechat.md         # 微信：mp.weixin.qq.com 文章
  bilibili.md       # B站：BV 号视频
  x.md              # X/Twitter
  paper-pdf.md      # 论文 PDF（arXiv/ACL/OpenReview/HF）
  image.md          # 本地截图/图片
  video.md          # 视频文件/链接
```

## 许可证

MIT
