<div align="center">

# 2d-limited-mv-studio

**二次元 MV 工坊 · 2D 运镜限制 · One image, one song, many worlds.**

*The limitation is the style.*
*限制就是风格。*

*The world mutates. The character does not.*
*世界不断变异，角色始终稳定。*

[![Built with DeepSeek Harness](https://img.shields.io/badge/built%20with-DeepSeek%20Harness-4B4BFF)](#built-with-deepseek-harness)
[![DSH Skill](https://img.shields.io/badge/DSH-agent%20skill-111111)](#install)
[![Target](https://img.shields.io/badge/target-MiniMax%20H3-FF4E8A)](#platforms)
[![Best on](https://img.shields.io/badge/best%20on-小云雀%20%C2%B7%20MiniMax%20Design-3DD6D0)](#platforms)
[![Tests](https://img.shields.io/badge/tests-119%20passing-2E7D32)](#tests)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-8A9BA8)](#requirements)
[![Camera](https://img.shields.io/badge/camera-2D%20limited%20%C2%B7%20no%203D-6B4FBB)](#the-camera-never-leaves-the-paper)

[English](#english) · [中文](#中文) · [Quick start](#quick-start) · [Platforms](#platforms) · [Endings](#the-last-gesture)

</div>

---

> A music video is not a sequence of pretty frames.
> It is a single body that refuses to stop dancing while the world around it is repeatedly
> redrawn — printed, torn, engraved, dissolved, re-registered — and it is still unmistakably
> the same person at the last frame.
>
> 一条 MV 不是一串好看的画面。它是一具**拒绝停下来的身体**：周围的世界被反复重画——
> 印刷、撕开、刻蚀、溶解、错版——而到最后一帧，她仍然明确地是同一个人。

**One-click anime character music videos.** Give it a character image and a song; it hands back a
complete, machine-checked prompt package for **MiniMax H3** — the music cut at **14.5 s**, a cast of
art movements your character dances through, lyric objects written into the background, camera
language restricted to H3's official vocabulary, and every segment chained to the previous one by
its **actual last frame**.

**一键生成二次元人物 MV 音乐动画。** 给它一张人物图和一首歌，它交回一整套经过机器校验的
**MiniMax H3** 提示词包：音乐按 **14.5 秒**切分，人物穿越多种艺术流派，歌词里的实物落进背景，
运镜只用 H3 官方词表，并且每一段都用上一段的**真实尾帧**续接。

---

## English

### Why 14.5 seconds

H3's `duration` parameter accepts **integers only**, between 4 and 15 seconds — and its frame grid
(`17k+5`) means a request for 15 s actually delivers **362 frames ≈ 15.083 s**.

So the two numbers are deliberately kept apart:

| | value | why |
|---|---|---|
| music cut | **14.5 s**, snapped to the nearest bar line | musical, and the user's unit |
| H3 `request` | **15** | the smallest legal integer whose *delivered* length still covers the music |
| delivered | **15.083 s** | verified against a real H3 output |
| usable | 14.5 s | the remaining **0.58 s is seam overlap** — hide the join inside the fastest motion |

Naive rounding-up silently *truncates the music* (a 6 s request only delivers 5.875 s).
`2d-limited-mv-studio` picks the smallest integer whose delivered length still covers the audio.

### The six-section prompt

Every prompt uses one fixed shape, in this order:

```text
人物与参考保持一致性：   reference roles + full character canon + drift prohibitions
风格提示词：           2D · limited animation · hand-drawn · flat composition + this segment's movement
内容提示词：           the continuity clause, then shot by shot
integrated_multimodal_description:  how reference, lyrics, music, dance and edit co-operate
overall_soundscape:    ambience and the physical sounds of the body
non_diegetic_music: N/A
```

`N/A` is not an omission. **You already uploaded the song.** Nothing here asks a model to compose
music — which also avoids the official failure mode of asking for music and forbidding it in the
same prompt.

### The camera never leaves the paper

This is not a live-action camera that happens to be pointed at a drawing. **It is a camera
standing over a stack of paper**, and that is the whole point.

What the camera may do is bounded on purpose:

- **No 3D camera.** No orbit through space, no drone rise, no fly-through, no perspective travel.
  Depth comes from **layers** — foreground paper, the character cel, background illustration,
  graphic overlay — never from a moving viewpoint.
- **Motion is authored in 2D.** A rostrum move slides flat across the artwork with **zero
  perspective change**. A cel slide keeps the background dead still while the character moves.
  A multiplane parallax separates layers by speed — the only honest "depth of field" 2D has.
- **Limited animation is the texture.** Held frames, animation on twos, stepped motion,
  pose-to-pose, smear drawings. Smoothness is not the goal; a drawing that *behaves like a
  drawing* is.
- **Misregistration is a language, not an error.** Colour layers sliding apart by a few pixels
  is how this skill says *an identity has come loose*.

The motion vocabulary is capped at H3's **20 official terms** for exactly this reason — a bigger
vocabulary would tempt the camera off the paper. What gets enriched instead is everything the
camera *is looking at*: angle, composition, focus, and what the shot is for.

> **The test we hold ourselves to:** if you removed every 3D camera move, would the film still
> hold up? If not, it was never a 2D film.

### The camera never leaves the paper — 运镜限制感

这不是一台「碰巧对着画的实拍摄影机」，而是**一台架在纸堆上的摄影机**——这才是重点。

摄影机被允许做什么，是被**刻意限死**的：

- **不做 3D 运镜。** 不绕空间、不无人机上升、不飞越、不穿越透视。
  深度只来自**图层**：前景纸 + 人物赛璐珞 + 背景插画 + 图形叠加，绝不来自移动的视点。
- **运动在 2D 里被写出来。** 摄影台推移是画面**平移、透视完全不变**；
  赛璐璐滑动是背景纹丝不动、只有人在动；多层视差靠图层速度差——
  这是 2D 唯一诚实的那种「景深」。
- **limited animation 是质感本身。** 定格、on twos、stepped motion、pose-to-pose、
  smear drawing。**不追求丝滑**——追求的是「一张画在该有的样子里动」。
- **错版是语言，不是事故。** 色层错开几个像素，是本技能说「身份松动了」的方式。

运动词被压在 H3 官方那 **20 个**里，正是这个原因——词表一大，摄影机就想离开纸面。
于是我们丰富的是摄影机**在看什么**：角度、构图、焦、以及这一下要揭示什么。

> **我们拿来衡量自己的那条标准**：如果把所有 3D 运镜全拿掉，这条片子还立得住吗？
> 立不住，那它本来就不是一条 2D 片。

### Camera: six layers, one vocabulary

H3 recognises exactly **20 camera-motion words** — and nothing else. So "richer camera work"
cannot come from inventing terms; `crane shot` and `whip pan` simply are not read. The enrichment
comes from **layering** instead:

```
shot size → angle → composition → focus → official motion word → subject–camera relation → what it reveals
```

| Layer | Count | Examples |
|---|---|---|
| Shot size | 10 | extreme wide → extreme close-up |
| **Angle** | **12** | low / high / dutch / overhead / worm's-eye / over-the-shoulder / POV / **flat frontal (2D-native)** |
| Composition | 12 | rule of thirds, symmetry, negative space, frame-within-frame, poster layout |
| Focus | 4 | deep, shallow, soft, **rack** |
| **2D-native moves** | **10** | rostrum camera, multiplane parallax, cel slide, **registration shift**, paper wipe, iris, hard-crop reframe, split screen, exposure flash, held-frame drift |
| Relation | 7 | follows / leads / matches pace / observes / reveals / opposes / circles |

**The missing layer was never motion — it was *angle*.** A library of nothing but pans and
push-ins is why the camera felt thin.

Three rules, all machine-checked:

1. **A locked shot gets an explicit lock line.** Models drift, especially on wide shots. Every
   `Static Shot` gets *"The camera is entirely motionless for the duration of the scene, with
   movement only occurring from the subject."*
2. **Every moving shot must name its relation to the subject.** Without it the two motions run on
   separate clocks — visible as jitter and a character who appears to glide.
3. **Rich camera work is not a camera showreel.** At most **half** the shots in a segment may move;
   the rest are locked, with the energy supplied by **2D-native moves** — a locked camera over a
   living drawing.

Live-action terms are for *thinking*; everything emitted is mapped back to the official 20
(`crane_up → Pedestal Up`, `whip_pan → Pan Right + large + fast`). A test enforces that every
mapping target is a real official term — the skill will not teach you to write words the model
ignores. Sources and the full tables: `references/camera-vocabulary.md`.

### 运镜：六层，而不是一层（角度丰富，平面不变）

H3 只认官方那 **20 个运动词**。所以「丰富运镜」不能靠编新词——`crane shot`、`whip pan`
模型根本不读。丰富化只能靠**分层**：

```
景别 → 角度 → 构图 → 焦 → 官方运动词 → 相机与主体的关系 → 这一下要揭示什么
```

**原来缺的从来不是运动词，是角度层。** 一个只有平移推拉的库，镜头当然是薄的。

三条硬规矩，全部机器校验：**固定镜头必须再用自然语言加一次锁**（模型在远景上会自己飘）；
**运动镜头必须写清与主体的关系**（不写就抖动、人物像在飘）；
**运镜丰富 ≠ 运镜展览**（每段运动镜头 ≤ 一半，其余靠 2D 专属招提供动感——机位锁死、画面在动）。

实拍术语只用于**思考**，输出前一律映射回官方词；测试强制每个映射目标都是真官方词。
词表与来源见 `references/camera-vocabulary.md`。

### The last gesture

A standing pose is the laziest way to end a film. The last gesture is what the audience keeps.
`2d-limited-mv-studio` offers **eight directable endings**, ranked against the music's own ending character:

| id | Ending | What happens |
|---|---|---|
| `jump_freeze` | **Jump & Freeze** 跃起定格 | full jump, freeze at the apex, background pulled away to a single offset contour |
| `reach_and_crack` | **Reach & Crack** 伸手裂屏 | she pushes a fingertip into the lens; the whole image cracks like glass, white showing through |
| `swipe_to_black` | **Swipe to Black** 手一滑黑屏卡点 | arm sweeps the lens, screen cuts to black exactly on the downbeat, one afterimage lingers |
| `frame_drop_vanish` | **Frame-Drop Vanish** 逐帧抽掉 | arms go, then torso, motion continues, until only a contour line is left |
| `misregistration_exit` | **Misregistration Exit** 印版退位 | de-prints in layers: colour → line → nothing but registration marks |
| `spin_to_line` | **Spin to a Line** 旋转成线 | mid-spin the body collapses into one vertical line, then is erased upward |
| `paper_tear_exit` | **Paper Tear Exit** 纸撕离场 | the frame tears down the middle; she dances out through the rip |
| `look_back_fade` | **Look Back, Fade** 回望褪色 | the only full stop in the film — she looks back, the frame fades to an old photograph |

Every ending preserves identity. **What disappears is the drawing, never the person.**

### Last-frame chaining

```
C1 ──its last frame──▶ C2 ──its last frame──▶ C3 ──▶ C4
```

The previous segment's **final frame** becomes the next segment's **first frame**.
This is the only continuity evidence a model cannot argue with: it is looking at the same image.

Two hard constraints follow, and one of them is a genuine design tension worth naming:

1. **The style change happens *inside* the segment.** A chained first frame drags the previous
   segment's art style in with it. Rather than choosing between "connected" and "a new style every
   segment", `2d-limited-mv-studio` does both: `0–1.5 s` holds the previous drawing style and pose, then the
   world transitions *within the shot*. The transition becomes an event instead of a cut.
2. **Do not change the pose while chaining.** A third-party field report (unverified — see
   `references/platform-playbook.md`) puts limb tearing at vertical displacement above **12 % of
   frame height** between the two chained frames. We take the conservative side.

Frame capture ladder: `ffmpeg` → **macOS AVFoundation** (no install needed; verified extracting a
2560×1440 frame at 15.034 s) → export from the platform timeline.
It never passes off a first frame as a last frame.

### Every step waits for you

```bash
python3 scripts/mvstudio.py confirm --status
python3 scripts/mvstudio.py confirm --step canon --note "人设没问题"
python3 scripts/mvstudio.py confirm --all
```

Confirmation points are written to `workspace/confirmations.json` — auditable, revocable:

```
gate → analyze → lyrics → canon → threeview → styles → segments
     → prompt-01 … prompt-N      every single prompt
     → chain-01  … chain-N       every segment's output and tail frame
     → ending → render → validate → pack
```

`render` and `pack` **refuse to continue (exit 5)** while anything is unconfirmed, unless you pass
`--unattended`. (MiniMax Design's own hands-on review describes the user's only two actions as
*"确认，以及等"* — confirm, and wait. The rhythm matches.)

### What is machine-checked

Not "looks good" — the things that can be asserted:

```
segments = ceil(duration / 14.5), each ≤ 15 s, contiguous
every camera word is in H3's official 20-term vocabulary
every background lyric element is derivable from that segment's lyrics
≥ 3 distinct art movements across the film, never the same one twice in a row
six sections present, in order, zero Markdown, ≤ 7000 chars per prompt
no music-generation instruction anywhere
the six render-critical canon fields are filled
```

---

## 中文

### 为什么是 14.5 秒

H3 的 `duration` **只接受 4–15 的整数**；而它的帧网格（`17k+5`）意味着
请求 15 秒实际交付 **362 帧 ≈ 15.083 秒**。

所以两个数字被刻意分开：

| | 值 | 为什么 |
|---|---|---|
| 音乐切点 | **14.5 秒**，吸附到最近的小节线 | 音乐上干净，也是你要的单位 |
| H3 `duration` | **15** | 「实出时长仍能盖住音乐」的最小合法整数 |
| 实出 | **15.083 秒** | 已在真实 H3 产出上核对 |
| 可用 | 14.5 秒 | 多出的 **0.58 秒是接缝重叠量**——把缝藏在最快的那一下动作里 |

单纯向上取整会**悄悄截断音乐**（请求 6 秒只交付 5.875 秒）。
`2d-limited-mv-studio` 取的是「实出时长仍能盖住音乐」的最小整数。

### 每条提示词的固定六段

```text
人物与参考保持一致性：  参考素材职责 + 完整 Character Canon + 漂移禁令
风格提示词：           2D · limited animation · hand-drawn · flat composition + 本段画风
内容提示词：           延续上一帧的接续句，然后逐镜头写
integrated_multimodal_description:  参考 / 歌词 / 音乐 / 舞蹈 / 剪辑如何协同
overall_soundscape:    环境音与身体动作的物理声音
non_diegetic_music: N/A
```

`N/A` 不是省略。**你已经自己上传了原曲**，这里没有任何一句要求模型作曲——
这同时避开了官方列出的失败模式：一边要配乐、一边禁配乐。

### 最后一个手势

站定是最偷懒的收尾。观众记住的是最后一个动作。
`2d-limited-mv-studio` 提供 **八种可直接写进提示词的收尾效果**，并按音乐自己的收束性格排序
（见上方英文表格 / `python3 scripts/mvstudio.py endings`）。

每一种都**不改变人物身份**。**消失的是「画」，不是「人」。**

### 尾帧续接

```
C1 ──它的最后一帧──▶ C2 ──它的最后一帧──▶ C3 ──▶ C4
```

上一段的**最后一帧**成为下一段的**第一帧**。这是模型无法争辩的连续性证据——
它看到的是同一张图。

随之而来两条硬约束，其中一条是值得点明的设计张力：

1. **画风转换发生在段内。** 续接的首帧会把上一段的画风一起带进来。
   我们没有在「接得上」和「每段换画风」之间二选一，而是两个都要：
   `0–1.5 秒`保持上一帧的画风与姿势，之后世界在**同一个镜头内**转场。
   转场本身变成了一个事件，而不是一次硬切。
2. **续接时不要换姿势。** 一条第三方现场经验（未经官方证实，见
   `references/platform-playbook.md`）：首尾帧之间垂直位移超过**画面高度 12%**
   容易肢体撕裂。我们取保守的一侧。

取帧降级：`ffmpeg` → **macOS 自带 AVFoundation**（无需安装；实测取出
2560×1440、位于 15.034 秒的精确尾帧）→ 平台时间轴导出。
**绝不拿首帧冒充尾帧。**

### 每一个步骤都等你确认

确认点落盘在 `workspace/confirmations.json`，可查、可撤销：

```
gate → analyze → lyrics → canon → threeview → styles → segments
     → prompt-01 … prompt-N      每一条提示词
     → chain-01  … chain-N       每一段的输出与尾帧
     → ending → render → validate → pack
```

未确认时 `render` / `pack` **拒绝继续（exit 5）**，除非显式 `--unattended`。

### 机器校验的是这些

```
段数 = ceil(时长 / 14.5)，每段 ≤15s，首尾相接
运镜全部落在 H3 官方 20 词表内
每个背景歌词元素都能从该段歌词推出
整片穿越 ≥3 种画风，且相邻两段不重复
六段齐全且有序，零 Markdown，每条 ≤7000 字符
全文没有任何生成音乐的要求
六个渲染关键 Canon 字段已填满
```

---

## Quick start

```bash
git clone <this repo> ~/Desktop/2d-limited-mv-studio && cd ~/Desktop/2d-limited-mv-studio

python3 scripts/mvstudio.py doctor          # environment check
python3 scripts/mvstudio.py all             # deterministic pipeline
python3 scripts/mvstudio.py endings         # pick the last gesture
python3 scripts/mvstudio.py confirm --all   # confirm each step
python3 scripts/mvstudio.py render          # six-section package
python3 scripts/mvstudio.py validate        # must exit 0
python3 scripts/mvstudio.py pack --platform xiaoyunque
```

Runs from any directory with `--project <writable dir>`. If the skill folder itself is read-only
(shared install, sandboxed session), the CLI tells you exactly which command to run instead.

---

## Platforms

**Best on 小云雀 and MiniMax Design** — this skill is tuned for their cut, first/last-frame and
AI-edit features. **Other platforms work too**: anything that accepts an uploaded asset plus a
per-segment prompt can run the package; with `--platform generic` you get a canvas-agnostic
playbook instead of a platform-specific one.

**最佳平台是 小云雀 与 MiniMax Design** —— 本技能专门适配了它们的切割、首尾帧与 AI 剪辑能力。
**其他平台同样可以挂载运行**：任何支持「上传素材 + 逐条提示词」的画布都能跑，
`--platform generic` 会给出与画布无关的通用操作单。

| | 小云雀 | MiniMax Design |
|---|---|---|
| cut | 智能分镜 / 时间轴切割 | AI 剪辑（自然语言）——实测「裁掉最后 2 秒」通过 |
| first frame | 首尾帧模式 | 尾帧作为首帧参考；或 3D 导演台先摆姿势 |
| identity lock | 角色库 / 局部重改 | 资产中心（人物锚） |
| rhythm | 逐条提交 | Agent **先反问确认**再动手 |

The division of labour: **the skill cuts the music, the platform cuts the picture.**
Full playbook, each platform's pitfalls, and the provenance and confidence of every claim:
`references/platform-playbook.md`.

分工是：**音乐由本技能切，画面由平台裁。** 完整落地手册、各自的坑、以及每条结论的来源与
可信度，见 `references/platform-playbook.md`。

---

## Install

<a id="install"></a>

```bash
bash install-to-dsh.sh ~/my-project    # symlink into <project>/.dsh/skills/2d-limited-mv-studio
```

---

## Built with DeepSeek Harness

This is an **agent skill for DeepSeek Harness (DSH)** — composed so any DSH agent can mount it,
and equally usable from Claude Code, Codex or Cursor, because it is just `SKILL.md` plus
zero-dependency Python.

这是一个 **DeepSeek Harness（DSH）智能体技能**，任何 DSH agent 都能挂载；
因为它就是 `SKILL.md` + 零依赖 Python，在 Claude Code / Codex / Cursor 里同样可用。

**Community tags:** `deepseek-harness` `dsh` `agent-skill` `ai-video` `minimax-h3`
`music-video` `prompt-engineering` `2d-animation` `lyrics` `art-direction` `xiaoyunque`

---

## Requirements

- **Python ≥ 3.7**, standard library only. The whole pipeline runs with **zero third-party
  dependencies** (tested on 3.9.6 system Python).
- Optional, each strictly additive:
  - `ffmpeg` **or** macOS `afconvert` — cut non-WAV audio
  - macOS **AVFoundation** (built in) — extract exact last frames
  - `numpy` / `librosa` — sharper BPM and spectral analysis
  - an art-style library (147 movements with layered prompts) — path is configurable; without it
    the skill degrades to a built-in media palette and says so

---

## Tests

<a id="tests"></a>

```bash
python3 -m unittest discover -s tests -t tests
# Ran 119 tests … OK
```

119 tests, zero dependencies, including an end-to-end run (synthetic assets → `all` → the draft
must refuse to render → fill → render → validate → pack) and a **privacy guard** that fails the
build if a project-specific name, a private prompt set or a hardcoded local path ever enters the
package.

---

## Repository layout

```
2d-limited-mv-studio/
├── SKILL.md                    the skill itself — workflow, hard gates, DoD
├── config/defaults.yaml        tunable parameters (directorial judgement is not here)
├── scripts/
│   ├── mvstudio.py                single entry point, 15 subcommands
│   └── lib/
│       ├── beats.py            beat grid · bar snapping · 14.5 s segmentation · H3 duration contract
│       ├── slicer.py           actually cuts audio (ffmpeg → afconvert → wave)
│       ├── h3render.py         six-section renderer (mv / ref / i2va / t2va)
│       ├── chain.py            last-frame chaining across segments
│       ├── frames.py           frame capture (ffmpeg → AVFoundation → platform export)
│       ├── endings.py          eight directable endings
│       ├── styleroutes.py      six fusion routes through art history
│       ├── threeview.py        character turnaround sheet
│       ├── confirm.py          per-step confirmation ledger
│       ├── platforms.py        小云雀 / MiniMax Design adapters
│       ├── gates.py            the machine-checkable gates
│       ├── director.py         draft + worksheet
│       ├── materials.py        material & duration gates
│       ├── canon.py            character canon scaffold
│       ├── pack.py             the upload package
│       ├── music.py            audio analysis (librosa → numpy → stdlib)
│       ├── audioprobe.py       ffprobe → afinfo → pure Python
│       ├── imgprobe.py         image probe & palette, pure Python
│       ├── lyricsrc.py         lyrics sources (embedded / lrc / srt / vtt / txt / ASR)
│       ├── artbridge.py        bridge to the art-style library
│       ├── miniyaml.py         tiny YAML reader (no PyYAML)
│       └── common.py           paths, config, logging, degradation
├── references/                 method, vocabularies, official H3 guides
└── tests/                      119 tests, zero dependencies
```

---

## Design notes

A few decisions that were not obvious, and the reasoning behind them:

**Character canon lives in the official slot, not the body.**
One source method insists every prompt restate the full character canon; another insists you must
never describe appearance in the body, because text and reference image fight and the model drifts.
Both are right, in different places. H3's full-reference mode has `subject_definitions` and
`retention_analysis` — the slots the format reserves for exactly this. Canon goes there; the body
stays clean.

**Degrade loudly, never quietly.**
No `ffmpeg`? You get a millisecond-accurate cut sheet and are told to cut it yourself — not a
silently wrong result. No frame extractor? An error and a route to the platform's own export.
Every fallback is recorded with its impact.

**Colour is not decoration.**
Art-movement choice is indexed from the lyrics, and every background element must be traceable back
to the line it sits under. Random ornament is a validation failure, not a style.

---

## License

MIT — see [LICENSE](LICENSE).

<div align="center">

*One body. Many worlds. The same face at the last frame.*
*一具身体，许多世界，最后一帧上还是同一张脸。*

</div>
