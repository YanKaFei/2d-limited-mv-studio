# MiniMax H3 提示词格式

> 一手来源：`references/official/h3-base-en.txt`（T2VA/I2VA/FL2VA/L2VA）与
> `references/official/h3-ref-en.txt`（全参考 Ref2VA）。
> 本文件是提炼；**冲突时以 official/ 里的原文为准**。
> 官方仓库：<https://github.com/MiniMax-AI/MiniMax-H3>

---

## 一、先选路线，再写提示词（这一步最容易错）

| 你的素材 | 路线 | 主字段 | 必需段落 |
|---|---|---|---|
| 什么都没有，纯文字 | **T2VA** | `integrated_multimodal_description` | 三个核心段 |
| 一张图当**第一帧** | **I2VA** | `integrated_multimodal_description` | 三核心段 ＋ 第一行对齐指令 |
| 一图首帧 + 一图尾帧 | **FL2VA** | 同上 | 三核心段 ＋ 首尾对齐指令 |
| 一图当**尾帧** | **L2VA** | 同上 | 三核心段 ＋ 尾帧对齐指令 |
| 一张图**只用来定义角色／场景／服装／风格** | **Ref2VA** | **`detailed_description`** | **六段** |

**MV 的正确选择**：

- **默认 → Ref2VA**。人物图 + 三视图都只用来定义角色，原曲 1:1 复用。
- 用户想让片子**从他那张图的第一帧开始** → I2VA。
- 别用 T2VA 做人物 MV：没有参考图就没有人物一致性（官方失败模式 ⑤）。

> ⚠️ **选错路线是最贵的错误。** 图片只定义角色时按 I2VA 处理，
> 模型会试图把那张图当**第一帧**对齐。

---

## 二、Ref2VA：六段（顺序固定）

```
subject_definitions:
<Subject 1> is …

summary:
[reference generation + audio reuse] …

retention_analysis:
<Subject 1> (appears in [Shot 1], …): fully_preserved - …
<Audio 1>: fully_copy - …

detailed_description:
<style in 1–2 English sentences>
[Shot 1] …
[Shot 2] At 00:03.500, the shot cuts to …

overall_soundscape:
…

non_diegetic_music: N/A
```

### 参考标签的四种

| 标签 | 含义 |
|---|---|
| `<Subject N>` | 从素材里抽象出的、可在目标视频中复用或修改的**可见内容** |
| `<Picture N>` | 当作**具体帧**或分镜锚点的参考图 |
| `<Video N>` | 提供剪辑源／续接起点／整片时间结构 |
| `<Audio N>` | 被复制或参考的音频 |

> **关键规则（O14）**：**如果一张图只用来定义角色、场景、服装或风格，
> 不要建独立的 `<Picture N>` 条目**，而要把它引在对应的 `<Subject N>` 定义里：
>
> ```
> <Subject 1> is the character in <Picture 1> (character reference) and
> <Picture 2> (character turnaround reference), with …
> ```

这就是本技能**人物 Canon 的正确落点**：写在 `<Subject 1>` 里，而不是正文里。
正文复述外观会和参考图打架（漂移的常见根因）。

### `summary` 的任务类型前缀

| 类型 | 什么时候用 |
|---|---|
| `keyframe completion` | 图片当作首帧／关键帧／尾帧 |
| `reference generation` | 图片/视频/音频提供**生成指导**（人物、场景、风格、动作…），不作为具体帧 |
| `video editing` | 直接修改已有源视频 |
| `video continuation` | 从已有视频续接 |
| `audio reuse` | 同一段音频被完整或部分复用 |
| `audio reference` | 不复制信号，只参考风格／音色／节奏 |

多个关系用 ` + ` 连接。**MV 的标准写法**：

```
[reference generation + audio reuse]
```

（人物图提供人物 → reference generation；原曲 1:1 当音轨 → audio reuse。）

### `retention_analysis` 的关系标记（固定英文值）

**可见内容**：`fully_preserved` / `partially_preserved` / `attribute_transfer` / `weak_reference`
**音频**：`fully_copy` / `partially_copy` / `reference` / `weak_reference`

```
<Subject 1> (appears in [Shot 1], [Shot 2]): fully_preserved - her face, feature
proportions, hairstyle, hair colour, costume structure and signature accessories are
identical in every shot. What changes by design is the drawing medium, line quality,
palette and background system.
<Audio 1>: fully_copy - <Audio 1> is reused 1:1 as the target video's complete final
audio track.
```

> **不要把「新加的背景、动作、剧情」当作参考保真度的损失。**
> 那是本来就该变的——要写清楚**什么按设计改变、什么不变**。

---

## 三、T2VA / I2VA：三核心段

```
<I2VA 才有：第一行对齐指令，后面空一行>

integrated_multimodal_description: [Shot 1] …

overall_soundscape: …

non_diegetic_music: …
```

**I2VA 的第一行必须逐字是**：

```
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.
```

---

## 四、正文写法（五种路线共用）

| 规则 | 说明 |
|---|---|
| `[Shot 1]` **不带时间戳** | 从第二个镜头起才写时间 |
| 后续镜头 | `[Shot N] At MM:SS.mmm, the shot cuts to …`，时间**严格递增**且在时长内 |
| 剪辑动词 | `the camera cuts to` / `the shot cuts to` / `the shot transitions to` / `the shot changes to` / `the shot switches to`。明确要求才用 cross-dissolve / fade / wipe |
| 切镜要报新信息 | 一个切必须带来主体、空间、状态、视角或时间上的**新信息**。只是改变景别或轻微角度 → 用运镜，不要切 |
| 正文语言 | **英文**。台词、歌词、画面文字保留原文 |
| 时长 | **4–15 秒，整数**（API 的 `duration`） |
| 提示词上限 | 7,000 字符 |

运镜的官方词表与「类型 + 幅度 + 速度」写法见 `h3-rules.md` 第三节。

---

## 五、三个声音／文本段

| 段 | 要求 |
|---|---|
| `overall_soundscape` | **1–4 句英文**。环境音 + 物理动作音 + 非语言人声。**不要重复**已在正文里的台词／歌声／有源音乐 |
| `non_diegetic_music` | **1–3 句英文**，只写乐器、速度、节奏、力度变化，**不写抽象情绪词**。无配乐时写 `N/A` |
| 画面文字 | 必须**逐字引用**并加英文双引号，不翻译 |

> **MV 里的 `non_diegetic_music` 写 `N/A`**：成片配的是已录好的原曲，
> 不要让模型自己编配乐。而且**绝不能一处要音乐一处禁音乐**——
> 这是官方列出的失败模式 ③。
>
> 本技能的做法：`non_diegetic_music: N/A`（干净的官方写法），
> 「不要生成音乐」这句话放在 `retention_analysis` 的 `<Audio 1>: fully_copy` 一行里
> ——那才是官方给音频关系准备的位置，两边不打架。

### 说话人与歌词

发声主体用稳定 ID `(S1)` `(S2)`；台词／歌词写成 `<d>[语言] 原文</d>`，
**逐字保留原文与标点**。说话人的识别信息写在 `<d>` **外面**。

> **MV 用原曲时通常不需要 `(S1)`**——歌声不由模型生成。
> 本技能默认不写 `<d>`：歌词以**平面字体**的形式印在背景平面上（见下）。

---

## 六、歌词怎么进画面（本技能的特色写法）

用户的硬要求是「歌词里的元素要在画面背景里体现」。落成两句：

1. **实物进背景**（主要手段）：
   `Behind her the flat printed background is built out of the lyric's own objects: 水面, 影子, 波纹.`
2. **歌词原文作为平面字体**（先锋 2D 的合法手法，可 `--no-lyric-text` 关闭）：
   `The lyric line "我把影子留在水面" is printed on the background plane as hard-edged flat typography.`

两者都在正文里，**镜头看得见**（符合 O8），且画面文字逐字引用（符合 O9）。

---

## 七、语言规则（最容易踩混的一条）

| 内容 | 语言 |
|---|---|
| 正文（`detailed_description` / `integrated_multimodal_description`） | **英文**（官方 O13） |
| 六段／三段的**字段名** | 永远是英文（它们是格式键，不是内容） |
| 台词、歌词、画面可见文字 | **保留原文**，逐字不改 |
| 背景实物名（`background_lyric_elements`） | **保留原文**（它们是歌词里的东西） |
| **创作字段**：`environment_system` / `overall_soundscape` / `content_prompt` / `action` / `choreography` | **必须用目标语言写** |

> ⚠️ 最后一行是最容易漏的：这些字段会被**原样拼进英文正文**。
> 用中文写它们，英文正文里就会夹整句中文——校验器会给 warning。

切到中文平台路线时，用 `--lang zh` 出整段中文自然语言。
**两种不能混着粘**：H3 前面有 Context-IR 做理解与改写，混用会打架。
