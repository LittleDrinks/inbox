# 图片 profile

触发：本地截图/图片路径（`/mnt/...`、`E:\...`、微信 temp 转存 `E:\xwechat_files\<wxid>\temp\RWTemp\<YYYY-MM>\`）。

## 路由

1. **vision_analyze 直读本地路径是主路**
2. vision 失败切 kimi 备路（下节）
3. 大批量纯文本 OCR（几十张+、纯文本级）→ RapidOCR（下节）
4. 几十张图逐张 vision 会炸上下文 → 丢 subagent（delegate_task）逐张写 `ocr/<code>.md`，只回摘要

## kimi 备路

kimi-code 是 agent 不是一次性 CLI，**不支持位置参数**（`kimi -p "..." 图片.jpg` 报 unknown command）：cd 进图片目录，prompt 内引用文件名。

```bash
cd <图片目录>/
~/.kimi-code/bin/kimi -p "请读取当前目录下的图片 <filename>（用你的图片读取工具），完整转录全部文字，逐段不漏，岗位要求、数据、链接、命令等原文细节全部保留。用中文输出，跳过排版和颜色描述。"
```

- 转录 prompt 必须写死"完整转录逐段不漏"——默认行为是挑重点，实测 4 段只回 1 段且看不出丢
- 多图一次点名并行读（`img1.jpg、img2.jpg…`），kimi 会放大核对遮挡区域；每图需不同 prompt 才退回 for 循环；单图 20-60s
- **清理 reasoning 前缀**：stdout 是「英文 reasoning 段 + 空行 + 中文转录段」，从含 ≥20 个 CJK 字符的第一个块开始保留，砍行首 `• `；噪声图全块 CJK <20 时保留全文人判
- 输出尾部 `To resume this session: kimi -r <id>` 是噪声；同图两次运行可能一次成功一次只回 20 字节残片，`wc -c` 进程结束后再看
- 额度 403 → 模型自带视觉时直接切 vision_analyze

## RapidOCR 主路（批量纯文本）

```bash
# venv 必须 python3.12（python3.14 无 onnxruntime wheel）
python3.12 -m venv /tmp/rapidocr_env && /tmp/rapidocr_env/bin/pip install -q -i https://pypi.tuna.tsinghua.edu.cn/simple rapidocr_onnxruntime
/tmp/rapidocr_env/bin/python -c "from rapidocr_onnxruntime import RapidOCR; print('READY')"
```

```python
from rapidocr_onnxruntime import RapidOCR
engine = RapidOCR()
result, _ = engine("/path/img.png")   # [[box, text, score], ...]
text = "\n".join(item[1] for item in result) if result else ""
```

- ~1.1s/张（202 张 4.5 分钟），中文准确率高（群名/引用/内嵌小字全对）；Windows.Media.Ocr 实测错字多+GBK 乱码
- 批量循环输出目录每次用新的，复用旧 DST + 跳过已存在 = 新旧错配
- **语料级逐字提取只用 RapidOCR**：kimi 会语义补全污染语料；存行级 JSON（含 box 坐标）；可疑形近字（干/千、Al/AI、l/1）在原稿标注"疑为"并保留原文
- 双引擎兜底：RapidOCR 与主引擎输出做覆盖率比对（归一化标点后逐行查子串），立刻暴露漏行/改写
- 架构/排版图按视觉行序提取，左右栏顺序可能错乱，交付注明"排版顺序以原图为准"

## 图片版 PPT/PDF 批量提取

```bash
# 判定无文字层：python-pptx 遍历 shape.has_text_frame 全空 → 走提图 OCR
python3.12 -c "from pptx import Presentation; prs=Presentation('f.pptx'); [open(f'/tmp/p/slide_{i:02d}.{s.image.ext}','wb').write(s.image.blob) for i,sl in enumerate(prs.slides,1) for s in sl.shapes if s.shape_type==13]"
# 先 python3 -c "import fitz" 确认 PyMuPDF 装在哪个解释器（3.14 与 3.12 常不匹配）
# → RapidOCR 批量（~1s/页），跳过 <50KB 装饰图 → 合并文本 → grep 日期/序号验证覆盖
```

## 纪律

- OCR 文本与笔记 desc 交叉校验：内容无关（广告/美妆/宠物）= 推荐流污染图，剔除后才归档
- OCR 只用 >30000 字节的全分辨率图（缩略图会诱发模型臆造无关内容）
- WebP 伪装 .jpg：`file x.jpg` 显示 RIFF/WebP → `PIL Image.open(f).convert('RGB').save(png)` 转真 PNG
- 读出的 URL 验证后才写进 md；不可读段落标注存疑
- **声称来源某论文的绘图帖，配图可能与论文不符**（2026-08-22 实测 CLIP-Backdoor 帖配图实为 MCD-Net/FlashCache）：prompt 显式要求核对图中内容与声称论文是否一致；不符 → 标注"⚠️ 配图与论文不符"，图仅作配色/排版参考，核心信息以论文本体为准（走 paper-pdf），不按论文内容脑补图片描述

## 场景出口

- **配色帖**：名称+HEX+用途标签表格；色名保持原文中文；标注"建议对照原图核对"
- **论文首页截图说"归档"**：RapidOCR 拿标题/作者/摘要（~1s）→ 识别出论文走 paper-pdf profile，截图归档 `inbox/webclip/<topic>-YYYY-MM-DD/`
- 原图归档 `inbox/webclip/<topic>-YYYY-MM-DD/`，md 里引用目录
