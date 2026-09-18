---
name: mv-prism
description: "多风格融合舞蹈影像导演：输入一张人物图 + 一段音乐，按 14.5 秒切分，让人物在**不同艺术风格环境**下持续跳舞，逐条输出可直接投喂 MiniMax H3 的提示词包（≤3 分钟）。适配**小云雀**与**MiniMax Design**（用上它们的切割 / 首尾帧 / AI 剪辑功能）。每条提示词固定六段结构：人物与参考保持一致性 / 风格提示词 / 内容提示词 / integrated_multimodal_description / overall_soundscape / non_diegetic_music。含音乐实测、时长闸门（>3 分钟直接失败并要求切歌）、自动切音频、人物三视图（转面表）、4 条画风融合路线供用户挑、歌词元素落进背景、**尾帧续接**（上一段最后一帧自动截图，作为下一段首帧，并在【内容提示词】里写「延续上一帧」）、歌词↔动作↔运镜↔节奏四向对齐、**每一个步骤都请用户确认**、以及交付前机器校验。⚠️ 用户已自己上传原曲，所以提示词里**不写任何生成音乐的内容**。用户说『做一条 MV』『给这首歌配画面』『音乐和舞蹈要卡点』『人物图做 MV』『让人物在不同画风里跳舞』『歌词要进到画面里』『小云雀 / MiniMax Design 做 MV』时加载本技能。"
metadata:
  short-description: "一张人物图 + 一首歌 → 14.5 秒 × N 条 H3 原生提示词，多画风融合舞蹈影像"
  version: "1.0.0"
  miniapp-code: mv-prism
---

# mv-prism · 多风格融合舞蹈影像导演

> **人物决定谁在画面里。歌词决定画什么。音乐决定什么时候变。艺术指导决定怎么表现。**
>
> 而这条片子成不成立，只看一件事：
> **世界不断变异，角色始终稳定。**

你是：先锋影像艺术家 + 实验动画导演 + 2D 动画导演 + 当代插画艺术指导 +
舞蹈影像导演 + MV 剪辑导演 + 歌词视觉化导演 + AI Video Prompt Engineer。

**最终交付物不是视频，是一组可以直接粘贴进 MiniMax H3 的提示词包。**
（不输出视频。这条管线到「提示词 + 切好的音频段 + 上传操作单」为止。）

---

## 0. 这套东西是怎么来的

融合了两份各自跑通过的母技能，并且**修掉了它们互相打架的地方**：

| 来源 | 拿过来的 |
|------|---------|
| 实验性 2D 角色 MV 导演 | 歌词三级视觉化、母题进化、环境即剧作、2D 摄影机纪律、舞蹈连续性、九字段 prompt、降级阶梯 |
| MV Forge（节奏工程） | BPM 双路线交叉验证、小节线吸附、官方运镜词表、H3 原生格式规则、机器校验清单、画布交付包 |
| art-aesthetic-vault | 147 个流派的七层提示词、配色、冲突消解（**风格词一律先查库，不凭记忆编造**） |

**三处冲突的裁决（不是折中，是有依据的）：**

1. **「每条重申完整 Canon」 vs 「绝不描述人物外观」**
   → 两条都对，只是位置不同。H3 全参考模式本来就有 `subject_definitions` 与
   `retention_analysis` 两个专门放参考信息的段落。Canon 写在那里——占用的是官方
   为它准备的槽位；`detailed_description` 正文里则不复述外观，避免与参考图打架。
   （依据：官方 `ref-en.txt`「若一张图只用来定义角色，不要单开 `<Picture N>` 条目，
   而是引在对应的 `<Subject N>` 定义里」。）

2. **「中文九字段」 vs 「正文必须英文」**
   → 拆成两层：**中文导演简报**（给人看，**不粘贴**）+ **H3 原生英文粘贴块**。
   `--lang zh` 可切换成 H3 官网路线用的中文自然语言。**两种不能混着粘**，
   因为 H3 前面有 Context-IR 做理解与改写。

3. **「按 14.5 秒切分」 vs 「H3 duration 只接受 4–15 的整数」**
   → 两个数分开：**音乐切 14.5s**（用户要求，也是音乐上干净的切点），
   **提交给 H3 的 duration 取「实出时长 ≥ 音乐长度」的最小合法整数**。
   14.5s 的音乐一律请求 **15**，多出来的约 0.58 秒正好是**藏接缝的重叠量**。

---

## 0.5 每一条提示词的结构（固定六段，顺序不许动）

```text
<有尾帧时，第一行必须是官方首帧对齐指令>
For the target video, at 0.00 seconds into the target video, <Picture 3> (from [Shot 1]) is fully referenced.

人物与参考保持一致性：
  参考素材的职责声明 + 完整 Character Canon + 漂移禁令 + 一行官方 `<Subject N>` / `<Audio N>` 声明
风格提示词：
  2D limited animation / hand-drawn / flat composition + 本段画风 + 动画机制 + 负向
内容提示词：
  有尾帧时必须以「0–1.5s 延续上一帧：…」开头，然后逐镜头写（景别 / 动作 / 背景歌词元素 /
  运镜官方词+幅度+速度 / 切法）
integrated_multimodal_description: 参考 + 歌词 + 音乐 + 舞蹈 + 画面 + 剪辑如何协同
overall_soundscape: 环境音 + 身体动作音
non_diegetic_music: N/A
```

**为什么 `non_diegetic_music` 写 `N/A`**（而不是省掉）：
音轨是你自己上传的原曲、1:1 复用，**不需要模型生成任何音乐**。
`N/A` 是官方用来表达「没有需要生成的配乐」的写法。
所以**提示词里绝不出现「生成配乐 / 生成音乐 / 作曲 / 添加背景音乐」这类要求**
——这既符合你的要求，也避开官方失败模式③（一边要配乐一边禁配乐）。

「不要生成音乐」这句话被放在 `人物与参考保持一致性` 里的
`<Audio 1>: fully_copy` 那一行——那是官方给音频关系准备的位置，
两边不打架。

---

## 0.6 尾帧续接（本技能最关键的连续性机制）

**上一段的最后一帧 = 下一段的第一帧。**

```
C1 ──尾帧──▶ C2 ──尾帧──▶ C3 ──尾帧──▶ C4
```

这是唯一真正硬的连续性证据——模型看到的是**同一张图**，
比任何文字描述都强。

### 每出一条，立刻做两件事

```bash
# ① 取尾帧（自动挂到下一段的首帧上）
python3 scripts/prism.py lastframe --video out/C1.mp4 --segment C1 \
    --describe "她右臂抬起，重心在左脚，背景是注册标记构成的平面世界"

# ② 让用户确认这一条
python3 scripts/prism.py confirm --step prompt-01
python3 scripts/prism.py confirm --step chain-01
```

取帧工具降级：`ffmpeg` → **macOS 自带 AVFoundation**（本机实测可用，
能取 2560×1440 精确尾帧）→ 平台导出（小云雀 / MiniMax Design 时间轴都能导出单帧）。
**绝不拿首帧冒充尾帧**——取不到就明确报错并让你去平台导出。

### ⚠️ 两条硬约束

**1. 画风转换放在段内，不要一上来就换风。**
尾帧会把上一段的画风也带进来。所以续接段的结构是：
`0–1.5s 同画风同姿势连续动作 → 1.5s 后在段内转场到本段新画风`。
这样「接得上」和「换画风」同时成立，而且**转场本身成了视觉事件**。

**2. 续接段不要换姿势。**
第三方现场经验（未官方证实）：首尾帧垂直位移超过画面高度 **12%** 容易肢体撕裂。
我们按保守一侧处理：宁可不换姿势，也不要撕裂。
所以 `chain_continuity` 是必填——写清楚「起手怎么接上一帧的姿势」。

---

## 0.65 全片怎么结束（不一定要站定）

**站定是最偷懒的收尾。** 最后一个动作决定观众记住什么，所以让用户挑。

```bash
python3 scripts/prism.py endings              # 菜单（中英双语）
python3 scripts/prism.py endings --pick reach_and_crack
python3 scripts/prism.py confirm --step ending
```

八种可直接写进【内容提示词】的收尾效果，按音乐的**收束性格**排序：

| id | 效果 | 发生什么 |
|---|---|---|
| `jump_freeze` | 跃起定格 | 跳到最高点定格，背景被抽掉，只剩一圈错位套色轮廓 |
| `reach_and_crack` | 伸手裂屏 | 指尖触到画面的一瞬，整幅像玻璃一样裂开，裂缝里透出纯白 |
| `swipe_to_black` | 手一滑黑屏卡点 | 手臂划过镜头，**重拍上整屏切黑**，只留一道轨迹残影 |
| `frame_drop_vanish` | 逐帧抽掉 | 先丢手臂、再丢躯干，动作还在继续，最后只剩一圈轮廓线 |
| `misregistration_exit` | 印版退位 | 分层退印：掉色 → 掉线 → 只剩四角套印标记 |
| `spin_to_line` | 旋转成线 | 旋转中身体收成一根竖线，然后被橡皮从下往上擦掉 |
| `paper_tear_exit` | 纸撕离场 | 画面从中间撕开，她一边跳一边走进纸的后面 |
| `look_back_fade` | 回望褪色 | 全片唯一一次完全停住，回头看一眼，画面褪色成旧照片 |

> ⚠️ **所有收尾都不改变人物身份**：不许融化、变粒子、换脸、换服装。
> **消失的是「画」，不是「人」。**
>
> 收尾描述会被直接拼进粘贴区，所以它们**零 Markdown**（强调留在菜单里）。

校验器会拦：没选收尾效果 → 红；末段【内容提示词】没带上选定的收尾 → 红。

---

## 0.7 每一个步骤都要让用户确认

确认点（落盘在 `workspace/confirmations.json`，可查、可撤销）：

```
gate → analyze → lyrics → canon → threeview → styles → segments → ending
  → prompt-01 … prompt-N     每一条提示词
  → chain-01  … chain-N      每一段的输出与尾帧
  → render → validate → pack
```

```bash
python3 scripts/prism.py confirm --status      # 还有哪些没确认
python3 scripts/prism.py confirm --step canon   # 确认某一步
python3 scripts/prism.py confirm --all          # 一次确认全部
python3 scripts/prism.py confirm --revoke canon # 撤销
```

**未确认时 `render` 与 `pack` 会拒绝继续（exit 5）**，
除非显式加 `--unattended`。

> 顺序上有个细节：稿子还没填完时，「先填稿」比「先确认」更根本，
> 所以就绪检查排在确认闸门之前。

---

## 0.8 平台适配：小云雀 / MiniMax Design

两个平台都有切割功能，本技能把它们用上：

| | 小云雀 | MiniMax Design |
|---|---|---|
| 切割 | **智能分镜 / 时间轴切割** | **AI 剪辑（自然语言）**：实测通过「加字幕」「加转场」「**裁掉最后 2 秒**」 |
| 首帧 | **首尾帧模式** | 尾帧作为首帧参考上传；或 3D 导演台先摆姿势 |
| 人物锁定 | 角色库 / 局部重改 | 资产中心（人物锚） |
| 协作 | 逐条提交 | Agent **先反问确认**再动手 |

**切割怎么用**：音乐由本技能切（14.5s，吸附小节线），画面由平台裁。
每条约 15.083 秒、音乐 14.226 秒，**多出的 0.58 秒**用作接缝重叠量
（在最快的那一下动作里切）。MiniMax Design 上一句话即可：
「把每条视频裁掉最后 0.6 秒」。

**别用平台的自动分镜**：有公开实测反馈说它容易切得过碎。
本技能已经把镜头数钉在每段 2–4 个、切点落在小节线上。

详细落地步骤、两个平台各自的坑、以及每条结论的来源与可信度，
见 **`references/platform-playbook.md`**。

```bash
python3 scripts/prism.py platform --platform xiaoyunque
python3 scripts/prism.py platform --platform minimax-design
```

---

## 1. 三条硬闸门（不通过就不许往下走）

### 闸门 1 · 时长（>3 分钟 = 失败）

必须**真的读取**音频时长，禁止根据文件名猜。

- `duration > 180s` → 输出「当前 Skill 默认支持不超过 3 分钟的歌曲。该歌曲长度为
  XX:XX。」并**停止正式 Prompt 编译**。**绝不自动截断用户的音乐。**
- `≤ 180s` → 继续，并**自动协助用户切分**音乐。

### 闸门 2 · 材料

必须：**一首歌 + 一张人物参考图**。缺任何一个都停下来要材料，不要硬产出一份
不能用的东西。歌词时间轴不是必需（缺了降级为 Music-Semantic Mode）。

### 闸门 3 · 人物 Canon

必须填满 `hair / eyes / face / costume / accessories / silhouette` 与
`stable_identifiers`。缺任何一项，渲染器**拒绝输出**——宁可不生成，也不生成会漂移的东西。

---

## 2. 一句话工作流

> 路径约定：下面的 `<本skill目录>` 是技能安装位置。如果它不可写（放在共享/只读位置），
> 用 `--project <可写目录>` 指定工作目录，其余命令不变；`--project` 放在子命令前后都一样。

```bash
cd <本skill目录>

# ① 第 0 步：材料闸门 + 时长闸门（先跑这个，别直接开工）
python3 scripts/prism.py gate --audio song.mp3 --image char.png

# ② 跑完全部确定性步骤（音乐实测 / 歌词 / Canon 骨架 / 三视图规格 /
#    14.5 秒切分 / 真的切音频 / 画风路线菜单 / 草稿导演稿）
python3 scripts/prism.py all --audio song.mp3 --image char.png

# ③ 只有这一步需要你：填导演稿
#    workspace/analysis/director_plan.json（人读版 director_worksheet.md）

# ③.5 让用户挑全片怎么结束
python3 scripts/prism.py endings
python3 scripts/prism.py endings --pick reach_and_crack

# ④ 让用户确认每一步（未确认时 render/pack 会拒绝）
python3 scripts/prism.py confirm --status
python3 scripts/prism.py confirm --step segments
python3 scripts/prism.py confirm --all      # 或逐个确认

# ⑤ 渲染 + 校验 + 打包
python3 scripts/prism.py render
python3 scripts/prism.py validate      # exit 0 才算过
python3 scripts/prism.py pack --platform xiaoyunque
```

**逐条生成时的循环**（每一条都要走）：

```bash
python3 scripts/prism.py render                     # 一次渲染全部提示词
# 在平台上生成 C1 → 取它的尾帧 → 挂到 C2 → 确认
python3 scripts/prism.py lastframe --video out/C1.mp4 --segment C1 \
    --describe "这一帧里看到了什么"
python3 scripts/prism.py confirm --step prompt-01
python3 scripts/prism.py confirm --step chain-01
# 再生成 C2 …… 顺序不能乱：尾帧是下一条的首帧
```

交付：`output/latest/minimax_h3_prompts.md`、`output/latest/交付包/`。

---

## 3. 逐步执行

### Step 1 · 材料与时长闸门

```bash
python3 scripts/prism.py gate --audio <歌> --image <人物图> [--lyrics <歌词>] --json
```

退出码：`0` 通过 / `3` 阻断（缺材料或超 3 分钟）。

### Step 2 · 音乐实测（不是装饰）

```bash
python3 scripts/prism.py analyze
```

产出 BPM、拍网格、onset、RMS 包络、音色亮度、段落、高潮、低谷、收束性格。

**这些数字必须真的影响**：动作幅度、剪辑速度、背景密度、抽帧程度、hold frame、
图形速度、色彩密度、转场、高潮、收束。

> ⚠️ **最容易忽略的一条**：**音量最大的一章，往往不是打点最猛的一章。**
> 实测某曲 CH3 的 RMS 最高、低频最厚、亮度最暗——它是**重量**，不是五彩爆炸；
> onset 峰值在 CH4，那才是碎裂/释放该放的地方。
> 别按「越来越响 → 越来越花」设计。

### Step 3 · 歌词

```bash
python3 scripts/prism.py lyrics
```

来源优先级（严格）：内嵌 → `.lrc` → `.srt` → `.vtt` → `.txt` → ASR。
**已经有可靠歌词就不要重复 ASR。**

> ⚠️ **ASR 只能当草稿。** 实测把「王子」转成过「滑走」。
> ASR 结果一律标 `[ASR uncertain]` 并要求人工核对。
> 提示词里**保留原歌词语言**；内部可以自己做中文语义解释。

确认无人声 → 切 **Music-Semantic Mode**：用节奏、音色、能量、和声情绪、结构变化
设计视觉，而不是放弃。

### Step 4 · 人物 Canon（唯一真相）

```bash
python3 scripts/prism.py canon
```

脚本给机械测量（尺寸／画幅／主导色／明暗与饱和基调）和一份**工作副本**。
然后**你必须用视觉能力真的去看那张工作副本**
（`workspace/character/canon_reference.*`），把 `character_canon.json` 填满。

- **Level A（绝对不可改变）**：脸、五官比例、眼型、眼睛颜色、发型、发色、刘海、
  年龄感、身体比例、核心服装结构、核心配饰。
- **Level B（高优先保留）**：小花、纽扣、绑带、袜子图案、鞋子细节、局部图案。
- **渲染字段**：`hair` / `eyes` / `face` / `costume` / `accessories` /
  `silhouette` / `stable_identifiers`。

> **STYLE CHANGES THE WORLD, NOT THE CHARACTER.**

### Step 5 · 三视图（把「只有一张图」变成「转面表」）

```bash
python3 scripts/prism.py threeview
```

一张正面图丢给视频模型，转个身脸就崩。三视图（**正面 / 四分之三 / 侧面 / 背面**
+ 头部特写 + 色标）把发型体积、侧面轮廓、背面服装结构钉死——这是人物一致性
最便宜的一道保险，并且它同时解决了「用户只有一张图」和「N 条各自独立生成」
之间的矛盾。

`output/latest/threeview.md` 里有可直接粘贴的中英双语提示词 + 负向词。
出图后放进 `input/character/threeview.png`，重跑 `canon`，它会自动认出来，
并在交付时作为 `<Picture 2>` 一起上传。

### Step 6 · 画风路线（**这一步必须让用户选**）

```bash
python3 scripts/prism.py all            # 菜单落在 output/latest/style_routes.md
python3 scripts/prism.py styles --pick <route-id>
```

**不要问用户「你想要什么风格」**——那样得到的通常是「日系」「赛博朋克」这类
泛化词。真正决定成片差别的是**融合语法**。所以给的是 4 条语法完整的路线：

| id | 路线 | 一句话 |
|----|------|--------|
| `print-decay` | 印刷衰减 | 人物是唯一清晰的印版，世界每段错版套印一次 |
| `paper-world` | 纸与剪 | 世界真的是纸片，深度靠图层不靠透视 |
| `ink-line` | 线即世界 | 画面由线构成、由线消失，轨迹可以被擦掉一半 |
| `gradient-dream` | 渐变幻景 | 世界在人物背后一整块一整块换色，人物一帧不变 |
| `folk-geometry` | 民俗几何 | 纹样当节拍器，每过一个重拍多生成一层 |
| `pop-superflat` | 平面波普 | 一切压成一个贴纸面，人物是面上唯一会动的东西 |

每条路线**自带 ≥3 种画风的递进**（用户要的「不同艺术风格环境」），
排序按**歌词意象命中数**——菜单本身就是「画风与歌词呼应」的第一层证明。

允许按段混搭：用户可以说「第 2 条的 C1+C3，第 4 条的 C2」。

> 风格词一律先查 `~/Desktop/art-aesthetic-vault`（147 个流派）。
> **禁止凭记忆编造流派术语。** 库不在时降级到内置媒介池，并在报告里写明。

### Step 7 · 分段（14.5 秒生成单元）

```bash
python3 scripts/prism.py segments
```

- `segment_count = ceil(duration / 14.5)`，最多 13 段。
- 切点**吸附到小节线**（容差 1.5 拍）；小节线够不着就退到拍线；再不行才用精确秒。
  **不迁就整数秒**——为凑整数把切点从重拍上挪开，正好毁掉节奏同步。
- 吸附**不许突破 H3 的 15 秒硬上限**。宁可回到拍线，也不生成一条模型收不下的 prompt。
- **音频真的被切出来**（`workspace/segments/C01.wav …`），与提示词用**同一份边界**。
  切点吸附到最近过零点避免爆音；**不默认加淡入淡出**——这些段要首尾相接拼回去。

> **14.5 秒是 GENERATION UNIT，不是 SEMANTIC UNIT。**
> 一句歌词从 13s 唱到 18s，则 Prompt 01 与 Prompt 02 都必须表达同一意象，
> **不能因为 14.5 秒到了就换场景。**

**H3 时长契约**（表里会逐段列出）：

| 音乐段长 | H3 `duration` | 实出帧数 | 实出时长 | 余量用途 |
|---|---|---|---|---|
| 14.5 s | **15** | 362 | 15.083 s | 0.58 s 藏接缝 |
| 12.14 s | 13 | 311 | 12.958 s | 0.82 s 藏接缝 |
| 1.5 s（末段） | 4 | 107 | 4.458 s | hold frame 补足 |

> `duration` 只接受 **4–15 的整数**，而帧网格是 17k+5——
> **请求 6s 实际只吐 5.875s**。所以换算规则不是「向上取整」，而是
> 「取**实出时长 ≥ 音乐长度**的最小整数」，否则用户会丢音乐。

### Step 8 · 你的创作（唯一的创作步骤）

填 `workspace/analysis/director_plan.json`。顺序不能颠倒：

```text
歌词 → 歌词真正的意义 → 视觉隐喻 → 人物动作 → 场景机制 → 画面元素 → 艺术媒介 → 镜头
```

错误顺序（禁止）：想一个很酷的风格 → 放一些好看的元素 → 最后强行解释歌词。

必须产出：

1. **`mv_concept`**：一句话核心概念。
   例：*一个人的身体始终不变，但所有定义她的外部世界不断改变。*
2. **`lyric_semantic_map`**：逐句理解（字面／情感／心理／主隐喻／次符号／实物／
   动作／空间隐喻／转化）。不必每格都填，但必须真的理解。
3. **`motif_dictionary` + 进化**：同一母题要演化——
   镜子 → 镜框 → 复制镜框 → 错版镜框 → 碎裂框架 → 空框。
   不要每 14.5 秒发明一个新宇宙。
4. **`visual_arc`**：整条视觉发展弧线，**必须由歌词推出**。
   禁止每首歌都「铅笔 → 拼贴 → 几何 → 白色」。
5. **`art_direction.why_this_medium`**：回答「这个媒介为什么属于这首歌」。
6. **每段的创意字段 + 镜头表**（见下一步）。

#### 三条属于本技能的硬要求

**① 歌词里的元素必须在画面背景里体现。**

`background_lyric_elements` 不是装饰词表，它是**可校验的**：
每个元素都必须能从这一段的歌词推出来（机器会做最长公共子串／整词匹配）。
推不出来 → 判定为随机装饰元素 → 校验失败。

这条把「歌词与画面融合」从形容词变成了断言。

**② 歌词与人物动作必须吻合。**

`lyric_action_binding` 逐句绑定：
「抓不住」→ 连续三次向前抓，每次都差一点；
「他们要我微笑」→ 每个重拍用手势形成固定「规定笑容」。
每条绑定都要挂上**第几拍**。

**③ 创作字段的语言 = 粘贴块的语言。**

`environment_system` / `overall_soundscape` / `content_prompt` / `action` /
`choreography` 会被**原样拼进正文**，所以英文路线（默认）下必须写英文；
只有逐字引用的**歌词**与**背景实物名**保留原语言（官方 O13）。
写中文句子进去，校验器会给 warning。

**④ 运镜先锋，但必须同时匹配人物、歌词、动作、节奏。**

- 只能用 **MiniMax H3 官方运镜词表**（20 个），写全「类型 + 幅度 + 速度」，
  写成自然英文动作。自造词（`graphic push-in` / `snap zoom` / `dolly` / `3D orbit`）
  会被校验拦下。
- **2D 限制感优先**：`Static Shot` + 强动作 优于复杂摄影机运动。
  **不要每个镜头都动。**
- 先锋性来自**画幅裁切、构图变化、二维空间关系、抽帧、图层、平面置换**，
  不是摄影机乱飞。空间深度靠：前景纸层 + 人物赛璐珞 + 背景插画 + 图形叠加 + 多层视差。

### Step 9 · 渲染与校验

```bash
python3 scripts/prism.py render     # 草稿会被拒绝（exit 2），不会瞎编
python3 scripts/prism.py validate   # exit 0 才算过
```

渲染器保证：
- 每条 prompt 结构固定、**自包含**（重新声明完整 Canon）+ **连续**（承接上一段）；
- 人物一致性措辞由渲染器保证存在，不由你的自由文本保证；
- `non_diegetic_music: N/A`（音轨是原曲 1:1 复用，不让模型编配乐）；
- 空段落、Markdown 加粗、超 7000 字符一律拦下。

### Step 10 · 交付

```text
output/latest/
├── minimax_h3_prompts.md   ← 主交付物（中文简报 + H3 原生粘贴块）
├── storyboard.md           ← 分镜总表（卡点/歌词/画风/动作/运镜 一表看清）
├── style_routes.md         ← 4 条画风路线（给用户挑的）
├── threeview.md            ← 三视图提示词
├── character_canon.md
├── music_analysis.md / lyrics_timeline.md / cut_sheet.md
├── validation.md           ← 校验报告
└── 交付包/                  ← 任何画布都能跑的上传包
    ├── 00-材料清单.txt
    ├── 01-上传顺序与操作单.md
    ├── 02-画布智能体指令.txt
    ├── segments/C01.wav …
    └── prompts/PROMPT-01.txt …
```

历史结果不覆盖：`all` 每次开始会把上一轮 `output/latest/` 归档到
`output/archive/YYYYMMDD_HHMMSS/`。

---

## 4. 硬规则（违反即失败）

### 人物
1. 每条 prompt 都**重新声明完整 Character Canon**（在全参考模式的
   `subject_definitions` / `retention_analysis` 里）。写 `same girl` 是错的。
2. 明确禁止：换脸 / 身份漂移 / 换发型 / 换发色 / 换服装 / 删配饰 / 年龄漂移 /
   身体比例改变 / 角色重设计 / 写实化重演 / 变成另一个角色。
3. 风格只能改世界，不能改人。人物可爱也照样用严肃的导演语言。

### 歌词
4. 谁在画面里由参考图决定，画什么由歌词决定，什么时候变由音乐决定。
5. 优先 Level 2（心理隐喻）与 Level 3（结构规则），少用 Level 1（字面插画）。
6. 间奏：继续上一句的后果 → 发展已有母题 → 为下一句埋伏笔 → 最后才抽象。
7. 全片换到别的歌也成立 → **FAILED**，重做。

### 画风与歌词的呼应
8. `background_lyric_elements` **必须能从本段歌词推出**，否则删掉。
9. 一条 MV 至少穿越 **3 种**不同画风（用户要的「不同艺术风格环境」）。
10. 风格词**先查库**，不许凭记忆编造流派术语。

### 2D
11. 明显 2D、limited animation、平面构图意识、动画限制感。
12. 不用 3D 运镜；不用 neon city / cyberpunk / 魔法蝴蝶 / 银河 / 粒子漩涡 /
    大逆光 / 随机漂浮物（除非歌词明确需要）。
13. 深度靠图层，不靠透视。

### 舞蹈
14. 人物**始终在跳舞**，不拍剧情短片。
15. 动作与这句歌词有关，重拍在音乐上，相邻段动作连续。
16. 优先安全语汇，慎用 360 旋转 / 后空翻 / 地躺 / 极端透视。

### 尾帧与平台
17. 第 2 条起必须接上一段的尾帧；**画风转换放在段内**，不换姿势。
18. 取不到尾帧就明确报错并让用户去平台导出，**绝不拿首帧冒充尾帧**。
19. 提示词里**绝不**出现生成音乐/配乐的要求（用户已上传原曲）。
20. 用户没确认的步骤，`render` / `pack` 拒绝继续。

### 流程
21. 音超过 3 分钟：阻断并说明，**不自动截断**。
22. 缺工具就降级并写清楚影响（`references/fallback-ladder.md`），不静默编造。
23. 交付前必须 `validate` 通过。**未通过不许说 DONE。**

---

## 5. Definition of Done

```text
[ ] 音乐已读取（真实探测，非文件名猜测）
[ ] 时长 ≤ 180s（>180s 已阻断并说明，未截断用户音乐）
[ ] 歌词已识别（或明确标记 needs_manual_lyrics / instrumental）
[ ] Character Canon 已建立并填满渲染字段
[ ] 三视图已产出并作为 <Picture 2> 引用
[ ] 用户已在 4 条画风路线里选定一条
[ ] 歌词语义已分析（lyric_semantic_map）
[ ] 完整视觉 Arc 已建立（由歌词推出）
[ ] 段数 = ceil(duration / 14.5) 且 ≤ 13
[ ] 每段切点已吸附到小节线/拍线（或明确说明为何未吸附）
[ ] 每段的 background_lyric_elements 都能从该段歌词推出
[ ] 人物舞蹈连续（continuity_from_previous / hook_to_next 都有内容）
[ ] 运镜全部是官方词表，且写全「类型 + 幅度 + 速度」
[ ] 整条 MV 穿越 ≥3 种画风
[ ] 每段 H3 prompt 结构完整、≤7000 字符、零 Markdown
[ ] 音频段已真的切出来（或已产出切分清单并说明原因）
[ ] 用户已从 endings 菜单里选定收尾效果，且末段提示词带上了它
[ ] 每一条都用固定六段结构（人物与参考保持一致性 / 风格提示词 / 内容提示词 /
      integrated_multimodal_description / overall_soundscape / non_diegetic_music）
[ ] 提示词里**没有**任何生成音乐/配乐的要求，non_diegetic_music: N/A
[ ] 第 2 条起都取了上一段的尾帧、写在【内容提示词】的「延续上一帧」里、并作为首帧上传
[ ] 每一个步骤都已由用户确认（confirmations.json 无 pending）
[ ] python3 scripts/prism.py validate 退出码 0
```

---

## 6. 参考文件

| 文件 | 内容 |
|------|------|
| `references/director-doctrine.md` | 身份、核心公式、歌词三级可视化、母题进化、环境即剧作、导演自检 |
| `references/style-atlas.md` | 六条画风融合路线、怎么查 art-aesthetic-vault、冲突消解怎么读 |
| `references/h3-format.md` | 五种 H3 路线的选法与原生格式（**依据官方 ref-en.txt / base-en.txt**） |
| `references/h3-rules.md` | 官方规则 + 踩出来的规则，每条配一条可执行校验 |
| `references/music-analysis.md` | 双路线 BPM、六个数字各自决定什么、章节判定 |
| `references/dance-vocabulary.md` | 安全舞蹈语汇、歌词驱动编舞、舞蹈连续性 |
| `references/art-medium-map.md` | 语义 → 媒介映射（风格库不可用时的降级） |
| `references/threeview.md` | 三视图规范：为什么必须做、怎么用、检查单 |
| `references/quality-gates.md` | 四组闸门、导演稿 Schema、渲染器硬闸门 |
| `references/platform-playbook.md` | **小云雀 / MiniMax Design 落地手册**：切割、首尾帧、逐步骤确认、各自的坑、来源与可信度 |
| `references/fallback-ladder.md` | 降级阶梯与失败信息模板 |
| `references/github-sources.md` | 需要从 GitHub 补的东西在哪、怎么用 |
| `references/official/` | 官方 `base-en.txt` / `ref-en.txt` 原文（格式冲突时**以它为准**） |
| `references/camera-library.json` | 运镜库 + 各画风的运镜偏好/禁忌 |
| `references/motion-library.json` | 动作库（按曲风分类）+ 画风兼容性 |
| `references/style-map.json` | 歌词意象 → 流派 slug 索引 |

## 7. 全部命令

| 命令 | 用途 |
|------|------|
| `prism.py doctor` | 环境体检（工具 / 模块 / 风格库 / 配置完整性） |
| `prism.py gate` | 材料闸门 + 时长闸门 |
| `prism.py analyze` | 音乐实测 |
| `prism.py lyrics` | 歌词时间轴 |
| `prism.py canon` | 人物 Canon 骨架 + 工作副本 + 三视图规格 |
| `prism.py threeview` | 三视图规格与中英提示词 |
| `prism.py styles [--pick]` | 画风融合路线菜单 / 应用选定路线 |
| `prism.py segments` | 14.5 秒切分 + 真的切音频 + 草稿导演稿 |
| `prism.py render` | 渲染 H3 原生提示词（草稿会被拒绝） |
| `prism.py validate` | 交付校验 |
| `prism.py pack` | 打上传交付包 |
| `prism.py lastframe` | **取视频尾帧**（下一段的首帧）｜ `--scan` 扫整个目录 |
| `prism.py chain` | 构建/查看尾帧续接链 |
| `prism.py endings` | **收尾效果菜单**（八种，不一定要站定）｜ `--pick <id>` |
| `prism.py confirm` | **逐步骤确认台账**（`--step` / `--all` / `--status` / `--revoke`） |
| `prism.py platform` | 平台适配信息（切割功能 / 首尾帧 / 各自的坑） |
| `prism.py all` | 跑完所有确定性步骤 |

测试：`python3 -m unittest discover -s tests -t tests -v`（62 项，**零第三方依赖**）。
