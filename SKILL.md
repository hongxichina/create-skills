---
name: video_teardown
description: 解析短视频分享链接并进行完整的视频内容拆解与复刻。Stage 1：提取无水印直链、AI分析视频内容（时间轴拆解、钩子分析、卖点提炼、口播转录）、下载视频、按时间段拆分、抽帧、场景检测、合成分镜大图。Stage 2：基于拆解出的分镜大图，使用 GPT-image2 进行受控替换（换产品/人物/场景，保持原视频结构不变）。Stage 3：将拆解报告整理为结构化动作骨架。Stage 4：整合所有材料，调用编排模型生成可直接发送给视频生成模型的最终 Video Prompt。Stage 5：当 Prompt 总时长超过15秒时，智能分段为多个≤15s的独立 Segment Prompt。Stage 6：调用云梦2.0 (seedance-2-0) 逐段生成视频。当用户提到"解析视频链接"、"拆解视频"、"分析这个视频"、"视频去水印"、"抖音链接"、"复刻视频"、"换产品重拍"、"分镜替换"、"视频翻拍"、"生成视频Prompt"、"编排视频指令"、"视频分段"、"生成视频"等场景时触发此技能。即使用户只是粘贴了一个短视频分享链接（如 v.douyin.com），也应触发。
---

# Video Teardown - 短视频内容拆解

## 概述

本技能提供完整的短视频拆解工作流：从一个分享链接出发，完成链接解析、AI内容分析、视频下载、按时间轴拆分、抽帧、场景检测、合成分镜大图的全流程。

## 前置条件

调用本技能前，智能体必须检查以下环境依赖是否满足。**如果检测到任何前置条件不满足，智能体应直接自动安装所需依赖，无需询问用户确认。**

### Python 版本

- **最低要求：Python 3.10**
- 原因：脚本使用了 `X | Y` 联合类型语法（PEP 604）和 `list[str]` 内置泛型语法（PEP 585）

检测命令：

```bash
python --version
```

如果版本低于 3.10，提示用户升级 Python。

### Python 依赖包

| 包名 | pip 安装名 | 用途 |
|------|-----------|------|
| requests | `requests` | HTTP 请求（抖音解析、文件上传、API 调用） |
| python-dotenv | `python-dotenv` | 环境变量管理（.env 文件加载） |
| openai | `openai` | OpenAI 兼容 API 客户端（百炼/DashScope） |
| Pillow | `Pillow` | 图片处理（抽帧合成、分辨率计算） |
| markdown | `markdown` | Markdown 解析为 HTML |
| python-docx | `python-docx` | Word 文档生成 |
| htmldocx | `htmldocx` | HTML 转 Word 文档 |

一键安装命令：

```bash
pip install requests python-dotenv openai Pillow markdown python-docx htmldocx
```

### 系统依赖

| 依赖 | 用途 | 检测命令 |
|------|------|----------|
| ffmpeg | 视频下载、拆分、抽帧、场景检测 | `ffmpeg -version` |
| ffprobe | 获取视频时长元数据 | `ffprobe -version` |

`ffmpeg` 和 `ffprobe` 必须在系统 PATH 中可用。

安装方式：

```bash
# Windows (winget)
winget install FFmpeg

# Windows (choco)
choco install ffmpeg

# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

### 环境变量

所有脚本通过 `scripts/.env` 加载配置。**`.env` 文件必须放在 `scripts/` 目录下**（与 `scripts/.env.example` 同级），参考 `.env.example` 创建。

#### 1. 阿里云百炼 API Key（`DASHSCOPE_API_KEY`）

用于视频内容分析（Stage 1）和 Video Prompt 编排（Stage 4）。

获取步骤：
1. 打开 [阿里云百炼控制台](https://bailian.console.aliyun.com/)
2. 登录后点击右上角头像 → **API-KEY 管理**
3. 创建新的 API Key，复制后填入 `DASHSCOPE_API_KEY`

#### 2. 云简平台配置（`YUNJIAN_BASE_URL` / `YUNJIAN_TOKEN` / `YUNJIAN_SITE_ID`）

用于图片/视频上传、GPT-image2 分镜替换（Stage 2）、Seedance 2.0 视频生成（Stage 6）。

获取步骤：
1. 登录云简控制台（`YUNJIAN_BASE_URL` 对应的平台地址）
2. 进入 **系统设置 → 系统令牌**，复制令牌填入 `YUNJIAN_TOKEN`
3. `YUNJIAN_SITE_ID` 填写你的站点 ID（通常为 `10000`，可在控制台 URL 或设置中查看）

#### 3. 飞书开放平台配置（`FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_USER_ID`）

用于将拆解报告自动上传到飞书文档。

**创建飞书应用步骤：**
1. 打开 [飞书开放平台](https://open.feishu.cn/app)，登录飞书账号
2. 点击「创建企业自建应用」，填写名称（如"视频拆解助手"）
3. 进入应用 → **凭证与基础信息**，复制 **App ID** 和 **App Secret**

**开通权限（必须）：**
进入应用 → **权限管理** → 搜索并开通以下权限：

| 权限标识 | 说明 |
|----------|------|
| `drive:drive` | 查看、评论、编辑和管理云空间中所有文件（上传文件、创建文件夹、导入文档） |

**发布应用：**
进入 **版本管理与发布** → 创建版本 → 提交发布（自建应用无需审核，立即生效）

**获取 `FEISHU_USER_ID`（用于自动共享文档给自己）：**

方法一（推荐）：
1. 打开飞书 → 点击左下角头像 → **个人信息**
2. 在 URL 中或通过飞书管理后台 → 组织架构 → 找到自己，查看 user_id

方法二（API 查询）：
```bash
# 用 App ID 和 App Secret 换取 token 后调用
curl -H "Authorization: Bearer <tenant_access_token>" \
  "https://open.feishu.cn/open-apis/contact/v3/users/me?user_id_type=user_id"
```
返回结果中的 `user_id` 字段即为所需值。

**`FEISHU_FOLDER_TOKEN`（可选）：**
留空则文档上传到应用根目录。如需指定文件夹，在飞书网页版打开目标文件夹，URL 中 `/folder/` 后面的字符串即为 folder token。

#### 完整 `.env` 示例

```ini
# 阿里云百炼（https://bailian.console.aliyun.com/）
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 云简平台
YUNJIAN_BASE_URL=https://your-yunjian-domain.com
YUNJIAN_TOKEN=yjsys-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
YUNJIAN_SITE_ID=10000

# 飞书开放平台（https://open.feishu.cn/app）
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_FOLDER_TOKEN=
FEISHU_USER_ID=xxxxxxxx
```

> **注意**：`.env` 文件必须放在 `scripts/` 目录下，即与 `scripts/.env.example` 同级。不要放在项目根目录。

### 自动检测与安装流程

智能体在首次调用本技能时，应执行以下检测流程：

```python
import subprocess, sys

# 1. 检测 Python 版本
assert sys.version_info >= (3, 10), "需要 Python 3.10+"

# 2. 检测并安装 Python 依赖
required_packages = [
    "requests", "python-dotenv", "openai", "Pillow",
    "markdown", "python-docx", "htmldocx"
]
subprocess.run([
    sys.executable, "-m", "pip", "install", *required_packages
], check=True)

# 3. 检测 ffmpeg
result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
if result.returncode != 0:
    raise EnvironmentError("ffmpeg 未安装，请先安装 ffmpeg 并确保在 PATH 中")

# 4. 检测 .env 配置
from pathlib import Path
env_path = Path("scripts/.env")
if not env_path.exists():
    raise FileNotFoundError("缺少 scripts/.env 配置文件，请参考 scripts/.env.example 创建")
```

如果 Python 依赖缺失，直接执行 `pip install` 安装；如果 ffmpeg 缺失，根据操作系统执行对应的安装命令；如果 `.env` 不存在，提示用户参考 `.env.example` 创建。

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
| `scripts/upload_feishu.py` | 通用 | 上传 .docx 到飞书文档 | 本地 .docx 文件路径 | 飞书在线文档 URL |

## 智能体编排流程

使用此技能时，智能体必须先获取当前对话的工作目录（即用户所在目录），所有产出保存到该目录下的 `qwen_video/` 中。

### 交互模式规则

**除非用户明确说"一次性跑完"或"全部执行"，否则智能体必须逐步执行，每完成一步后暂停，向用户展示本步产出，并询问下一步操作。**

完整步骤顺序如下：

```
Step 0: 确定工作目录
Step 1: 解析视频链接 / 上传本地视频
Step 2: AI 分析视频内容（生成拆解报告，自动上传飞书）
Step 3: 下载视频 + 按时间轴拆分 + 抽帧 + 合成分镜大图
Step 4: 结构化整理动作骨架（Stage 3）
Step 5: 分镜受控替换（Stage 2，需用户提供素材图）
Step 6: 编排最终 Video Prompt（Stage 4）
Step 7: 长视频 Prompt 分段（Stage 5，仅当总时长 > 15s）
Step 8: 生成视频（Stage 6）
```

每步完成后，智能体应：
1. 展示本步的关键产出（文件路径、飞书链接、分析摘要等）
2. 询问用户："接下来要执行哪一步？" 并列出可选的下一步

如果用户只是粘贴了一个视频链接，默认只执行 Step 1，完成后询问用户是否继续。

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

分析结果会打印到 stdout 并保存为该目录下的 `拆解报告.docx`，同时自动上传到飞书。

飞书文档的存放路径为：`<FEISHU_FOLDER_TOKEN 对应的根文件夹>/<YYYY-MM-DD>/<视频名称>/拆解报告.docx`

智能体在上传飞书前，需要先确保飞书目标文件夹存在。如果不存在，调用飞书创建文件夹 API 按 `<日期>/<视频名称>` 的层级创建。

```python
from scripts.upload_feishu import upload_docx_to_feishu

# 上传拆解报告到飞书
result = upload_docx_to_feishu(
    file_path="qwen_video/20260521/氨糖带货/拆解报告.docx",
    doc_name="拆解报告",
    folder_token="<日期/视频名称 对应的文件夹 token>",
)
print(result["url"])  # 飞书文档链接
```

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
├── 拆解报告.docx             # AI分析报告（同步上传飞书）
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

### 飞书文档目录结构

拆解报告上传到飞书后的目录结构：

```
<FEISHU_FOLDER_TOKEN 根文件夹>/
└── <YYYY-MM-DD>/
    └── <视频名称>/
        └── 拆解报告.docx     # 飞书在线文档
```

智能体在上传前需确保飞书目标文件夹按 `<日期>/<视频名称>` 层级存在，不存在则创建。

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
3. **选择原分镜图**：优先使用 `场景变化总览.jpg`（场景检测合成大图）；如果该文件不存在，则使用 `全视频时间轴总览.jpg`（全视频均匀抽帧合成大图）。**禁止使用** `拆分/` 目录下各片段的分镜总览图（如 `分镜总览_segment_000_0s-3s.jpg`）作为输入。
4. **生成替换提示词**：根据 `references/storyboard-replacement-gptimage2.md` 中的规则和模板，构造 GPT-image2 的提示词
5. **调用 GPT-image2**：将原分镜大图 + 替换素材 + 提示词发送给 GPT-image2 生成新分镜
6. **校验输出**：检查新分镜的格子数量、构图、动作是否与原分镜对齐

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
