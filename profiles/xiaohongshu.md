# 小红书 profile

触发：`xhslink.cn/o/`、`xhslink.com/o/`（分享短链）、`xiaohongshu.com/explore/`、`search_result/`。
图文叠加 image profile，视频叠加 video profile。

## 采集主路（优先级序）

1. **分享页 HTML 直取全量字段**：`curl -sL -A "<iPhone UA>" "http://xhslink.cn/o/<CODE>"` 的 HTML 内嵌完整 noteData。双层转义还原（`\\` → `\`，`\uXXXX` → 字符，`\n`/`\t` 再解一次）；单字段正则优于整体 json.loads。字段：desc / title / nickName / likedCount / collectedCount / commentCount / imageList / masterUrl。
2. **opencli note/download 兜底**：`opencli xiaohongshu note '<完整URL>' --window background -f json`（输出 field/value 数组，解析用 `{x['field']: x['value']}`）。
3. download 后**验证输出目录名 == 目标 noteId**，不一致 `rm -rf` 重来 ≤5 次；download 会在输出目录下再套一层 noteId 目录（实际在 `media/<nid>/<nid>/`）。

## xsec_token 获取

- **xsec_token 与 noteId 绑定**，跨笔记互借触发 SECURITY_BLOCK（小红书风控）
- **首选**：短链 HTML 里挖 `grep -oE 'xsec_token=[A-Za-z0-9_-]+'`（4/4 全通）。token 有两种写法：`"CB...="` 和 `CB...%3D`，两个正则都跑，喂 opencli 时 `=` 编码成 `%3D`
- search 返回的 token 仅用于验证标题/noteId（跨页使用触发 SECURITY_BLOCK）
- 历史 md 里的 token 长期有效：`grep -oE 'explore/[0-9a-f]+\?xsec_token=[^ )]*' $OBSIDIAN_INBOX/webclip/*.md`

## 标题（多来源交叉）

短链 HTML 的 title **紧跟在 `"noteId":"<nid>"` 之后**（`raw[idx:idx+300]` 内取），之前出现的是推荐位别人的标题；opencli note 的 title 偶发抓错。以 HTML title + 正文首句 + 用户描述交叉定标题。作者定位用 `opencli xiaohongshu user <userId>` 列其公开笔记，比站内搜索准。

## 图片下载

- H5_DTL 正则只出部分图；抓全用宽正则 `re.findall(r'http://sns-webpic-qc\.xhscdn\.com/[^"\\]*', raw)` 排序去重（9 图实测）
- URL 结尾 `!h5_1080jpg` 后缀要保留，漏掉 curl 到 0 字节；按字节数 >30000 过滤缩略图
- curl 必带 `-e "https://www.xiaohongshu.com/"`
- 签名 URL 会过期：ThreadPoolExecutor(4) + `--max-time 20`，过期就放弃标注

## 交付铁律

- 交付链接带 token：`https://www.xiaohongshu.com/explore/<nid>?xsec_token=<token>`；没 token 用 `http://xhslink.cn/o/<code>` 短链（裸 `explore/<nid>` 在网页端显示"找不到帖子"）
- search 的 `search_result/...` URL 仅用于内部传给 note/download，交付前转成上款真实链接
- frontmatter `url:` 与正文链接同步更新

## 场景要点

- **配色帖**：提取名称+HEX+用途标签成表格，色名保持原文中文，标注"建议对照原图核对"
- **视频笔记**：小红书全部无字幕 → 一律下载视频跑完整三连（curl masterUrl 下 MP4 → ffmpeg 抽音频 zh2text 转写 → 抽帧联系表喂 vision）。小红书视频多为几分钟以内，必须当场完成转写+抽帧并写入 md，不再默认"未转录"。仅音频 >10 分钟时先交抽帧结果、转写派 background+notify 补齐
- **论文识别**：标题/正文含 arXiv/顶会关键词 → paper-pdf profile

## 批量（30+ 条）

流水线而非逐条：curl 层先跑（50 条约 1 分钟）→ 浏览器层后台（约 1 条/分钟）→ 每 5 条 sleep + 状态 json 可续跑（状态目录 `~/.cache/<项目>/`，/tmp 会被系统清理）→ 按主题合册交付（约 5 册）。查重用 noteId 精确匹配（标题模糊匹配 12/19 漏一半）。

**搜索→批量分析**（`opencli xiaohongshu search '<关键词>' --limit N -f yaml`）：

- 结果过滤：去掉明显无关标题，优先视频笔记条目；`search_result/...` URL 仅内部传给 note/download
- 每个结果独立输出子目录 `/tmp/xhs-video-work/search-<query>-<ts>/<rank>-<nid>/`，防文件名冲突
- 无 token 的笔记：download 短链（xhslink.com 可直传）+ 目录名验证；搜索收录差的营销号笔记搜不到 token，靠 download 图片 OCR + HTML 标题生成 md，标注"⚠️ 正文未获取"
- 批量输出每条：标题/作者/可交付链接/一句话结论/实际展示要点/明确出现的工具链接/未验证项；用户只要链接列表时输出"视频已验证出现"的链接

## opencli note 采集（⚠️ 必须 --trace retain-on-failure）

- **不加 `--trace retain-on-failure` 必失败**：`opencli xiaohongshu note` 默认报 `Navigation rejected`，加 `--trace retain-on-failure` 后正常返回
- **xsec_token 与 noteId 严格一对一绑定**：跨笔记借用 token → `SECURITY_BLOCK`；同笔记 token 短期有效，批量采集时每条独立 curl 短链取 fresh token 再喂 opencli
- **批量流水线**：`curl xhslink.cn/o/<code>` 取 HTML → 正则挖 `xsec_token=...` → 拼 `explore/<nid>?xsec_token=<token>` → `opencli xiaohongshu note <url> --window background -f json --trace retain-on-failure`
- **desc 编码**：curl HTML 内嵌的 desc 是正确 UTF-8（`json.loads(f'"{raw}"')` 直接解）；不要用 `unicode_escape`（会变 mojibake）
- **风控节奏**：连续 curl 16+ 条会触发登录页（HTML 长度 <20k）；每 3-5 条 sleep 0.5-1s 可缓解
- **opencli title 偶发抓错**：`opencli xiaohongshu note` 返回的 title 字段可能为空或与 HTML title 不一致，以 curl HTML 的 title 为准（`"noteId":"<nid>"` 后 300 字符内取）

## 坑

- masterUrl 双层转义（2026-10 实测）：curl HTML 里 masterUrl 是 `http:\\u002F\\u002F` 双层转义，json.loads 解不动；直接字符串替换 `\\u002F`→`/`、`\u002F`→`/`。ThreadPoolExecutor(4) 批量 curl 带 `-e https://www.xiaohongshu.com/`，15 个视频全部直下载成功，不需要 opencli download
- 视频批量转写环境：sherpa_onnx 在 `~/.venvs/transcribe/bin/python`（系统 python 没有），批量脚本里写死这个解释器；无音轨的视频 ffmpeg 抽音频报 "Output file does not contain any stream"，属正常（BGM-only 海报视频/纯图轮播），跳过即可
- 同笔记换文案重发：查重以 noteId 为准（同一笔记换文案后标题就不同）；重复条目标 `⚠️ 已有：<旧文件>` 让用户决定
- 搬运视频：帧内水印账号 ≠ 笔记作者 → 多条笔记同源，合并为一条产品记录互 `[[]]` 引用

## 营销号溯源（digest 时必做）

- **GitHub 链接一律 API 验证**：404 时用关键词搜索定位真身：`/search/repositories?q=<关键词>`
- **常见错误模式**：OCR 数字/字母混淆（`a1i`→`ali`）、凭记忆手打项目名、旧链接失效、加不存在的组织前缀
- **star 数交叉验证**：star 很高但链接 404 → 几乎肯定是链接错了，用描述关键词搜索
- **产出**：溯源结果写入 digest 文件，标注 `✓ 验证通过` / `✗ 已纠正` + 正确地址 + 错误原因
