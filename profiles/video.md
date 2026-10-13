# 视频 profile

触发：视频文件路径、或来源 profile 下载出的 MP4（小红书/B站）。

## 三连（下载 → 音频转文字 → 抽帧）

1. **下载**：来源 profile 负责（小红书使用上游 OpenCLI download；B站见 bilibili.md）
2. **音频转文字**（先拿全文，信息密度高于抽帧，纯 CPU）：
```bash
ffmpeg -i input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav
zh2text audio.wav          # sherpa-onnx + SenseVoice int8；wrapper 在 ~/.local/bin/zh2text
```
   - **音频超过 ~10 分钟必须先切段**，否则 SenseVoice 注意力按 T² 吃内存直接 OOM 返回空结果：`ffmpeg -i audio.wav -f segment -segment_time 300 -ar 16000 -ac 1 -acodec pcm_s16le seg/%03d.wav`，再 `zh2text seg/*.wav`（单进程加载一次模型、逐文件出 `<wav>: <文本>` 行）
   - wrapper/模型缺失或损坏时的重建参数：模型 `~/.cache/sherpa-onnx/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/`（229MB），脚本 `~/.cache/sherpa-onnx/transcribe.py`（整文件解码、无 VAD、不切段），走 `~/.local/share/uv/tools/sherpa-onnx/bin/python`（uv tool install 需 `--with click`；1.13.x 无 CLI，走 Python API + 标准库 wave）
   - **视频可能没有音轨**：ffmpeg 报 `Output file does not contain any stream` = 只有视频流；`ffprobe -show_entries stream=codec_type` 确认后转抽帧 + desc 正文补内容
3. **抽帧联系表**：
```bash
ffmpeg -i input.mp4 -vf "fps=1,scale=720:-2" -q:v 2 frames/%04d.jpg    # 短视频
ffmpeg -i input.mp4 -vf "fps=0.2,scale=720:-2" -q:v 2 frames/%04d.jpg  # 长视频
ffmpeg -pattern_type glob -i "frames/*.jpg" -filter_complex "tile=4x6:padding=4:margin=4:color=white" contact.jpg
```
   - **帧数按 20 帧算**：`fps = 20 / 视频时长`（28.8s→0.7；72s→0.28），固定 fps=1 在 40s+ 视频会出 40+ 帧，联系表喂不进
   - WebP 伪装 jpg 混入会让 tile/xstack 解码失败 → 全部先转 PNG 再拼
   - 联系表 scale=540 够用；>24 帧 ffmpeg tile 自动分块输出 tile_N.jpg

## 多模态分析

vision_analyze / kimi 读联系表 + 字幕文本 → md。多段 MP4 逐一 ffprobe 盘点、逐一分析（各段可能是不同内容）；关键信息处 `-ss` 局部加密抽帧复查。

**抽帧单独足够**：3 条视频仅靠 19-20 帧联系表（fps = 20/时长）完整提取全部内容——128s 视频读出 GitHub star 数（60.1k）和命令数，19.2s 视频库名/网址/推文原文完整可读。帧里的小字 kimi 会放大核对，scale=540 即可：

```bash
ffmpeg -y -v error -i input.mp4 -vf "fps=0.15,scale=540:-2" -q:v 2 frames/f%04d.jpg   # 128s → 19 帧
ffmpeg -pattern_type glob -i "frames/*.jpg" -filter_complex "tile=5x4:padding=4:margin=4:color=white" contact.jpg
```

## 纪律

- 区分"视频实际展示" vs "标题/文案称" vs "推断"，不脑补
- 画面里的 URL/仓库名单次读取不可靠，验证后写
- 小红书视频按实际媒体决定处理：先验证视频与音轨；有讲话则转录，有独立画面信息则抽帧核对。无音轨/仅配乐记录依据，不凭平台假定字幕存在或不存在。CLI 标记 unsupported 时保留待补，不把封面或 desc 当视频内容。长音频切段并后台补齐。
- B站长视频（>10 分钟）等重负载仍走 background+notify；100 分钟音频约 40 分钟 CPU
