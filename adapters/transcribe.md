# transcribe 适配器：音频/视频 → 文本

## 契约

输入：音频或视频文件路径
输出：纯文本转录稿（可选时间戳）

## 默认实现

`whisper`（OpenAI Whisper，本地 GPU，whisper skill）

## 替换

任何语音转文字工具。常见替代：faster-whisper、FunASR、剪映字幕导出、讯飞听见。换掉时改本文件的"默认实现"段。
