# 三视图（人物转面表）规范

> **一张正面图丢给视频模型，转个身脸就崩。**
> 三视图把发型体积、侧面轮廓、背面服装结构钉死——这是人物一致性最便宜的一道保险。

---

## 一、为什么必须有这一步

一条 MV 会被切成 **N 个 14.5 秒独立生成**。每一代模型都看不到别人。
只有两样东西能让「始终是同一个人」成立：

1. **文字 Canon**（写在每条 prompt 的参考信息段落里）
2. **参考图**（`<Picture 1>` 原始图 + `<Picture 2>` 三视图）

而用户通常只给**一张正面图**。三视图把这一张图**展开**成模型真正需要的信息量。

它同时解决三个问题：

| 问题 | 三视图怎么解 |
|---|---|
| 用户只给一张正面图 | 补齐侧面／背面／四分之三 |
| 转身时脸崩 | 侧面轮廓被明确锁定 |
| 服装结构漂移 | 背面结构被明确锁定 |

---

## 二、生成规格

| 项 | 值 |
|---|---|
| 视角 | **正面 / 四分之三侧面 / 正侧面 / 背面** |
| 附加格 | 头部特写 + 色标（colour chart） |
| 排版 | 四格等分一行，**同一比例**，脚底对齐同一基线 |
| 姿势 | 放松 A-pose，手臂略离身体；所有格用同一套姿势族 |
| 背景 | 中性平灰，**无场景** |
| 画法 | 单一连续线宽，所有格同一遍渲染 |

指令：`python3 scripts/mvstudio.py threeview` → `output/latest/threeview.md`
（内含可直接粘贴的**中英双语**提示词 + 负向词。）

---

## 三、负向词为什么这么写

```
multiple characters, different character, different face, different outfit,
wardrobe change, extra accessories, inconsistent scale,
different art style between panels, 3D render, photorealistic, depth of field,
motion blur, watermark, signature, text, cropped limbs, extra limbs,
background scenery, colour cast between panels
```

这治的是**三视图综合症**：模型把「多角度」理解成「多个人」，于是每格换一套衣服。
`different outfit` 与 `multiple characters` 是必须写的两条。

---

## 四、出图之后怎么用

1. 存成 `input/character/threeview.png`；
2. 重跑 `python3 scripts/mvstudio.py canon` —— `materials.discover` 会按文件名
   （`threeview` / `turnaround` / `三视图` / `setting`）自动认出来；
3. 渲染时它作为 **`<Picture 2>`（character turnaround reference）** 与原始图
   `<Picture 1>` 一起上传；
4. **官方规则（O14）**：这张图**只用来定义角色**，所以它被引在 `<Subject 1>` 的
   定义里，而**不是**单独建一条 `<Picture 2>` 帧条目。

---

## 五、一致性检查单

`threeview.consistency_checklist(canon)` 逐项检查。缺哪个字段，三视图就会在哪一维度崩：

| 字段 | 缺了会怎样 |
|---|---|
| `hair` | 背面与侧面的发型体积各画各的 |
| `eyes` | 四分之三视角的瞳色/眼型漂移 |
| `face` | 五官比例在不同格里不一致 |
| `costume` | 背面服装结构被模型自由发挥 |
| `accessories` | 核心配饰在部分格里消失 |
| `silhouette` | 整体比例与轮廓对不上 |
| `stable_identifiers` | 跨 14.5 秒的条与条之间没有可校验的锚点 |

**缺任何一项，渲染器拒绝输出。** 宁可不生成，也不生成会漂移的东西。
