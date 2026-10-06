# pdf-scanned 适配器：扫描版 PDF → markdown

## 契约

输入：PDF 文件路径（扫描版/公式密集/复杂版面）
输出：markdown 文本，保留语义结构

## 默认实现

Logics-Parsing V3（vlm-pdf-extraction skill）。odl-pdf 失败时升级到本路径。

## 替换

任何 VLM-based PDF 解析方案。常见替代：GPT-4o/Claude vision 直接读页图、MinerU、GOT-OCR2.0。换掉时改本文件的"默认实现"段。
