# paper-store 适配器：论文 → 文献管理器

## 契约

输入：论文 PDF 路径或 arXiv/DOI 标识
输出：文献管理器中的一条记录（含元数据）

## 默认实现

`zotero-cli import`（zotero-cli skill）。inbox 不存 PDF，只存元数据和笔记。

## 替换

任何文献管理工具。常见替代：Zotero 官方客户端手动拖入、EndNote、Paperpile、Obsidian Citations 插件。换掉时改本文件的"默认实现"段。
