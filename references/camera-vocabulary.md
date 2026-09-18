# 运镜分层库 · 丰富角度，但不破坏平面感

> **问题**：2D MV 也需要丰富的镜头角度，否则每条都是「中景推到近景」。
> **约束**：MiniMax H3 只认它官方那 **20 个运动词**。写 `crane shot`、`whip pan`、
> `dolly zoom` 这类实拍术语，模型不认——`gates` 也会拦。
>
> **所以丰富化不能靠编新词，只能靠分层。**

---

## 一、六层模型

按 [Runway 的 AI camera prompts 参考](https://runway.com/resources/ai-camera-prompts)
给的公式组织：

```
[景别] + [角度] + [运动 + 方向 + 速度 + 与主体的关系] + [主体与动作] + [这个镜头要揭示什么]
```

| 层 | 字段 | 词从哪来 | 是否受 H3 限制 |
|---|---|---|---|
| 景别 | `shot_size` | 10 个有出处的景别（大远景 → 大特写） | 否，自然语言 |
| **角度** | `angle` | 12 个角度 | 否，自然语言 |
| 运动 | `camera` | **只能**官方 20 词 | **是** |
| 构图 | `framing` | 12 个构图 | 否 |
| 焦 | `focus` | 4 个（深/浅/柔/移焦） | 否 |
| 2D 专属 | `move_2d` | 10 个 2D 工业术语 | 否 |
| 关系 | `camera_relation` | 7 个关系动词 | 否 |
| 揭示 | `purpose` | 自由 | 否 |

**关键洞察**：H3 缺失的从来不是「运动词」，而是**角度层**。原来的库里只有
平移推拉，一个角度都没有——这才是「运镜不够丰富」的真正原因。

---

## 二、角度层（这一层最值钱）

| id | 中文 | 什么时候用 |
|---|---|---|
| `eye_level` | 平视 | 中性、可信 |
| `low_angle` | 仰角 | 力量感，把她抬高；副歌/高潮 |
| `high_angle` | 俯角 | 脆弱、**被观看、被评价**——「被审视」类歌词首选 |
| `dutch_canted` | 荷兰角 | 失衡不安。**全片 1–2 次就够**，多了廉价 |
| `overhead_top` | 正俯视 | 把舞蹈看成平面图形，最接近 2D 构成 |
| `birds_eye` | 鸟瞰 | 人在图案里；民俗几何 / 满屏纹样路线 |
| `worms_eye` | 虫视 | 压迫感极强。**慎用**，比例容易失真 |
| `over_the_shoulder` | 过肩 | 前景遮挡——2D 里正好做**前景纸层** |
| `pov` | 主观视角 | 「看见了什么」的歌词 |
| `reverse_angle` | 反打 | 与上一镜成对使用 |
| `flat_frontal` | **完全正面（2D 专属）** | 取消透视，人物与画面平行——最「动画」的角度 |
| `rear_view` | 背面 | 背对观众跳舞；⚠️ 别停太久，会丢脸部识别 |

---

## 三、2D 专属运镜（本技能的身份所在）

这一层是实拍运镜库里**没有**的，也是 2D MV 先锋性的来源：

| id | 中文 | 做什么 |
|---|---|---|
| `rostrum` | 摄影台推移 | 画面像放在摄影台下平移，**透视完全不变** |
| `multiplane_parallax` | 多层视差 | 前景纸最快、背景几乎不动——**2D 唯一正当的「景深」** |
| `cel_slide` | 赛璐璐滑动 | 背景不动、人动。卡点最省的一招 |
| `registration_shift` | 套印偏移 | 整幅脱版、色层错开几像素——**「身份不稳」的视觉语法** |
| `paper_wipe` | 纸张推移 | 转场，比 dissolve 有材质感 |
| `iris_2d` | 圆形遮罩 | 默片语法，实验段落很成立 |
| `hard_crop_reframe` | 硬裁切重构 | 不动机位只改裁切——最省的一次「换镜」 |
| `split_screen` | 分屏 | 「另一个自己」用这个，**不改人物 Canon** |
| `exposure_flash` | 曝光闪白 | 重拍上的强调；抽帧手感的关键 |
| `hold_frame_drift` | 定格微移 | 「不动」但不死板；quiet 段落主力 |

**默认策略（保守）**：只在 `Static Shot` 的镜头上加 2D 招——
**机位锁死、画面仍在动**，这正是 limited animation 的手感来源，
而且完全不破坏平面感。

---

## 四、实拍术语 → 官方词映射（20 条）

丰富化最实用的一张表：**用电影术语思考，输出官方词**。

| 实拍术语 | → 官方词 | 说明 |
|---|---|---|
| `dolly_in` | `Push In` | 机位真的前进，背景随之变化——**不是变焦** |
| `crash_zoom` | `Zoom In` + 大幅度 + 快 | 极速变焦＝突然强调。2D 里等于放大原画 |
| `whip_pan` | `Pan Right` + 大幅度 + 快 | 带运动模糊，**两个重拍之间最高效的转场** |
| `crane_up` | `Pedestal Up` | 2D 里用机位上升代替摇臂 |
| `drone_rise` | `Pedestal Up` | ⚠️ 实拍无人机在 2D MV 里是错语汇，降级并只在远景用 |
| `vertigo_dolly_zoom` | `Zoom In` + `Truck Right` | 变焦与机位反向同时进行。**全片最多一次** |
| `handheld` | `Shake Slightly` | ⚠️ 建议全片只用在 1–2 个镜头，多了破坏平面感 |
| `steadicam` | `Tracking Shot` | 平稳跟拍 |
| `orbit` / `arc_soft` | `Arc Shot` | 大幅度绕满 / 小幅度弧线 |

（完整 20 条见 `camera-library.json` 的 `cinematic_to_official`，
每条都带幅度、速度与理由。）

**不变量**：每个 `official` 都必须在 H3 官方 20 词内。
`tests/test_mvstudio.py::TestCameraEnrichment` 会强制这条——
**不允许教用户写模型不认的词。**

---

## 五、三条硬规矩（都是踩出来的）

### 1. 固定镜头必须**再用自然语言加一次锁**

模型天生要制造运动，尤其在远景上会自己飘。Runway 的参考给的做法是补一句：

```
The camera is entirely motionless for the duration of the scene,
with movement only occurring from the subject.
```

本技能对每个 `Static Shot` 自动追加这句。

### 2. 运动镜头必须写清**相机与主体的关系**

不写 → 模型让两个运动各走各的，表现为**抖动、人物像在飘**。

```
✅ the camera follows her
✅ the camera leads her, backing away as she advances
✅ the camera moves at exactly her pace
```

`camera_relation` 是必填；运动镜缺它 → 校验红。

### 3. **运镜丰富 ≠ 运镜展览**

每段运动镜头 **≤ 一半**（`ceil(n/2)`），其余压回固定镜头。
超出 → 校验红。

理由：这是 2D MV，不是运镜 demo。多出来的动感应该由
**2D 专属招**提供——机位不动，画面在动。

---

## 六、来源与可信度

| 内容 | 来源 |
|---|---|
| 景别 / 角度 / 构图 / 焦 四层词表 | [patipanpealt/alt-cinematography-reference](https://github.com/patipanpealt/alt-cinematography-reference) 的 `content.json`（结构化摄影参考） |
| 相机提示词公式、固定镜头加锁句、关系动词、不要堆动词、dolly≠zoom | [Runway · AI camera prompts](https://runway.com/resources/ai-camera-prompts)（一手厂商参考，含 Gen-4.5 实测） |
| 2D 动画运镜（多层视差、摄影台） | [DigiCel · Camera Moves in 2D Animation](https://digicel.net/camera-moves-in-2d-animation/) · 动画工业通行术语 |
| anime 摄影术语背景（撮影／Satsuei） | [Sakuga Blog Glossary](https://blog.sakugabooru.com/glossary/) |
| 官方 20 个运动词 | [MiniMax H3 官方提示词指南](https://github.com/MiniMax-AI/MiniMax-H3)（`references/official/`） |

> 三处第三方来源**只用于词汇与做法**；落地到 H3 时一律经过
> `cinematic_to_official` 映射回官方词。凡是我们自己判断的（例如
> 「2D 招加在固定镜头上」），都标了「本技能的做法」。
