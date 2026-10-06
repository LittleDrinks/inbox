---
name: inbox
description: "喂与取 two-verb inbox router. 喂/capture: user drops 小红书/微信/B站/X links, papers, or screenshots saying 收藏/放进inbox → load profiles/<site|medium>.md → one md in $OBSIDIAN_INBOX/webclip/. 取/recall: user wants to USE stored stuff (选配色/改图/选工具/找方法) → answer only from inbox stock with source paths; digests land in digest/."
version: 3.1.0
author: user
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [inbox, xiaohongshu, weixin, bilibili, x-twitter, webclip, obsidian, capture, recall, router]
    related_skills: [opencli-usage, opencli-browser, xitter, obsidian-research]
---

# inbox：喂与取（v3.1 路由器）

设计原则（mymind/Readwise/NotebookLM 共同验证）：组织动作归 agent 不归用户；存货靠 recall 浮上来才有价值；回答只来自存货并给出处，没有就说没有。本文件只做判动词与路由，每个来源一个 profile。

## 判动词

| 用户行为 | 动词 |
|---|---|
| 丢链接/截图/文字，说"收藏/放进 inbox/处理一下" | **喂**（capture） |
| 说要"用"：改图选配色、选工具、找读论文方法、写论文找素材 | **取**（recall） |

## 喂 → 路由表

按输入特征加载 `profiles/<name>.md`；内容重的输入叠加媒介 profile：

| 输入特征 | profile | 叠加 |
|---|---|---|
| `xhslink.cn/o/`、`xiaohongshu.com` | `profiles/xiaohongshu.md` | 图文→image，视频→video |
| `x.com`、`twitter.com` | `profiles/x.md` | 含论文→paper-pdf |
| `mp.weixin.qq.com/s/` | `profiles/wechat.md` | 识别出论文→paper-pdf |
| `b23.tv`、`bilibili.com/video/BV` | `profiles/bilibili.md` | video |
| arXiv/ACL/OpenReview/HF 链接或论文标题 | `profiles/paper-pdf.md` | — |
| 本地截图/图片路径 | `profiles/image.md` | — |
| 视频文件/视频链接（任意来源） | `profiles/video.md` | 来源 profile 在前 |

**aris 目录已废弃（2026-10-07）**。ARIS 产出（概念拆解、实验方案、评审记录）直接按内容类型进 webclip 或 digest，不再单列目录。

## 通用规则（所有分支）

- **paste 链**：用户连贴多次时 paste 文件互相引用（`Pasted text #N → file`），顺链追到底；说"全部"就全量，只说当前 N 条就只处理消息里的。
- **事实分层**：区分"内容实际展示" vs "标题/文案称" vs "推断"。
- **URL 验证**：OCR/画面读出的链接验证后才写进 md（如 GitHub API 返回 200），多次读取冲突以 API 为准。
- **终端**：批量走脚本文件（terminal 工具拒绝 `&` 后台）；opencli 批量稳定模式是每条独立进程。
- **状态目录**：`~/.cache/<项目>/`（/tmp 会被系统清理）。

## 消化与 digest 硬规则（2026-10-07 定）

- **Wikipedia 句式**：每条 = 名称 + 一句话定义（输入→输出 / 解决什么 / 覆盖什么），句号结尾。禁过渡词（"这个主题下""值得注意的是""总的来说"）、禁连接词（"互补""配合"）、禁额外解读（"这意味着""本质是"）。条与条之间就是换行。
- **xhs 链接必须带 xsec_token**：裸 `explore/<noteId>` 会被风控弹到通用页。写完 digest 后必须自查裸链——`grep -oE 'xiaohongshu\.com/explore/[0-9a-f]{24}[^?]' <file>` 命中即为事故。token 丢失时用 `opencli xiaohongshu search <标题关键词> --window background -f json` 按 noteId 匹配找回；搜不到标注 `[链接已失效]`。
- **进 inbox 即标类型**：过眼即焚（营销号/工具推送）消化后只留一手来源（GitHub/arXiv/官网），xhs 链接不留；未来要查（prompt 模板/色卡/清单）内联进 digest 且附 xhs 原链。
- **评论爬取**：仅两类必爬——评论区给出一手链接（GitHub 等）的笔记、求助帖（"xxx 背景求指导"，评论是精华）。其他默认不爬，用户明说才爬。
- **消化后删原料**：digest 内联了原料的，原料 md 即删。digest 汇总即权威版本，不留指针回已删原料。

## 交付形态（全分支统一）

目录 `$OBSIDIAN_INBOX/webclip/`（md）。论文 PDF 直接入 Zotero（zotero-cli import，inbox 不存 PDF）。
命名 `YYYY-MM-DD-webclip-<平台>-<主题>.md`。
文件头：
```markdown
#status/todo

---
date: <日期>
source: <平台 / 作者>
url: <原文链接>
type: 论文解读 | 图文笔记 | 视频笔记 | 论文清单 | 调研素材 | 项目构思
title: "<原标题>"
---
```
正文只写信息本身：零自我指涉、来源进 frontmatter、并入子代理产出前砍掉过程说明块。论文清单类标注"无链接，无法下载单篇 PDF"。

**aris 废弃后**：调研素材、项目构思、prompt 模板等原 ARIS 产出直接进 webclip，type 字段标注「调研素材」「项目构思」「prompt 模板」即可。

## 堆积治理（喂出来的东西堆积时）

- inbox/webclip 堆积 → 按主题归并合集（TOPICS 关键词分组，每条保留标题+来源+核心+链接）；同一笔记存在裸 explore/短链/带 token 三种 url 形态，去重按标题核心词匹配。合集 = 过渡形态，recall 消化后合集与原料一起删
- 堆积的根因是没被 recall。取（recall）产物落 digest/ 后，同主题原料即删，digest 汇总即权威版本
- digest 本身堆积 → 按主题跨日期合并（如「科研绘图与论文写作」合并 09-22/09-24/10-06 三期），每主题只保留一篇权威版，旧版删除

## 取（recall）

1. **先查 `inbox/digest/` 缓存**有没有现成汇总产物（如 `2026-10-07-digest-科研绘图与论文写作.md`），命中就基于它回答
2. 缓存未命中再检索存量：grep inbox 全区（webclip/digest）frontmatter 的 type/title + 桌面历史报告；用概念词（配色/pipeline/读论文），少用平台词
3. 汇总成决策层产物：主推放最前；HEX/命令等原始数据内联；每条带来源文件路径；存货没有的部分明说
4. 产物落 `inbox/digest/YYYY-MM-DD-digest-<主题>.md`，成为下次取的缓存层；对应原料（如已内联的色卡原帖）随之删除

输出形态按场景定：改图 → 场景→色卡映射表；选工具 → 梯队表+首推+理由；找方法 → 步骤清单。