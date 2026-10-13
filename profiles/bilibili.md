# B站 profile

触发：`b23.tv`（短链）、`bilibili.com/video/BV`。视频转写叠加 video profile。

## 有字幕（最快）

```bash
opencli bilibili video '<BV链接>' --window background -f json    # 元数据
opencli bilibili subtitle '<BV链接>' --window background -f plain > sub.txt
```

## 无字幕 / yt-dlp 412

yt-dlp 直连报 `HTTP 412`，opencli bilibili download 也卡在只下封面。可靠路径：浏览器页面上下文取播放流。

1. browser_exec：`new_tab("https://www.bilibili.com/video/<BV>/")` + `wait_for_load()`，然后 `js("window.__playinfo__.data.dash.audio")`
   - 每次用 new_tab 新开标签页：`__playinfo__` 只在首次加载时注入，复用旧 tab 读到 undefined
   - `dash.audio` 按 `bandwidth` 挑最大（30216=64k / 30280=132k / 30232 等）；同时可拿 `dash.video` 档位与 `__INITIAL_STATE__.videoData.duration/cid`
2. `curl -sL -A "<桌面 Chrome UA>" -e "https://www.bilibili.com/" -o audio.m4s "<baseUrl>"`（100 分钟约 94MB）；不行换 `backupUrl`
3. `ffmpeg -y -i audio.m4s -vn -acodec pcm_s16le -ar 16000 -ac 1 audio16k.wav`
4. **转写前验证完整性**：`ffprobe -show_entries format=duration` 与网页 duration 对齐

## 长音频转写（带时间戳）

`~/.cache/sherpa-onnx/transcribe_ts.py`（SenseVoice int8 分块，`--chunk 30 --start/--end`，输出 `[HH:MM:SS] 文本`）。先验证 Python 可 import sherpa_onnx；Hermes 自带 Python 不等于转写环境，已有 `~/.venvs/transcribe/bin/python3` 可用。核对语言配置，英文用 en，不沿用 zh。长音频 `background=true, notify=true` 派后台；结束核对内部退出码、预期分块数和片尾，外层 shell 成功不代表转写成功。精确定位先 30s 粒度，再 `--chunk 10` 细化。

## 原版字幕优先

搬运访谈先搜索原版视频。YouTube 字幕先用 `opencli youtube transcript '<URL>' -f json`，参数查 --help。yt-dlp 或 player API 遇到 bot/LOGIN_REQUIRED 时，空 captionTracks 不能证明没有字幕。OpenCLI Chrome 与 browser_exec 登录态不同，Navigation rejected 不代表未登录，先 doctor。

产品名和仓库归属用画面或官方仓库复核。字幕说话人标号可能错误，不机械归属观点。程序验证或数学证明不等于消除数据丢失等不可逆后果。

## 屏幕文字（PPT/slides）

屏幕文字**先去课程站找 slides 源文件**（如 jyy 的在 `jyywiki.cn`，提示词原文以 `\u003c`/`\u4f60` 转义嵌在 HTML，解一层转义再抽 `blockquote/pre/code`）；slides 拿不到再抽帧 tesseract（本机带 chi_sim+eng，整句识别受画质限制）。

## 论文解读视频

标题通常含论文关键词 → paper-pdf profile 反查下载。
