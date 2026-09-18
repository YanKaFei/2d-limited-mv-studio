# 舞蹈语汇与歌词驱动编舞

核心形式：**同一个人物持续跳舞。** 不是「14.5 秒舞蹈测试 × N」。

---

## 安全动作（人物一致性优先）

step-touch / side step / side bounce / shoulder pulse / shoulder hit / arm sweep /
arm extension / hand accent / wrist movement / heel step / small jump / body
isolation / head accent / hip shift / frontal groove / weight transfer。

## 慎用

360 spin / backflip / floor choreography / fast body rotation / extreme
foreshortening / hands covering entire face / long back-facing shot / extreme
acrobatics。

原因：这些动作最容易造成**人脸丢失、比例漂移、身份崩解**——
**人物的可识别性优先于动作难度**。

---

## 歌词驱动编舞

| 歌词 | 动作设计 |
|------|----------|
| 抓不住 | 重复三次向前抓，每次都差一点 |
| 他们要我微笑 | 每次重拍机械抬起脸，用手势形成固定笑容 |
| 越来越远 | 人物向自己的轮廓靠近，轮廓同步远离 |
| 被困住 | 动作在若干外部轮廓内被限制，越用力越被框住 |
| 被衡量 | 每次重拍动作被「按暂停」，然后继续 |
| 忘记 | 动作被擦除：抬手的轨迹上一半消失 |
| 还在跳 | 动作不停，但世界在背后换掉一层 |

**本技能把这件事机器化了**：`lyric_action_binding` 逐句绑定，每条挂上**第几拍**。

---

## 舞蹈与音乐的分工

- 音乐决定**什么时候**变化：重拍上做 accent / hit / hold，小节线上换动作组。
- 段落能量决定**动作幅度**：quiet 段只做 isolation；peak 段允许全身与抽帧。
- **起音密度**（`rhythmic_density`）决定**抽帧程度**：

| 起音密度 | 动画机制 |
|---|---|
| < 1.2 | `animation on twos` + 每个重拍 hold，稀疏关键帧，不补间 |
| 1.2 – 2.5 | `on twos` + 反拍 stepped accent + 偶发 smear frame |
| > 2.5 | 重音 `on ones`、其余 `on twos` + 密集 smear + 姿势替换 |

---

## 连续性

- 每条 prompt 先看上一段的**结尾动作与转场**，再决定本段起手式。
- 相邻段之间**至少保留一个动作元素**（同一手势、同一朝向、同一重心）。
- 绝不允许「上一段结束在左侧抬手，下一段开始在右侧下沉」这种无因跳跃。

`continuity_from_previous` 与 `hook_to_next` 两个字段是**必填且被校验的**——
缺任何一个，校验直接红。

---

## 安全运镜 ↔ 动作的搭配

| 动作类型 | 适合的运镜 | 为什么 |
|---|---|---|
| 原地 isolation | `Static Shot` | 动作本身就是信息，别抢 |
| 全身 sweep | `Pan Left/Right` 小幅度 | 跟得住，又不破坏平面感 |
| 转身 | `Truck Left/Right` | 平移让转身看起来是「画面上滑过去」 |
| 跳跃最高点 | 硬切 / 换画风 | 接缝藏在最快运动里 |
| 定格 pose | `Push In` 小幅度慢速 | 唯一的「推进」用在这里最值 |
| 末段收束 | `Pedestal Up` + `Pull Out` | 先看见人再看见世界 |

---

## 舞蹈质量闸门

- [ ] 人物持续舞蹈
- [ ] 动作与歌词相关（`lyric_action_binding` 有内容）
- [ ] 动作与音乐相关（绑定挂了拍号）
- [ ] 没有大量危险复杂动作
- [ ] 相邻段动作连续（`continuity_from_previous` / `hook_to_next` 都有）
