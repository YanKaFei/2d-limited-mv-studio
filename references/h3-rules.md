# MiniMax H3 规则库

> 分两类：**官方的**（不能违背）和**我们踩出来的**（付过代价）。
> 每条尽量配一条**可执行校验**——写在 `scripts/lib/gates.py` 里，违反就红。
> 权威原文在 `references/official/`，冲突时**以官方为准**。

---

## 一、官方的（不能违背）

| # | 规则 | 来源 |
|---|---|---|
| O1 | 单条 **4–15 秒**；API 的 `duration` **只接受整数** | [官方 API 文档](https://platform.minimax.io/docs/guides/video-generation) |
| O2 | 提示词上限 **7,000 字符** | 官方 |
| O3 | 结构 = **参考素材说明 + 核心 + 逐段描述**，不能糊成一段 | 官方 |
| O4 | 每个上传文件必须**声明职责**（角色参考／场景参考／关键帧／风格参考／音频复用…） | 官方 |
| O5 | 引用语法是 `<Subject N>` / `<Picture N>` / `<Video N>` / `<Audio N>` | 官方 |
| O6 | 结尾两个字段：`overall_soundscape:` 与 `non_diegetic_music:` | 官方 |
| O7 | 要杀配乐就写 **`non_diegetic_music: N/A`** | 官方 |
| O8 | **写镜头看得见的，不写隐喻** | 官方 |
| O9 | 画面里要出现文字，必须**逐字引用**（英文双引号，不翻译） | 官方 |
| O10 | 运镜写**具体词**，不写「环绕一下」 | 官方 |
| O11 | **切镜头时要报出新景别 + 主体名**——跨切保脸一致的手段 | 官方 |
| O12 | `[Shot 1]` **不带时间戳**；后续镜头 `[Shot N] At MM:SS.mmm, ...`，时间严格递增 | 官方 |
| O13 | 正文语言 **英文**；台词／歌词／画面文字保留原文 | 官方 |
| O14 | **图只用来定义角色时，不要单开 `<Picture N>` 条目**，引在 `<Subject N>` 定义里 | 官方 `ref-en.txt` |
| O15 | Ref2VA 支持 **音频 ≤3 段**，且**音频必须与图像或视频输入一起** | 官方 README |
| O16 | `retention_analysis` 的关系标记是**固定英文值**：可见内容用 `fully_preserved` / `partially_preserved` / `attribute_transfer` / `weak_reference`；音频用 `fully_copy` / `partially_copy` / `reference` / `weak_reference` | 官方 `ref-en.txt` |
| O17 | `summary` 必须以方括号任务类型前缀开头，如 `[reference generation + audio reuse]` | 官方 `ref-en.txt` |

**官方列出的六个失败模式**：① 一整段不分块 ② 传了文件没写用途 ③ 一边要配乐一边禁配乐
④ 想要长镜却写了分镜结构 ⑤ 想要脸一致却没传参考图 ⑥ 提示词太短又没参考文件。

---

## 二、踩出来的（每条对应一次真实失败）

| # | 规则 | 怎么踩到的 |
|---|---|---|
| F1 | **代码块内不许出现「音乐」「配乐」当**要求**——剪辑对齐一律用 BPM 说 | 校验器抓到：「切点踩在**音乐**重拍上」与 `non_diegetic_music: N/A` 同时出现，正撞官方失败模式③。改成「118 BPM 的重拍」 |
| F2 | **每条 prompt 的时间轴从 0 开始** | 原来写绝对时间码（第二条 14.48–28.71s）。H3 看不到上一条，绝对时间对它毫无意义 |
| F3 | **切点落在小节线上**，不迁就整数秒 | 15.00s 不在小节线上。为凑整数秒把切点挪开 = 毁掉节奏同步 |
| F4 | 运镜必须写**官方词**，不能只写中文描述 | 校验器抓到：`螺旋` 在提示词里出现 0 次——只写了「一边环绕一边推近」。改成用 `Arc Shot` 与 `Push In` 的官方说法 |
| F5 | 每个镜头**显式声明接法**（切 / 不切） | 让「连贯」可校验，而不是靠人记 |
| F6 | **缝藏在最快运动里** | 转身中途、跳跃最高点、满屏花纹——运动模糊和遮挡替你藏住不连续 |
| F7 | 复合运镜要写明两个词**同时进行** | 螺旋 = Arc + Push In；摇臂揭示 = Pedestal + Pull Out |
| F8 | **正文里不复述人物外观**，只引用 `<Subject 1>` | 文字与参考图冲突会让模型漂移。Canon 写在 `subject_definitions` / `retention_analysis` |
| F9 | 跨画风混搭时**只在段内合并负向词**，不跨段合并 | 不同画风的负向词互相打架（欧普禁具象主体 vs 我们要放人） |
| F10 | 语义冲突要人判断，`artvault compose` 只能抓词串包含 | `op-art` 的「representational subject」是语义冲突，compose 抓不到 |
| F11 | 单条**镜头数 ≤6**；超过 5 镜建议显式声明「快速蒙太奇」 | 12.8s 里 6 镜（歌词本身就是 6 个短句）是上限 |
| F12 | 短段落（<2.5s）**不要交给视频模型** | 直接出静帧在剪辑里做更快也更稳 |
| F13 | **帧网格 17k+5 会让请求比实出长** | 请求 6s 只吐 5.875s，请求 13s 只吐 12.958s。换算必须取「实出 ≥ 音乐」的最小整数，否则丢音乐 |
| F14 | **每段都填同一个 duration**，别让模型猜 | 14.5s 的音乐一律填 15，余量用来藏缝 |

---

## 三、运镜词表（官方，只有这些）

| 维度 | 可用表达 |
|---|---|
| 运动类型 | `Zoom In / Zoom Out`（变焦，机身不动）· `Push In / Pull Out`（机位前后）· `Pan Left / Pan Right`（机位不动，镜头水平转）· `Truck Left / Truck Right`（机位水平平移）· `Tilt Up / Tilt Down`（镜头垂直转）· `Pedestal Up / Pedestal Down`（整个机位升降）· `Arc Shot`（绕主体弧线）· `Tracking Shot`（跟拍）· `Static Shot` · `Shake Slightly / Shake Strongly` · `POV` · `Roll Clockwise / Roll Counterclockwise` |
| 幅度 | `with small amplitude` / `with large amplitude` |
| 速度 | `at slow speed` / `at fast speed` |

**写成自然英文动作，不要堆标签在句尾**：

```
✅ The camera pushes in with small amplitude at slow speed toward the folded letter in her hands.
✅ The camera pans right with large amplitude at fast speed, revealing the open doorway.
✅ The camera holds a static shot as the runner exits the frame.
❌ 镜头做一次 graphic push-in
❌ 镜头 snap zoom（幅度大速度快）
```

**复合运镜**要两个官方词并列 + 「同时进行」：

| 复合 | = | 用途 |
|---|---|---|
| 螺旋 | `Arc Shot` + `Push In` | 吞噬感、高潮 |
| 摇臂揭示 | `Pedestal Up` + `Pull Out` | 收尾，先看见人再看见世界 |
| 环绕上升 | `Arc Shot` + `Pedestal Up` | 变身、亮相 |

---

## 四、时长与帧数对照（官方实测端点）

```
帧数 = 17k + 5，  k = round(duration × 24 / 17)，  24 fps
```

| duration | 帧数 | 实出时长 |
|---|---|---|
| 4 | 107 | 4.458 s |
| 5 | 124 | 5.167 s |
| 6 | 141 | 5.875 s |
| 7 | 175 | 7.292 s |
| 10 | 243 | 10.125 s |
| 13 | 311 | 12.958 s |
| 14 | 345 | 14.375 s |
| 15 | **362** | **15.083 s** |

> ⚠️ 这是从官方实测端点（4→107、15→362）反推的模型，不是官方承诺的公式。
> 用前用一次真机核对。**但「实出可能短于请求」这件事本身就是必须防的**，
> 所以换算一律取「实出 ≥ 音乐长度」的最小整数。

---

## 五、校验清单（`scripts/lib/gates.py` 实现）

**A 时间**
- [ ] 段数 = ceil(duration / 14.5) 且 ≤13
- [ ] 每段 ≤15s、时间连续无缝、不重不漏
- [ ] 每段有 shots

**B 人物**
- [ ] Canon 六个渲染字段齐全
- [ ] `stable_identifiers` 非空
- [ ] 粘贴区有 `character reference` / `fully_preserved` / `the only character`
- [ ] 粘贴区**零**人物漂移词

**C 歌词**
- [ ] 每段 `background_lyric_elements` 非空
- [ ] 每个元素都能从该段歌词推出（最长公共子串／整词匹配）
- [ ] `continuity_from_previous` / `hook_to_next` 都有内容
- [ ] 穿越 ≥3 种画风；不是所有段同一画风

**D 格式**
- [ ] 运镜全在官方 20 词表内；幅度/速度写法合法
- [ ] `style_prompt` 含 2D / limited animation / hand-drawn / flat composition
- [ ] 无被禁通用元素（neon city / cyberpunk / galaxy / 3D orbit …）
- [ ] 粘贴区零 Markdown、每条 ≤7000 字符
- [ ] `non_diegetic_music: N/A` 恰好每条一次
- [ ] 有 `<Audio N>: fully_copy`
