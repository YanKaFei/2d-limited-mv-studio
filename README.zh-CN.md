<div align="center">

# 2D Limited MV Studio

**二次元 MV 工坊 · 2D 运镜限制 · 一张图，一首歌，许多个世界**

*限制就是风格。*
*世界不断变异，角色始终稳定。*

[![Built with DeepSeek Harness](https://img.shields.io/badge/built%20with-DeepSeek%20Harness-4B4BFF)](#built-with-deepseek-harness)
[![DSH Skill](https://img.shields.io/badge/DSH-agent%20skill-111111)](#install)
[![Target](https://img.shields.io/badge/target-MiniMax%20H3-FF4E8A)](#platforms)
[![Best on](https://img.shields.io/badge/best%20on-小云雀%20%C2%B7%20MiniMax%20Design-3DD6D0)](#platforms)
[![Tests](https://img.shields.io/badge/tests-173%20passing-2E7D32)](#tests)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-8A9BA8)](#requirements)
[![Camera](https://img.shields.io/badge/camera-2D%20limited%20%C2%B7%20no%203D-6B4FBB)](#the-camera-never-leaves-the-paper)

[**中文**](README.zh-CN.md) · [English](README.md) · [한국어](README.ko.md) · [日本語](README.ja.md) · [Français](README.fr.md)

</div>

---

> 一条 MV 不是一串好看的画面。它是一具**拒绝停下来的身体**：周围的世界被反复重画——
> 印刷、撕开、刻蚀、溶解、错版——而到最后一帧，她仍然明确地是同一个人。

**一键生成二次元人物 MV 音乐动画。** 给它一张人物图和一首歌，它交回一整套经过机器校验的
**MiniMax H3** 提示词包：音乐按 **14.5 秒**切分，人物穿越多种艺术流派，歌词里的实物落进背景，
运镜只用 H3 官方词表，并且每一段都用上一段的**真实尾帧**续接。

## 为什么是 14.5 秒

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

## 每条提示词的固定六段

每条提示词都使用同一个固定形状，顺序如下：

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

## 镜头永不离开纸面

这不是一台「碰巧对着画的实拍摄影机」，而是**一台架在纸堆上的摄影机**——这才是重点。

摄影机被允许做什么，是被**刻意限死**的：

- **不做 3D 运镜。** 不绕空间、不无人机上升、不飞越、不穿越透视。
  深度只来自**图层**：前景纸 + 人物赛璐珞 + 背景插画 + 图形叠加，绝不来自移动的视点。
- **运动在 2D 里被写出来。** 摄影台推移是画面**平移、透视完全不变**；
  赛璐珞滑动是背景纹丝不动、只有人在动；多层视差靠图层速度差——
  这是 2D 唯一诚实的那种「景深」。
- **limited animation 是质感本身。** 定格、on twos、stepped motion、pose-to-pose、
  smear drawing。**不追求丝滑**——追求的是「一张画在该有的样子里动」。
- **错版是语言，不是事故。** 色层错开几个像素，是本技能说「身份松动了」的方式。

运动词被压在 H3 官方那 **20 个**里，正是这个原因——词表一大，摄影机就想离开纸面。
于是我们丰富的是摄影机**在看什么**：角度、构图、焦、以及这一下要揭示什么。

> **我们拿来衡量自己的那条标准**：如果把所有 3D 运镜全拿掉，这条片子还立得住吗？
> 立不住，那它本来就不是一条 2D 片。

## 运镜：六层，而不是一层

H3 只认官方那 **20 个运动词**，别的都不读。所以「丰富运镜」不能靠编新词——
`crane shot`、`whip pan` 模型根本不读。丰富化只能靠**分层**：

```
景别 → 角度 → 构图 → 焦 → 官方运动词 → 相机与主体的关系 → 这一下要揭示什么
```

| 层 | 数量 | 例子 |
|---|---|---|
| 景别 | 10 | 大远景 → 大特写 |
| **角度** | **12** | 低角 / 高角 / 荷兰角 / 俯拍 / 虫视 / 过肩 / POV / **平面正拍（2D 原生）** |
| 构图 | 12 | 三分法、对称、留白、画中画、海报式排布 |
| 焦 | 4 | 深焦、浅焦、柔焦、**变焦（rack）** |
| **2D 专属招** | **10** | 摄影台推移、多层视差、赛璐珞滑动、**套版偏移**、纸张擦拭、光圈、硬裁重构、分屏、曝光闪白、定格漂移 |
| 关系 | 7 | 跟随 / 引领 / 同速 / 观察 / 揭示 / 对抗 / 环绕 |

**原来缺的从来不是运动词，是角度层。** 一个只有平移推拉的库，镜头当然是薄的。

三条硬规矩，全部机器校验：

1. **固定镜头必须再用自然语言加一次锁。** 模型会飘，尤其是在远景上。每条
   `Static Shot` 都带上「摄影机在整场中完全不动，只有主体在动」。
2. **运动镜头必须写清与主体的关系。** 不写，两种运动各跑各的钟——看起来就是抖动、
   人物像在飘。
3. **运镜丰富 ≠ 运镜展览。** 每段运动镜头**至多一半**，其余全部锁死，动感交给
   **2D 专属招**——机位锁死、画面在动。

实拍术语只用于**思考**，输出前一律映射回官方 20 词
（`crane_up → Pedestal Up`，`whip_pan → Pan Right + large + fast`）。
测试会强制每个映射目标都是真官方词——这个技能不会教你写模型根本不读的词。
完整词表与来源：`references/camera-vocabulary.md`。

## 让舞蹈「魔性」起来

一支舞之所以洗脑，不是因为编舞复杂，恰恰是因为它**简单到你能跟着做，然后做了八遍**。
所以动作层的核心不是更长的词表，而是**重复的设计**。

| 层 | 字段 | 决定什么 |
|---|---|---|
| **魔性度** | `seg.motion.viral_level` | 这一段重复得多狠——0 克制 → 3 洗脑 |
| **重复表** | `seg.motion.*` | 动作单元长度、循环长度、重复次数、在哪变异、用哪种变体 |
| **记忆点** | `plan.motion_design.hook_id` | 全片**唯一**的招牌动作，每个副歌必出现 |

魔性度**逐段从音乐推**，而且**往后递增**——魔性是攒起来再爆的。哪怕整首歌能量平坦，
你也会得到 主歌克制 → 副歌魔性 → 结尾洗脑。

```bash
python3 scripts/mvstudio.py motion                          # 菜单 + 当前设计
python3 scripts/mvstudio.py motion --hook shoulder_pop_8
python3 scripts/mvstudio.py motion --viral 3                # 全片拉到洗脑
python3 scripts/mvstudio.py motion --segment C2 --viral 0   # 单独一段克制
```

**八种记忆点动作**，各治一种「停不下来」：身体完全不动只有头在点的**点头锁**；
把计数本身变成笑点的**抖肩八连**；越停越久的**跺脚停顿**；
挤压拉伸最出「憨」的**蹲弹**；差一半三次然后超额兑现的**半转重复**。

**五种重复变体**——递增强调、双倍速、半速拖拍、错位半拍卡农，以及**末次截断**
（你正在哼的那个动作突然只做一半）。铁律：**变异是同一个动作的变奏，绝不换动作。**
换了动作，记忆点就断了。

循环表由**拍网格**驱动，不是拍脑袋写「重复 4 次」——这条前提和所有已发表的
音乐驱动舞蹈生成模型一致；我们只取原理，不取依赖，管线仍然零第三方依赖。

## 最后一个手势

站定是最偷懒的收尾。观众记住的是最后一个动作。
`2d-limited-mv-studio` 提供 **八种可直接写进提示词的收尾效果**，并按音乐自己的收束性格排序：

| id | 收尾 | 发生什么 |
|---|---|---|
| `jump_freeze` | **跃起定格** | 完整起跳、在最高点定格，背景被抽走，只剩一条偏移的轮廓 |
| `reach_and_crack` | **伸手裂屏** | 她把指尖推进镜头，整幅画像玻璃一样裂开，白光透出来 |
| `swipe_to_black` | **手一滑黑屏卡点** | 手臂扫过镜头，画面在重拍上精确切黑，只留一道残影 |
| `frame_drop_vanish` | **逐帧抽掉** | 先没有手臂，再没有躯干，动作还在继续，最后只剩一条轮廓线 |
| `misregistration_exit` | **印版退位** | 分层退印：颜色 → 线 → 只剩套版标记 |
| `spin_to_line` | **旋转成线** | 旋转到一半，身体塌缩成一条竖线，然后被自下而上擦除 |
| `paper_tear_exit` | **纸撕离场** | 画面从中间撕开，她从裂口里跳出去 |
| `look_back_fade` | **回望褪色** | 全片唯一的完全停顿——她回头，画面褪成一张旧照片 |

每一种都**不改变人物身份**。**消失的是「画」，不是「人」。**

## 尾帧续接

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

## 每一个步骤都等你确认

```bash
python3 scripts/mvstudio.py confirm --status
python3 scripts/mvstudio.py confirm --step canon --note "人设没问题"
python3 scripts/mvstudio.py confirm --all
```

确认点落盘在 `workspace/confirmations.json`，可查、可撤销：

```
gate → analyze → lyrics → canon → threeview → styles → segments
     → prompt-01 … prompt-N      每一条提示词
     → chain-01  … chain-N       每一段的输出与尾帧
     → ending → render → validate → pack
```

未确认时 `render` / `pack` **拒绝继续（exit 5）**，除非显式 `--unattended`。
（MiniMax Design 自己的上手评测把用户仅有的两个动作写成「确认，以及等」——节奏正好对得上。）

## 机器校验的是这些

不是「看起来不错」，而是能断言的东西：

```
段数 = ceil(时长 / 14.5)，每段 ≤15s，首尾相接
运镜全部落在 H3 官方 20 词表内
每个背景歌词元素都能从该段歌词推出
整片穿越 ≥3 种画风，且相邻两段不重复
六段齐全且有序，零 Markdown，每条 ≤7000 字符
全文没有任何生成音乐的要求
六个渲染关键 Canon 字段已填满
```

## 快速开始

```bash
git clone <this repo> ~/Desktop/2d-limited-mv-studio && cd ~/Desktop/2d-limited-mv-studio

python3 scripts/mvstudio.py doctor          # 环境检查
python3 scripts/mvstudio.py all             # 确定性流水线
python3 scripts/mvstudio.py endings         # 选最后一个手势
python3 scripts/mvstudio.py confirm --all   # 逐步确认
python3 scripts/mvstudio.py render          # 六段提示词包
python3 scripts/mvstudio.py validate        # 必须 exit 0
python3 scripts/mvstudio.py pack --platform xiaoyunque
```

在任何目录下都可以用 `--project <可写目录>` 运行。如果技能目录本身只读
（共享安装、沙箱会话），CLI 会明确告诉你该改跑哪条命令。

## 平台

**最佳平台是 小云雀 与 MiniMax Design** —— 本技能专门适配了它们的切割、首尾帧与 AI 剪辑能力。
**其他平台同样可以挂载运行**：任何支持「上传素材 + 逐条提示词」的画布都能跑，
`--platform generic` 会给出与画布无关的通用操作单。

| | 小云雀 | MiniMax Design |
|---|---|---|
| 切割 | 智能分镜 / 时间轴切割 | AI 剪辑（自然语言）——实测「裁掉最后 2 秒」通过 |
| 首帧 | 首尾帧模式 | 尾帧作为首帧参考；或 3D 导演台先摆姿势 |
| 身份锁 | 角色库 / 局部重改 | 资产中心（人物锚） |
| 节奏 | 逐条提交 | Agent **先反问确认**再动手 |

分工是：**音乐由本技能切，画面由平台裁。** 完整落地手册、各自的坑、以及每条结论的来源与
可信度，见 `references/platform-playbook.md`。

## 安装

<a id="install"></a>

```bash
bash install-to-dsh.sh ~/my-project    # 软链到 <project>/.dsh/skills/2d-limited-mv-studio
```

## 用 DeepSeek Harness 构建

这是一个 **DeepSeek Harness（DSH）智能体技能**，任何 DSH agent 都能挂载；
因为它就是 `SKILL.md` + 零依赖 Python，在 Claude Code / Codex / Cursor 里同样可用。

**社区标签：** `deepseek-harness` `dsh` `agent-skill` `ai-video` `minimax-h3`
`music-video` `prompt-engineering` `2d-animation` `lyrics` `art-direction` `xiaoyunque`

## 环境要求

- **Python ≥ 3.7**，仅标准库。整条管线 **零第三方依赖**（在 3.9.6 系统 Python 上测试）。
- 以下全部可选，且只会更好：
  - `ffmpeg` **或** macOS `afconvert` —— 切非 WAV 音频
  - macOS **AVFoundation**（内置）—— 精确抽取尾帧
  - `numpy` / `librosa` —— 更准的 BPM 与频谱分析
  - 一个画风库（147 种画派、带分层提示词）—— 路径可配置；没有它则降级到内置的
    媒介色板，并会明确说明

## 测试

<a id="tests"></a>

```bash
python3 -m unittest discover -s tests -t tests
# Ran 173 tests … OK
```

173 个测试，零依赖；包括一条端到端流程（合成素材 → `all` → 草稿必须拒绝渲染 → 填满 →
渲染 → 校验 → 打包），以及一道**隐私闸**：一旦项目专属名称、私有提示词集或写死的本地
路径进入发布包，构建就会失败。

## 仓库结构

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
│       ├── motion.py           魔性动作：viral level · beat-driven repeat schedule · hook
│       ├── camera.py           six-layer camera vocabulary (angles, framing, 2D moves)
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
└── tests/                      173 tests, zero dependencies
```

## 设计说明

几个当时并不显然的决定，以及背后的理由：

**人物 Canon 放在官方插槽里，而不是正文里。**
一种来源方法坚持每条提示词都要复述完整的人物设定；另一种坚持正文里绝不能描述外貌，
因为文字与参考图会打架，模型会漂。两种都对，只是位置不同。H3 的完整参考模式有
`subject_definitions` 与 `retention_analysis`——格式正为这件事留的插槽。Canon 放那里，
正文保持干净。

**降级要大声，绝不能悄悄降。**
没有 `ffmpeg`？你会拿到一张毫秒级精确的切点表，并被明确告知自己去切——而不是一个悄悄
出错的结果。没有取帧器？报错，并给出走平台自带导出的路线。每一次降级都会连同影响被记录。

**颜色不是装饰。**
画派的选择由歌词索引，每个背景元素都必须能追溯回它所在的那一句歌词。
随机的装饰是校验失败，不是风格。

## 许可证

MIT —— 见 [LICENSE](LICENSE)。

<div align="center">

*一具身体，许多世界，最后一帧上还是同一张脸。*

</div>
