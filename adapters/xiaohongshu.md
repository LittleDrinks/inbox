# xiaohongshu 适配器：小红书链接 → webclip md

## 契约

输入：小红书链接（短链 `xhslink.cn/o/<code>`、长链 `explore/<nid>`、裸 noteId）
输出：一篇 webclip md，含标题、正文、图片 URL、作者、可交付链接

## 默认实现

`scripts/xhs_feed.py <url>` — 两条路径：curl 短链 HTML 直取 → opencli note 兜底。产出写入 `$INBOX_DIR/webclip/`。

## 替换

任何能从小红书链接提取标题+正文+图片的工具。换掉时改本文件的"默认实现"段，profiles/xiaohongshu.md 不需要动。

## 已知坑（与实现无关，平台层面的）

- xsec_token 与 noteId 一对一绑定，跨笔记借用触发 SECURITY_BLOCK
- 裸 `explore/<noteId>` 无 token 在网页端显示"找不到帖子"
- 签名图片 URL 会过期，须即时下载
- 同笔记换文案重发时 noteId 不变，查重以 noteId 为准
