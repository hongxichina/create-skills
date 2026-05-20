# 最终 Video Prompt 编排用户任务模板

用于 Stage 4。将 Stage 3 产出的 `Original Video Breakdown`、Stage 2 产出的新分镜图、可选产品图、可选人物/场景参考图、可选 SRT 填入后，作为用户提示词发送给编排模型。

如果用户没有提供产品图，不要写 `the uploaded product image`；改为说明产品外观以 `the uploaded storyboard grid` 中可见产品为准。人物图、场景图同理。

```markdown
请根据以下输入，生成一段可以直接发送给视频生成模型的最终 Video Prompt。

---

# Task

基于：

1. 原视频结构化拆解结果
2. 新分镜拼图 / 新分镜图
3. 产品图
4. 人物参考图，可选
5. 场景参考图，可选
6. SRT 字幕，可选

生成最终视频生成 Prompt。

注意：

当前任务不是原视频拆解。

当前任务是第二阶段：新分镜视频生成 Prompt 编排。

你需要把第一阶段原视频拆解结果中的动作骨架，迁移到新分镜拼图对应的画面里。

核心原则：

动作跟第一阶段。
画面跟新分镜。
产品外观跟产品图。
声音根据新分镜人物和视频风格自动判断。

也就是说：

- 第一阶段拆解结果决定每个 Panel 的核心动作、动作节奏、产品使用方式、产品角色、运镜和转场
- 新分镜拼图决定每个 Panel 的最终人物形象、姿势、表情、手部位置、构图和画面内容
- 产品图决定最终产品外观
- 如果有 SRT，Voice Setting 需要根据新分镜人物和视频风格，自动给出声音描述

最终 Prompt 必须是正向生成语言，而不是替换过程说明。

---

# Input Assets

## 1. Original Video Breakdown

原视频拆解结果用于提取并强继承：

- 总时长
- Panel 数量
- 每个 Panel 的时间段
- 每个 Panel 的核心动作
- begins / continues / ends 动作阶段
- 动作速度与节奏
- 运镜方式
- 镜头类型
- 转场方式
- 产品使用方式
- 产品与人物 / 手部 / 口腔 / 纸巾 / 配件之间的交互关系
- 产品角色
- 产品展示节奏
- 构图变化节奏
- 场景切换关系

原视频拆解结果只提供“视频动作骨架”和“时间结构”。

禁止把原人物、原产品、原品牌信息直接写入最终生成 Prompt。

但是，原视频拆解结果中的动作、节奏、交互关系、产品角色必须继承。

请在下方粘贴原视频拆解结果：

【Original Video Breakdown】
在这里粘贴原视频结构化拆解结果

---

## 2. Uploaded Storyboard Grid

新分镜拼图用于确定最终画面：

- 人物外观
- 人物姿势
- 表情
- 视线方向
- 手部位置
- 身体姿态
- 产品佩戴方式
- 产品展示位置
- 画面构图
- 镜头顺序
- 场景视觉内容

必须严格按照新分镜拼图的格子顺序生成。

当新分镜图为拼图 grid 时，按照以下顺序编号：

- 从左到右
- 从上到下

例如：

第一行：Grid 1, Grid 2, Grid 3, Grid 4
第二行：Grid 5, Grid 6, Grid 7, Grid 8
第三行：Grid 9, Grid 10, Grid 11, Grid 12

【Storyboard Grid】
用户已上传新分镜拼图 / 新分镜图

---

## 3. Uploaded Product Image

产品图用于确定最终产品外观。

必须将产品图称为：

the uploaded product image

禁止称为：

- image_0.png
- image_1.png
- image_2.png
- first image
- second image

产品图是产品外观的唯一参考。

不得擅自改变产品的：

- 颜色
- 材质
- 形状
- 大小比例
- 图案
- 结构
- 佩戴方式
- 核心设计特征

【Product Image】
用户已上传产品图

---

## 4. Optional Model Reference Image

如果用户上传了人物参考图，则称为：

the uploaded model reference image

人物参考图只用于人物外观参考。

如果没有上传人物参考图，则以 uploaded storyboard grid 中的人物为准。

【Model Reference Image】
如有，请使用用户上传的人物参考图；如无，则忽略。

---

## 5. Optional Scene Reference Image

如果用户上传了场景参考图，则称为：

the uploaded scene reference image

场景参考图只用于场景风格参考。

如果没有上传场景参考图，则以 uploaded storyboard grid 中的场景为准。

【Scene Reference Image】
如有，请使用用户上传的场景参考图；如无，则忽略。

---

## 6. Optional SRT

如果用户提供 SRT，则需要保留口播。

如果用户没有提供 SRT，则必须默认：

voice: no voiceover

并且禁止添加：

- 口播
- 字幕
- floating text
- captions
- slogan
- price tag
- app UI
- watermark

【SRT】
如果有 SRT，在这里粘贴。
如果没有 SRT，请按无口播处理。

---

# Strong Action Inheritance Rules

原视频结构化拆解结果不是普通参考，而是最终 Prompt 的动作骨架来源。

第二阶段生成时，必须强继承第一阶段每个 Panel 中已经识别出的：

1. 主体动作
2. 动作阶段：begins / continues / ends
3. 动作速度与节奏：rapidly / quickly / naturally / steadily / smoothly
4. 产品使用方式
5. 产品与人物 / 手部 / 口腔 / 纸巾 / 配件之间的交互关系
6. 产品角色：hero product / proof object / comparison object / accessory / usage tool / packaging
7. 运镜方式
8. 转场方式
9. 场景切换关系

新分镜图只用于确定最终画面的：

- 人物外观
- 人物姿势
- 表情
- 头部角度
- 视线方向
- 手部位置
- 构图
- 镜头远近
- 场景画面锚点

禁止用新分镜图覆盖或弱化第一阶段已经明确识别出的动作事件。

尤其禁止将第一阶段中的具体动作降级为泛化动作。

---

# Forbidden Action Downgrade Rules

第二阶段不得把第一阶段中的具体动作改写成更模糊的动作。

禁止以下降级：

- spraying water into open mouth → holding water flosser near face
- spraying tissue / toilet paper → holding product over sink
- using floss pick on teeth → holding small tool near mouth
- presenting metal tongue scraper close to camera → showing small tool
- holding up four clear attachments → holding a small clear attachment
- holding up gray travel bag → holding an accessory
- pointing downward toward the camera → smiling while holding product
- product proof demonstration → hero product display
- comparison object → accessory / hero product
- accessory demonstration → generic product display
- rapidly / quickly → naturally / steadily

如果第一阶段已经明确写出动作、对象、产品角色、节奏词，第二阶段必须保留。

可以替换的只有：

- person → model
- hand A / hand B → hand A / hand B 或 model's hand，必须保持清晰
- 原产品外观 → the uploaded product image 中的产品外观
- 原人物外观 → uploaded storyboard grid / model reference 中的人物外观
- 原场景外观 → uploaded storyboard grid / scene reference 中的场景外观

---

# Correct and Incorrect Examples

错误示例：

第一阶段：
person begins spraying water into open mouth rapidly

第二阶段错误：
model opens his mouth wide holding the water flosser near his face

第二阶段正确：
model begins spraying water into his open mouth rapidly with the water flosser, while preserving the pose and composition shown in storyboard grid 1

---

错误示例：

第一阶段：
hand A begins holding toilet paper while hand B sprays it with water flosser, product role: proof object

第二阶段错误：
hand A holds a piece of white paper while hand B sprays it with the water flosser, product role: hero product

第二阶段正确：
hand A begins holding toilet paper while hand B sprays it with the water flosser as a proof demonstration, product role: proof object, while preserving the hand layout and composition shown in storyboard grid 3

---

错误示例：

第一阶段：
person begins presenting a metal tongue scraper close to the camera quickly, product role: comparison object

第二阶段错误：
model presents a small tongue scraper tool close to the camera

第二阶段正确：
model begins presenting the metal tongue scraper close to the camera quickly, product role: comparison object, while preserving the hand position and pose shown in storyboard grid 18

---

# Panel Quantity Rules

最终输出的 Panel 数量必须等于新分镜拼图中的格子数量。

必须：

1. 每一个分镜格子 = 一个 Panel
2. 不得合并 Panel
3. 不得跳过 Panel
4. 不得改变 Panel 顺序
5. 不得把多个格子压缩成一个 Panel
6. 不得根据原视频镜头结构反向合并新分镜
7. 不得重新编号 Panel
8. 不得重新编号 Storyboard Grid

---

# Timing Rules

每个 Panel 的时间段应优先继承原视频拆解结果中的对应 Panel 时间。

如果原视频拆解结果中已有：

[Panel 1 | 0.00-0.80s]
[Panel 2 | 0.80-1.60s]

则最终生成 Prompt 中必须保持相同时间段。

禁止平均分配时间。

如果新分镜格子数量与原视频拆解 Panel 数量一致，则一一对应。

如果数量不一致，则根据以下优先级重新映射：

1. 动作阶段
2. 构图变化
3. 产品展示变化
4. 手部位置变化
5. 人物姿势变化
6. 视线变化
7. 转场变化
8. 节奏变化

数量不一致时必须遵守：

1. 最终输出 Panel 数量必须等于新分镜格子数量。
2. 不要把数量不一致伪装成一致。
3. 不要机械删除关键动作。
4. 需要减少 Panel 时，只能合并相邻、同功能、同动作阶段或同语义段落的动作骨架。
5. 合并后仍必须保留第一阶段的核心动作、产品角色、节奏、运镜和转场逻辑。
6. 如果一个新分镜格子承载多个原始动作阶段，需要在一个 Panel 句子中自然串联，但不能写成分析说明。
7. 仍然禁止平均分配时间；时间段应覆盖完整视频并保持连续。

---

# Global Visual Context Rules

如果所有 Panel 共享相同的：

- 场景
- 光照
- 画面质感
- 拍摄风格
- 主体人物
- 产品
- 整体视觉调性

则必须统一写入：

[Global Visual Context]

Panel 内禁止重复写以下全局信息：

- indoor room area
- bathroom sink area
- bright indoor lighting
- TikTok UGC handheld mobile video texture
- front-camera selfie style
- vertical 9:16
- clean product commercial look

除非某个 Panel 的场景、光照、画面风格发生明显变化，否则 Panel 内只描述：

- 镜头变化
- 构图变化
- 继承自第一阶段的核心动作
- 人物动作
- 视线方向
- 手部位置
- 产品展示方式
- 产品角色
- 转场方式

---

# Storyboard Fidelity Rules

每个 Panel 必须以对应的新分镜格子为最终画面锚点。

必须保留新分镜格子中的：

- 人物姿势
- 人物表情
- 头部角度
- 视线方向
- 手部位置
- 产品位置
- 产品佩戴方式
- 身体姿态
- 构图比例
- 镜头远近
- 前后景关系
- 场景布局

禁止新增新分镜格子中没有明确出现、且第一阶段动作骨架中也没有要求的内容。

禁止擅自增加：

- 额外人物
- 额外产品
- 额外饰品
- 额外道具
- 额外文字
- 额外品牌 Logo
- 额外场景
- 夸张表情
- 夸张动作
- 过度眼部特写
- 第一阶段和新分镜中都不存在的产品使用方式

---

# Panel Fidelity Rules

每个 Panel 只能描述：

1. 第一阶段对应 Panel 中已经明确识别出的动作、节奏、产品角色、运镜和转场
2. 新分镜对应格子中明确可见的姿势、表情、手部位置、视线、构图和场景画面
3. 产品图中明确可见的产品外观

禁止新增以下内容：

- 分镜中没有明确出现、且第一阶段也没有要求的眼部极近特写
- 分镜中没有明确出现、且第一阶段也没有要求的情绪强度
- 分镜中没有明确出现、且第一阶段也没有要求的动作幅度
- 分镜中没有明确出现、且第一阶段也没有要求的产品位置
- 分镜中没有明确出现、且第一阶段也没有要求的构图变化
- 产品图中没有明确出现的产品功能
- 用户没有提供的品牌信息

---

# Product Description Rules

产品必须严格参考 the uploaded product image。

如果产品在新分镜中被佩戴、拿起、展示或使用，必须描述其画面位置和使用方式。

例如：

- water flosser sprays water into the model's open mouth
- water flosser sprays the tissue as a proof demonstration
- product remains held near the model's face
- attachment is shown close to the camera
- travel bag is held up in front of the camera
- product remains visible in the same position as shown in the storyboard grid cell

禁止擅自扩写产品功效。

禁止写：

- improves beauty
- makes the model elegant
- premium quality
- luxury craftsmanship
- best-selling
- branded
- expensive

除非用户明确提供这些信息。

---

# Product Role Rules

如果第一阶段已经识别产品角色，第二阶段必须优先保留。

产品角色包括：

- hero product
- worn product
- close-up product
- detail product
- supporting accessory
- proof object
- comparison object
- usage tool
- packaging

写法示例：

- product role: hero product
- product role: proof object
- product role: comparison object
- product role: accessory
- product role: usage tool

如果当前 Panel 没有明显产品出现，则不强行添加 product role。

禁止将第一阶段的 proof object / comparison object / accessory 全部泛化成 hero product。

---

# Camera Rules

每个 Panel 必须继承原视频拆解结果中的运镜骨架，但最终画面必须服从新分镜格子。

运镜描述必须清晰、可执行。

优先使用原视频拆解结果中的 camera 描述。

可使用以下表达：

- handheld front-facing camera with slight natural shake
- handheld follow shot
- static camera
- slow push in
- slow pull out
- slow tilt down
- slow tilt up
- stable close-up framing
- stable medium framing
- framing slightly tightens
- framing slightly widens
- steady close framing maintained

禁止使用模糊表达：

- cinematic movement
- beautiful camera
- luxury camera
- dynamic camera
- professional camera

---

# Shot Type Rules

镜头类型优先结合：

1. 第一阶段拆解结果中的 shot type
2. 新分镜格子的实际构图

如果两者冲突，以新分镜格子的真实构图为准，但不能因此删除第一阶段动作。

镜头类型可用：

- extreme close-up
- close-up
- medium close-up
- medium
- wide

禁止因为原视频是 close-up，就强行把新分镜也写成 close-up。

也禁止因为新分镜构图变化，就删除第一阶段已识别出的核心动作。

---

# Transition Rules

转场用于描述当前 Panel 到下一个 Panel 的连接方式。

必须优先继承原视频拆解结果中的转场。

可使用以下转场：

- continuous action
- hard cut
- jump cut
- match cut
- dissolve
- blur transition
- slide transition
- light leak
- glitch
- whip-pan transition
- motion blur transition
- hand-cover transition
- product-cover transition
- fade in
- fade out
- end

如果是明显剪辑效果，不能只写标签，必须写清楚画面如何变化。

错误：

transition: dissolve

正确：

transition: the current frame gradually fades out while the next frame fades in, smooth dissolve

错误：

transition: blur

正确：

transition: the frame becomes softly blurred, then resolves into the next storyboard grid cell, fast blur transition

如果只是连续动作，则写：

transition: continuous action

最后一个 Panel 必须写：

transition: end

---

# SRT Field Rules

如果用户提供 SRT，必须将 SRT 放在独立字段：

SRT:

不得放在 subtitles 字段下。

subtitles 字段只用于说明画面中是否显示字幕。

如果不希望画面显示字幕，必须写：

subtitles: none visible in the generated frames

正确格式：

[Voice Setting:
voice: young adult male-presenting voice
voice tone: clear, casual, energetic, slightly nasal, direct
delivery style: fast-paced TikTok UGC direct-to-camera product demo delivery
audio: clean spoken voiceover matching the SRT timing, no background music, no extra ambient noise
subtitles: none visible in the generated frames
SRT:
100
00:00:04,480 --> 00:00:06,520
if you got white tongue dead giveaway
]

---

# Voice Description Rules

如果用户提供了 SRT，需要在 Voice Setting 中自动补充适合新视频人物的声音描述。

声音描述应根据：

1. uploaded storyboard grid 中的人物可见特征
2. uploaded model reference image，如有
3. 视频风格，如 TikTok UGC / 高级商业广告 / 口播测评 / 产品演示
4. SRT 文案的语气与节奏

综合判断。

Voice Setting 中必须包含：

- voice:
- voice tone:
- delivery style:
- audio:
- subtitles:
- SRT:

禁止根据人物外观直接推断敏感身份。

禁止写：

- Black male voice
- Asian female voice
- Latino voice
- native speaker
- American native voice
- British native voice

除非用户明确要求具体口音或身份标签。

---

# Voice Rules

如果用户没有提供 SRT，必须输出：

[Voice Setting:
voice: no voiceover
audio: no background music, no extra ambient noise
subtitles: none
]

并且禁止在 Panel 中添加任何口播、字幕或文字。

禁止写：

- voiceover says
- narrator says
- subtitle appears
- text overlay
- caption
- slogan
- CTA text

如果用户提供 SRT，则必须：

1. 保留 SRT 原文
2. 不改写口播内容
3. 不新增口播内容
4. 不在每个 Panel 中重复口播
5. 只在 Voice Setting 或独立 Voiceover Section 中保留 SRT
6. subtitles 字段必须写 none visible in the generated frames，除非用户明确要求画面显示字幕
7. audio 字段必须写：clean spoken voiceover matching the SRT timing, no background music, no extra ambient noise
8. 根据新分镜人物和视频风格，自动补充 voice、voice tone、delivery style

Panel 内不写具体字幕内容，除非用户明确要求逐 Panel 对齐。

---

# Output Language Rules

最终 Prompt 建议使用英文输出，因为大多数视频生成模型对英文视频指令理解更稳定。

但结构标题可以保留英文。

禁止中英混杂地描述同一个 Panel。

如果输出英文，则所有 Panel 描述都必须是英文。

---

# Output Structure

必须严格按照以下结构输出：

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
voice tone: ...
delivery style: ...
audio: ...
subtitles: ...
SRT:
...
]

[Sequence Details:

[Panel 1 | 0.00-X.XXs | Storyboard Grid 1] ...
[Panel 2 | X.XX-X.XXs | Storyboard Grid 2] ...
[Panel 3 | X.XX-X.XXs | Storyboard Grid 3] ...
...

]

[Negative Constraints]
...

---

# Panel Sentence Format

每个 Panel 必须优先继承第一阶段动作，再叠加新分镜画面锚点。

推荐格式：

[Panel X | start-end | Storyboard Grid X] [shot type inherited/adapted from the breakdown], [camera movement inherited from the breakdown], [core action inherited from the original breakdown], while preserving the exact pose, hand position, gaze direction, framing, and composition shown in storyboard grid X, [product position / product role inherited from the breakdown if visible], transition: [transition inherited from the breakdown]

注意：

1. core action 必须来自第一阶段对应 Panel。
2. storyboard grid 只作为画面锚点，不得替代 core action。
3. product role 优先继承第一阶段。
4. transition 优先继承第一阶段。
5. camera movement 优先继承第一阶段。
6. Panel 内不要重复 Global Visual Context 中已经写过的信息，除非场景或画面风格发生变化。

---

# Negative Constraints Rules

Negative Constraints 只写视频模型真正需要避免的内容。

推荐保留以下约束：

[Negative Constraints]
Do not merge storyboard grid cells.
Do not skip any storyboard grid cell.
Do not change the storyboard grid order.
Do not renumber Panels.
Do not renumber Storyboard Grid cells.
Do not change the original Panel timecodes.
Do not change the product design shown in the uploaded product image.
Do not weaken or downgrade the core actions inherited from the original video breakdown.
Do not turn specific product usage actions into generic holding or showing actions.
Do not change product roles inherited from the breakdown, such as proof object, comparison object, accessory, usage tool, or hero product.
Do not invent additional jewelry, accessories, people, props, text, logos, or subtitles.
Do not change the model's pose, hand position, gaze direction, or composition shown in each storyboard grid cell.
Do not add subtitles, floating text, watermark, app UI, logo, slogan, or price tags unless requested.
Do not add voiceover if no SRT is provided.
Do not place SRT under the subtitles field.
Do not add background music.
Do not add extra ambient noise.
Do not add shaky handheld movement unless specified.
Do not over-zoom into the eyes or product beyond the framing shown in the storyboard grid.
Do not use abstract emotional exaggeration; keep movements visually faithful to the storyboard grid and actions faithful to the breakdown.

---

# Forbidden Final Output Content

最终输出中禁止出现：

- 对任务的解释
- 对原视频的分析
- “我将会”
- “以下是”
- “这个 Prompt”
- “复刻”
- “替换”
- “迁移”
- “原视频”
- “原人物”
- “原产品”
- “image_0.png”
- “image_1.png”
- “matching the intensity”
- “perfectly replicate”
- 主观评价
- 无依据的品牌信息
- 无依据的产品功效
- 过度文学化描述

---

# Final Self-Check

输出前必须检查：

1. Panel 数量是否等于新分镜拼图格子数量
2. Panel 顺序是否严格从左到右、从上到下
3. Panel 时间是否继承原视频拆解结果
4. 时间是否连续、无重叠、无断层
5. 是否使用了 Global Visual Context 压缩重复视觉信息
6. Panel 内是否避免重复全局场景、光照、风格
7. 是否删除了原视频、原人物、原产品相关表述
8. 是否没有出现 image_0.png / image_1.png
9. 是否统一使用 the uploaded product image
10. 是否统一使用 the uploaded storyboard grid
11. 是否每个 Panel 都锚定对应 storyboard grid cell
12. 是否每个 Panel 都强继承了第一阶段对应 Panel 的核心动作
13. 是否没有把具体动作降级成泛化动作
14. 是否保留了 begins / continues / ends 动作阶段
15. 是否保留了 rapidly / quickly / steadily / naturally 等动作节奏词
16. 是否保留了产品使用方式
17. 是否保留了产品角色，如 proof object / comparison object / accessory / hero product
18. 是否保留了人物姿势、手部位置、视线方向和构图
19. 是否保留了原视频拆解中的运镜和转场骨架
20. 如果有 SRT，是否放在独立 SRT 字段
21. 如果有 SRT，subtitles 是否写 none visible in the generated frames
22. 如果有 SRT，是否根据新分镜人物和视频风格自动补充了 voice、voice tone、delivery style
23. 如果有 SRT，audio 是否写 clean spoken voiceover matching the SRT timing, no background music, no extra ambient noise
24. 如果没有 SRT，是否明确 voice: no voiceover
25. 如果没有 SRT，audio 是否写 no background music, no extra ambient noise
26. 是否没有添加字幕、文字、水印、Logo、价格标签
27. Negative Constraints 是否只保留视频模型可理解的约束
28. 最终输出是否可以直接发送给视频生成模型使用

如果不符合，必须自动修正后再输出。

---

# Execution Requirement

请严格按照指定结构输出最终 Video Prompt。

不要添加任何解释说明。

不要输出分析过程。

不要输出原视频拆解过程。

只输出可以直接发送给视频生成模型的最终视频生成 Prompt。
```
