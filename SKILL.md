---
name: inbox
description: "把用户丢的链接/截图/文字存进本地 inbox 目录（小红书/微信/B站/X/论文/图片/视频各一个 profile），之后用户要用时从存量里检索汇总成 digest。用户说\"收藏/放进 inbox\"时触发喂，说\"帮我找/选/用之前存的\"时触发取。"
version: 3.2.0
author: user
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [inbox, xiaohongshu, weixin, bilibili, x-twitter, webclip, capture, recall, router]
    related_skills: [zotero-cli]
---

# inbox：喂与取

## 判动词

| 用户行为 | 动词 |
|---|---|
| 丢链接/截图/文字，说"收藏/放进 inbox/处理一下" | **喂** |
| 说要"用"：改图选配色、选工具、找读论文方法、写论文找素材 | **取** |

## 喂 → 路由表

按输入特征加载 `profiles/<name>.md`；内容重的输入叠加媒介 profile：

| 输入特征 | profile | 叠加 |
|---|---|---|
| `xhslink.cn`、`xhslink.com`、`xiaohongshu.com` | `profiles/xiaohongshu.md` | 图文→image，视频→video |
| `x.com`、`twitter.com` | `profiles/x.md` | 含论文→paper-pdf |
| `mp.weixin.qq.com/s/` | `profiles/wechat.md` | 识别出论文→paper-pdf |
| `b23.tv`、`bilibili.com/video/BV` | `profiles/bilibili.md` | video |
| arXiv/ACL/OpenReview/HF 链接或论文标题 | `profiles/paper-pdf.md` | — |
| 本地截图/图片路径 | `profiles/image.md` | — |
| 视频文件/视频链接 | `profiles/video.md` | 来源 profile 在前 |

## 本地群聊分享筛选

- 用户指定「好文推荐／好图分享」时，按推荐语境筛分享，不生成项目复盘；先确认用户的群昵称，@匹配不得借用数小时后的无关消息。
- 先解析消息头，核对导出声明条数与实际消息数；全文 URL/PDF 检索之外，扫描「好文、读论文、你喜欢的、好图、好表」及相邻消息。仅截图／纯标题的论文也要定位，不能只抽 URL。
- 用缩略拼图视觉筛掉表情、普通聊天、个人照片、工作进度；保存明确分享的绘图、表格、配色与界面设计参考原图。用户要求「只存图」时不加图解；按哈希去重与核验复制。`[图片]` 无文件的占位单列缺失，不能把别人的邻图当它。
- 好图文件名写原出处，不只写分享平台或群名：`分享日期-论文或文章短标题-稳定标识符-群名-L原行号.ext`。论文标题须与原图或图注交叉核验；无法确认写「原出处未确认」，转载水印与原作者区分。重命名前核对目录现状与哈希，已被用户移走或删掉的图不自动补回。
- 好文进入 Zotero；核对真实标题、作者、标识符，查重后保留推荐者、消息时间、原行号及是否明确 @用户。文章来源/阅读优先级用 provenance/tags，不新建待读或群来源 collection。推荐争论、自家稿件版本、会议通知不等于好文。
- 群聊有明文凭据：候选上下文只保留必要窗口，持久化前去除账户密码、验证码、API key及私密报告 token；不得复制整份聊天进可分享的笔记。

## 采集实现改进

批量采集、替换抓取工具或修复静默漏抓时，加载 `references/capture-contract.md`：上游负责抓取，本地负责归档与文件检查，语义取舍交 agent。

## 通用规则

- **paste 链**：用户连贴多次时 paste 文件互相引用（`Pasted text #N → file`），顺链追到底；说"全部"就全量，只说当前 N 条就只处理消息里的。
- **事实分层**：区分"内容实际展示" vs "标题/文案称" vs "推断"。
- **URL 验证**：OCR/画面读出的链接验证后才写进 md（如 GitHub API 返回 200），多次读取冲突以 API 为准。
- **终端**：批量走脚本文件（terminal 工具拒绝 `&` 后台）；批量稳定模式是每条独立进程。
- **状态目录**：小红书原料、状态与媒体同存 inbox 内持久批次目录，见 `profiles/xiaohongshu.md`；其他工具临时缓存遵循运行环境 scratch 约定。

## 消化与 digest 硬规则

- **Wikipedia 句式**：每条 = 名称 + 一句话定义（输入→输出 / 解决什么 / 覆盖什么），句号结尾。禁过渡词（"这个主题下""值得注意的是""总的来说"）、禁连接词（"互补""配合"）、禁额外解读（"这意味着""本质是"）。条与条之间就是换行。
- **链接有效性自查**：写完 digest 后检查所有链接是否可打开。先从 Markdown 中解析 URL，再逐条校验；不要让条目正文、标点或括号混进 URL。平台调用与校验规则统一见对应 profile。发现已有证据指向更正后的 GitHub/官网地址时，统一修正 digest 内所有旧地址，并复核安装命令、演示站和正文链接。
- **证据分层**：图集必须分别记录文件存在性、OCR/文字层证据和视觉审阅证据。OCR 只能支持候选类型，不能写成已确认的构图、色系或可复刻结论；视觉服务失败时保留“待视觉核验”，不要补猜，也不要把子代理的自报完成当作视觉事实。
- **批量 digest 先建索引再合并**：多图或多文件任务先生成带稳定编号、相对路径、SHA-256 和状态的 manifest/index，再从索引合并 digest；不要用未经检查的字符串拼接生成 Markdown 链接。合并后核对“声明总数 = 条目数 = manifest 数 = 实际存在数”，并检查所有内联路径存在。完全重复要记录但不删除原料，近重复不得凭文件名直接合并。
- **Prompt 与色卡内联**：digest 声称某个 prompt 或色卡可复用时，若 inbox 原料有完整正文、HEX/RGB/用途，就直接内联；只有视觉估算或来源未确认的值必须单独标注，不能伪装成原图参数。科研配色检索覆盖 `配色`、`色卡`、`HEX`、`RGB`、`palette`、`好图`、`figure`、`pipeline`、`prompt`、`MCM`、`paper`、`绘图` 和 `skill`，同时扫描 `webclip/`、`digest/`、`wish-to-do/`。
- **进 inbox 即标类型**：过眼即焚（营销号/工具推送）消化后只留一手来源（GitHub/arXiv/官网），原始平台链接不留；未来要查（prompt 模板/色卡/清单）内联进 digest 且附原始平台链接。
- **评论爬取**：仅两类必爬——评论区给出一手链接（GitHub 等）的笔记、求助帖（"xxx 背景求指导"，评论是精华）。其他默认不爬，用户明说才爬。
- **消化后删原料**：digest 内联了原料的，原料 md 即删。digest 汇总即权威版本，不留指针回已删原料。

## 课程资料验收

- 浏览器点击下载后，核查下载记录与实际默认目录；页面仍显示登录或未返回文件不等于下载失败。用户提供的具体路径优先于记忆里的目录大小写。同名副本核对大小、SHA256、ZIP完整性，未授权不删除。
- 区分外层资源包下载成功与内层可用范围；公开PPT可整理，加密内包记录限制，不猜密码、不把部分可读说成全部取得。
- 课程原子笔记按可独立解题的机制拆分，不按术语／课件页建文件。Introduction合并概览，题目默认折叠；波形和拓扑题嵌真实图片，单有PPT链接不等于笔记内可练题。

## 依赖

平台抓取的用法统一写在 `profiles/`。跨平台共用的 PDF、转录、文献管理工具保留在 `adapters/`，由 profile 引用，不重复抄写。

| 场景 | 适配器 |
|---|---|
| 数字版 PDF → markdown | `adapters/pdf-digital.md` |
| 扫描版/公式 PDF → markdown | `adapters/pdf-scanned.md` |
| 音频/视频 → 文本 | `adapters/transcribe.md` |
| 论文 → 文献管理器 | `adapters/paper-store.md` |
| 小红书抓取 | `profiles/xiaohongshu.md` |
| B站/微信/X 抓取 | 见各 profile |

## 交付形态

目录 `$INBOX_DIR/webclip/`。论文 PDF 入文献管理器（见 adapters/paper-store.md），inbox 不存 PDF。

PDF 入库成功后，再写一张 webclip 元数据卡；不要先写“已入库”再尝试导入。元数据卡记录来源文章 URL、直链 PDF URL、原始文档作者、发布者、发布日期、文档年份、Zotero 条目 key 和状态标签。来源文章作者与 PDF 原始作者不同（例如转载者发布旧备忘录）时，frontmatter 分开写 `source` 与 `author`，不要把发布者误写成论文作者。正文只保留内容摘要和可复核的 Zotero key，不复制 PDF 全文。

手写原料命名 `YYYY-MM-DD-webclip-<平台>-<主题>.md`；脚本管理的批次路径遵循对应 profile。
文件头：
```markdown
---
date: <日期>
source: <平台 / 作者>
status: "#status/todo"
url: <原文链接>
type: 论文解读 | 图文笔记 | 视频笔记 | 论文清单 | 调研素材 | 项目构思
title: "<原标题>"
---
```
正文只写信息本身：零自我指涉、来源进 frontmatter、并入子代理产出前砍掉过程说明块。论文清单类标注"无链接，无法下载单篇 PDF"。

调研素材、项目构思、prompt 模板等产出直接进 webclip，type 字段标注「调研素材」「项目构思」「prompt 模板」。

## 堆积治理（喂出来的东西堆积时）

- inbox/webclip 堆积 → 按主题归并合集（TOPICS 关键词分组，每条保留标题+来源+核心+链接）；同一小红书笔记按 noteId 精确去重；标题核心词仅辅助跨笔记主题合并，不用于认定同一笔记。合集 = 过渡形态，取消化后合集与原料一起删
- 堆积的根因是没被取。取消化产物写入 digest/ 后，同主题原料即删，digest 汇总即权威版本
- digest 本身堆积 → 按主题跨日期合并，每主题只保留一篇权威版，旧版删除

## 取

1. **先查 `inbox/digest/` 缓存**有没有现成汇总产物（如 `2026-10-07-digest-科研绘图与论文写作.md`），命中就基于它回答
2. 缓存未命中再检索存量：grep inbox 全区（webclip/digest）frontmatter 的 type/title + 桌面历史报告；用概念词（配色/pipeline/读论文），少用平台词
3. 汇总成决策层产物：结论先行；原始数据（HEX/命令/链接）内联；每条带来源文件路径；存货没有的部分明说
4. 产物写入 `inbox/digest/YYYY-MM-DD-digest-<主题>.md`，成为下次取的缓存层；对应原料随之删除
