---
name: video_teardown
description: 解析短视频分享链接并进行完整的视频内容拆解与复刻。Stage 1：提取无水印直链、AI分析视频内容（时间轴拆解、钩子分析、卖点提炼、口播转录）、下载视频、按时间段拆分、抽帧、场景检测、合成分镜大图。Stage 2：基于拆解出的分镜大图，使用 GPT-image2 进行受控替换（换产品/人物/场景，保持原视频结构不变）。Stage 3：将拆解报告整理为结构化动作骨架。Stage 4：整合所有材料，调用编排模型生成可直接发送给视频生成模型的最终 Video Prompt。Stage 5：当 Prompt 总时长超过15秒时，智能分段为多个≤15s的独立 Segment Prompt。Stage 6：调用云梦2.0 (seedance-2-0) 逐段生成视频。当用户提到"解析视频链接"、"拆解视频"、"分析这个视频"、"视频去水印"、"抖音链接"、"复刻视频"、"换产品重拍"、"分镜替换"、"视频翻拍"、"生成视频Prompt"、"编排视频指令"、"视频分段"、"生成视频"等场景时触发此技能。即使用户只是粘贴了一个短视频分享链接（如 v.douyin.com），也应触发。
---

# Video Teardown - 短视频内容拆解

## 概述

本技能提供完整的短视频拆解工作流：从一个分享链接出发，完成链接解析、AI内容分析、视频下载、按时间轴拆分、抽帧、场景检测、合成分镜大图的全流程。

## 脚本清单

| 脚本 | 阶段 | 功能 | 输入 | 输出 |
|------|------|------|------|------|
| `scripts/douyin_teardown.py` | Stage 1 | 解析抖音分享链接 | 分享URL | Markdown（标题、作者、直链、封面、点赞/评论/收藏） |
| `scripts/upload_video.py` | Stage 1 | 上传本地视频到云剪平台 | 本地视频路径 | 公网可访问视频URL |
| `scripts/video_analyze.py` | Stage 1 | AI视频内容拆解 | CDN直链/视频URL + 保存目录 | Markdown拆解报告（保存到指定目录） |
| `scripts/video_process.py` | Stage 1 | 下载+拆分+抽帧+合成大图 | CDN直链 + 时间段JSON + 名称 + 报告路径 + 工作目录 | 视频文件+分镜大图 |
| `scripts/upload_image.py` | Stage 2 | 上传本地图片到云间平台 | 本地图片路径 | 公网可访问URL |
| `scripts/storyboard_replace.py` | Stage 2 | GPT-image2 分镜受控替换 | 原分镜图 + 素材图（产品/人物/场景） | 替换后的新分镜图 |
| `scripts/generate_video_prompt.py` | Stage 4 | 编排最终 Video Prompt | 拆解报告 + 新分镜图URL + 产品图URL + 可选素材 | 最终视频生成Prompt |
| `scripts/segment_video_prompt.py` | Stage 5 | 长视频Prompt智能分段 | 最终Video Prompt文件 | 分段后的多个独立Segment Prompt |
| `scripts/generate_video.py` | Stage 6 | 云梦2.0视频生成 | Prompt文件 + 分镜图 + 产品图 + 可选人物/场景图 | 生成的视频文件(.mp4) |

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

## Stage 3: 视频结构化拆解整理

Stage 2 完成新分镜图后，需要将 Stage 1 的拆解报告整理为结构化的"动作骨架"，供 Stage 4 编排使用。

### 触发条件

Stage 2 新分镜图生成完毕后自动进入。

### 流程

智能体阅读 Stage 1 产出的 `拆解报告.md`，将【内容结构拆解】整理为标准化的 Panel 格式：

```
[Panel 1 | 0.00-3.00s] 核心动作、镜头类型、运镜、产品角色、转场
[Panel 2 | 3.00-8.00s] ...
...
```

每个 Panel 需要提取：
- 时间段
- 核心动作（begins / continues / ends）
- 动作速度与节奏（rapidly / quickly / naturally / steadily）
- 镜头类型（close-up / medium / wide）
- 运镜方式（static / push in / pull out / handheld）
- 产品使用方式与产品角色（hero product / proof object / comparison object / accessory）
- 转场方式（hard cut / continuous action / dissolve）

### 产出

整理后的结构化拆解结果保存为 `结构化动作骨架.md`，存放在视频目录下。

---

## Stage 4: 最终 Video Prompt 编排

将所有前序产出整合，生成可直接发送给视频生成模型的最终 Prompt。

### 触发条件

用户表达类似意图时进入此阶段：
- "生成视频 Prompt"
- "帮我编排最终的视频指令"
- "可以生成视频了"
- Stage 1-3 全部完成后，智能体主动询问是否进入此阶段

### 输入材料

| 材料 | 来源 | 必需 |
|------|------|------|
| 原视频结构化拆解结果 | Stage 3 产出 | 是 |
| 新分镜图 | Stage 2 产出 | 是 |
| 产品图 | 用户提供 | 是 |
| 人物参考图 | 用户提供 | 否 |
| 场景参考图 | 用户提供 | 否 |
| SRT 字幕 | 用户提供 | 否 |

### 编排规则

智能体使用 `references/final-prompt-orchestration-system.md` 作为系统提示词，`references/final-prompt-orchestration-user.md` 作为用户任务模板，将上述材料填入后调用编排模型生成最终 Prompt。

核心原则：
- **动作**跟 Stage 1/3 的拆解结果（时间、节奏、运镜、转场、产品交互）
- **画面外观**跟 Stage 2 的新分镜图（人物姿势、构图、场景）
- **产品外观**跟用户上传的产品图
- **声音**根据新分镜人物 + 视频风格自动推断（有 SRT 时）

### 输出格式

最终输出为结构化 Video Prompt：

```
[Video Prompt | 0.00-XX.XXs, Single Segment, Panels 1-X]

[Global Visual Context:
aspect ratio: vertical 9:16
scene: ...
lighting: ...
visual style: ...
camera baseline: ...
main subject: ...
product reference: the uploaded product image
storyboard reference: the uploaded storyboard grid
]

[Voice Setting:
voice: ...
audio: ...
subtitles: ...
SRT: ...
]

[Sequence Details:
[Panel 1 | 0.00-X.XXs | Storyboard Grid 1] ...
[Panel 2 | X.XX-X.XXs | Storyboard Grid 2] ...
...
]

[Negative Constraints]
...
```

### 参考文档

- 系统提示词：`references/final-prompt-orchestration-system.md`
- 用户任务模板：`references/final-prompt-orchestration-user.md`

### 产出

最终 Video Prompt 保存为 `最终视频Prompt.md`，存放在视频目录下。

---

## Stage 5: 长视频 Prompt 智能分段

当 Stage 4 生成的最终 Video Prompt 总时长超过 15 秒时，视频生成模型无法一次处理，需要智能分段。

### 触发条件

- Stage 4 产出的 Video Prompt 总时长 > 15.00s 时自动触发
- 用户说"帮我分段"、"视频太长了"

### 分段规则

- 每段不超过 15 秒
- 优先在 SRT 语义停顿处切分
- 其次在 Panel 边界、转场点、动作阶段结束处切分
- 禁止切断正在进行的核心动作
- 每段时间轴从 0.00s 重新开始
- Panel 编号和 Storyboard Grid 编号保留原始编号不重置
- SRT 时间码重新映射到本地时间轴
- 每段都是独立完整的 Prompt，可单独发给视频模型

### 脚本使用

```bash
python scripts/segment_video_prompt.py "qwen_video/20260515/氨糖带货/最终视频Prompt.md" \
  --output-dir "qwen_video/20260515/氨糖带货/"
```

### 参考文档

分段引擎完整规则：`references/long-video-prompt-segmentation.md`

### 产出

- 总时长 ≤15s：不分段，原样输出
- 总时长 >15s：输出 `分段视频Prompt.md`，包含分段策略说明 + 多个独立 Segment Prompt

---

## 完整工作流总览

```
[抖音分享链接]
      ↓
   Stage 1: 视频拆解
   （解析链接 → AI分析 → 下载 → 拆分 → 抽帧 → 合成分镜大图）
      ↓
[原分镜大图 + 拆解报告]
      ↓
[用户提供素材：产品图 / 人物图 / 场景图]
      ↓
   Stage 2: 分镜受控替换
   （GPT-image2 只换指定元素，保持结构不变）
      ↓
[新分镜大图]
      ↓
   Stage 3: 结构化拆解整理
   （将拆解报告整理为标准 Panel 动作骨架）
      ↓
[结构化动作骨架]
      ↓
   Stage 4: 最终 Video Prompt 编排
   （整合所有材料，生成可直接使用的视频生成指令）
      ↓
[最终 Video Prompt]
      ↓
   Stage 5: 智能分段（仅当总时长 > 15s）
   （按语义、Panel边界、转场点智能切分为 ≤15s 的独立段）
      ↓
[分段 Segment Prompts → 逐段发送给视频生成模型]
```

---

## Stage 6: 视频生成

将 Stage 4/5 产出的 Prompt + Stage 2 产出的新分镜图，发送给云梦 2.0 (seedance-2-0) 生成视频。

### 触发条件

- Stage 4/5 完成后，用户说"生成视频"、"开始生成"
- 智能体主动询问是否进入生成阶段

### 输入

| 材料 | 来源 | 必需 |
|------|------|------|
| 提示词（单段或分段 Prompt） | Stage 4/5 产出 | 是 |
| 分镜参考图 | Stage 2 产出的新分镜图 | 是 |
| 产品图 | 用户提供 | 是 |
| 人物参考图 | 用户提供 | 否 |
| 场景参考图 | 用户提供 | 否 |
| 时长 | 从 Prompt 自动检测或手动指定（4-15秒） | 是 |

### 固定参数

- 模型：seedance-2-0
- 分辨率：480p
- 画幅：9:16
- 声音：开启
- 模式：allround（参考图模式）

### 脚本使用

```bash
# 自动检测时长，逐段并发生成（分镜图 + 产品图 必传）
python scripts/generate_video.py "分段视频Prompt.md" "新分镜_替换后.png" "产品图.png" --output-dir "输出目录/"

# 带人物和场景参考图
python scripts/generate_video.py "分段视频Prompt.md" "新分镜_替换后.png" "产品图.png" \
  --person "人物.png" --scene "场景.png" --output-dir "输出目录/"

# 手动指定时长（单段）
python scripts/generate_video.py "最终视频Prompt.md" "新分镜_替换后.png" "产品图.png" --duration 10 --output-dir "输出目录/"
```

### 产出

每个 Segment 生成一个 `segment_N.mp4` 视频文件，保存到输出目录。

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
