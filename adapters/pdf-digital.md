# pdf-digital 适配器：数字版 PDF → markdown

## 契约

输入：PDF 文件路径（数字版，有文字层）
输出：markdown 文本，保留标题层级和表格结构

## 默认实现

`opendataloader-pdf`（odl-pdf skill）

## 替换

任何能把数字版 PDF 转成结构化 markdown 的工具。常见替代：pymupdf4llm、marker、MinerU。换掉时改本文件的"默认实现"段，SKILL.md 不需要动。
