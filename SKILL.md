---
name: video_teardown
description: 解析短视频分享链接并进行完整的视频内容拆解。包括：提取无水印直链、AI分析视频内容（时间轴拆解、钩子分析、卖点提炼、口播转录）、下载视频、按时间段拆分、抽帧、场景检测、合成分镜大图。当用户提到"解析视频链接"、"拆解视频"、"分析这个视频"、"视频去水印"、"抖音链接"、"复刻视频"等场景时触发此技能。即使用户只是粘贴了一个短视频分享链接（如 v.douyin.com），也应触发。
---

# Video Teardown - 短视频内容拆解

## 概述

本技能提供完整的短视频拆解工作流：从一个分享链接出发，完成链接解析、AI内容分析、视频下载、按时间轴拆分、抽帧、场景检测、合成分镜大图的全流程。

## 脚本清单

| 脚本 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `scripts/douyin_teardown.py` | 解析抖音分享链接 | 分享URL | Markdown（标题、作者、直链、封面） |
| `scripts/video_analyze.py` | AI视频内容拆解 | CDN直链 + 保存目录 | Markdown拆解报告（保存到指定目录） |
| `scripts/video_process.py` | 下载+拆分+抽帧+合成大图 | CDN直链 + 时间段JSON + 名称 + 报告路径 + 工作目录 | 视频文件+分镜大图 |

## 智能体编排流程

使用此技能时，智能体必须先获取当前对话的工作目录（即用户所在目录），所有产出保存到该目录下的 `qwen_video/` 中。

### Step 0: 确定工作目录

智能体获取当前工作目录（即对话所在目录），后续所有脚本的输出都指向该目录下的 `qwen_video/<日期>/<内容名称>/`。

```python
import os
CWD = os.getcwd()  # 当前对话目录
```

### Step 1: 解析链接

```python
from scripts.douyin_teardown import get_video_url

result = get_video_url("https://v.douyin.com/xxxxx/")
cdn_url = result.get("video_url_cdn") or result["video_url"]
title = result.get("title", "")
```

### Step 2: AI分析视频内容

保存目录为当前工作目录下的 `qwen_video/<日期>/<内容名称>/`：

```bash
python scripts/video_analyze.py "<CDN直链>" "<CWD>/qwen_video/<日期>/<内容名称>"
```

分析结果会打印到 stdout 并保存为该目录下的 `拆解报告.md`。

### Step 3: 提取时间段

智能体自行阅读拆解报告，将【内容结构拆解】中的时间轴信息整理为 JSON 格式：

```json
[{"start": 0, "end": 3}, {"start": 3, "end": 8}, {"start": 9, "end": 14}, ...]
```

这一步由智能体完成，不需要正则解析 — 智能体能直接理解 markdown 中的时间信息。

### Step 4: 下载+拆分+抽帧+合成大图

所有脚本都通过 `--base-dir` 或位置参数指定工作目录：

```bash
python scripts/video_process.py "<CDN直链>" '<时间段JSON>' "<内容名称>" "<拆解报告.md路径>" --base-dir "<CWD>"
```

或作为模块调用：

```python
from scripts.video_process import process_video

process_video(
    video_url=cdn_url,
    segments=segments,
    content_name="氨糖软骨素带货",
    base_dir=Path(CWD),
    analysis_text=report_text,
)
```

### 最终目录结构

```
<当前工作目录>/qwen_video/<日期>/<内容名称>/
├── original.mp4              # 原始视频
├── 拆解报告.md               # AI分析报告
├── 场景变化总览.jpg           # 全视频场景检测合成大图 (threshold=0.45)
├── 全视频时间轴总览.jpg       # 全视频每秒1帧合成大图
├── 场景检测/                 # 场景变化截图（原视频整体检测）
├── 全视频抽帧/               # 每秒1帧
└── 拆分/                     # 按时间段拆分
    ├── segment_000_0s-3s.mp4
    ├── segment_000_0s-3s/
    │   ├── 均匀抽帧/         # 每秒1帧
    │   └── 分镜总览_xxx.jpg  # 合成大图
    └── ...
```

---

## Stage 2: 分镜受控替换（视频复刻）

Stage 1 拆解完成后，如果用户想要"复刻"这条视频（换产品、换人物、换场景），进入 Stage 2。

### 触发条件

用户表达类似意图时进入此阶段：
- "我想用自己的产品复刻这条视频"
- "把里面的产品换成我的"
- "换个人拍同样的视频"
- "保持结构不变，换成我的场景"

### 流程

1. **确认替换项**：向用户确认产品、人物、场景三项分别是"替换"还是"沿用原样"
2. **收集素材**：用户要替换的项必须提供对应素材图（产品图/人物参考/场景参考），未提供则索要
3. **生成替换提示词**：根据 `references/storyboard-replacement-gptimage2.md` 中的规则和模板，构造 GPT-image2 的提示词
4. **调用 GPT-image2**：将原分镜大图 + 替换素材 + 提示词发送给 GPT-image2 生成新分镜
5. **校验输出**：检查新分镜的格子数量、构图、动作是否与原分镜对齐

### 核心原则

- 只替换用户指定的元素，其他一切保持原样
- 禁止改动构图、镜头角度、运镜、景别、人物动作、光影关系
- 新旧分镜格子数量必须一致（不一致时标记需要动作映射）
- 没有 GPT-image2 可调用时，只输出提示词和校验要求，等待用户外部生成

### 参考文档

详细的提示词模板、动态填充规则和校验清单见：`references/storyboard-replacement-gptimage2.md`

### 脚本使用

```bash
# 上传图片获取公网URL（内部工具，storyboard_replace.py 会自动调用）
python scripts/upload_image.py <图片路径>

# 分镜替换（至少指定一个替换项）
python scripts/storyboard_replace.py <原分镜大图路径> \
  --product <产品素材图> \
  --person <人物素材图> \
  --scene <场景素材图> \
  --output-dir <输出目录> \
  --size 1024x1024
```

示例：只替换产品

```bash
python scripts/storyboard_replace.py \
  "qwen_video/20260515/氨糖带货/场景变化总览.jpg" \
  --product "/path/to/my_product.png" \
  --output-dir "qwen_video/20260515/氨糖带货/"
```

智能体作为模块调用：

```python
from scripts.storyboard_replace import replace_storyboard

result_path = replace_storyboard(
    storyboard_path="qwen_video/20260515/氨糖带货/场景变化总览.jpg",
    product_path="/path/to/my_product.png",
    output_dir="qwen_video/20260515/氨糖带货/",
)
```

---

## 配置

在 `scripts/.env` 中配置百炼 API Key：

```
DASHSCOPE_API_KEY=sk-your-key-here
```

## 依赖

```bash
pip install requests openai python-dotenv Pillow
# 系统依赖
brew install ffmpeg  # macOS
```

## 注意事项

- 抖音CDN直链有时效性（约2小时），获取后尽快使用
- 视频分析使用 qwen3.6-plus 模型（已关闭思考模式）
- 场景检测对原视频整体运行一次，阈值 0.45（画面差异超过45%判定为新场景）
- 合成大图自动选择4-6列，算法确保最后一行尽量不空
- 仅供个人学习研究使用
