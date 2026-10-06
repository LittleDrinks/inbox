# 小红书 profile

触发：`xhslink.cn/o/`、`xhslink.com/o/`、`xiaohongshu.com/explore/`、`search_result/`。
图文叠加 image profile，视频叠加 video profile。

## 采集

见 `adapters/xiaohongshu.md`。

## 场景要点

- **配色帖**：提取名称+HEX+用途标签成表格，色名保持原文中文，标注"建议对照原图核对"
- **视频笔记**：小红书全部无字幕 → 一律下载视频跑完整三连（curl masterUrl 下 MP4 → ffmpeg 抽音频 zh2text 转写 → 抽帧联系表喂 vision）。仅音频 >10 分钟时先交抽帧结果、转写派 background+notify 补齐
- **论文识别**：标题/正文含 arXiv/顶会关键词 → paper-pdf profile

## 批量（30+ 条）

流水线而非逐条：curl 层先跑 → 浏览器层后台 → 每 5 条 sleep + 状态 json 可续跑（状态目录 `~/.cache/<项目>/`）→ 按主题合册交付。查重用 noteId 精确匹配。

## 营销号溯源（digest 时必做）

- GitHub 链接一律 API 验证，404 时用关键词搜索定位真身
- star 数交叉验证：star 很高但链接 404 → 几乎肯定是链接错了
- 溯源结果写入 digest，标注 `✓ 验证通过` / `✗ 已纠正` + 正确地址
