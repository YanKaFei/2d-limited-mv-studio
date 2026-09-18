# 媒介表与艺术语汇（art-aesthetic-vault 不可用时的降级版）

> 首选永远是用 `scripts/mvstudio.py styles` 查本机的 art-aesthetic-vault
> （147 个流派，含分层提示词）。这份表是**降级**：
> 手法正确，但流派术语不如库中精确。
> AGENTS.md 的硬规则：**不要凭记忆编造流派术语。**

---

## 一、语义 → 媒介

| 歌词语义 | 媒介方向 | 可选流派参考 |
|----------|----------|--------------|
| Memory 记忆 | pencil / erasure / photocopy / faded paper | 铅笔素描、蓝晒、老照片 |
| Social Judgment 被评价 | editorial grid / stamp / form / registration mark / xerox | 构成主义、瑞士国际主义、复印艺术 |
| Fragmented Identity 身份碎裂 | misregistration / double contour / offset printing / mirror layout | 丝网印刷错版、照相制版 |
| Emotional Overflow 情绪外溢 | ink spread / brush overflow / broken frame | 水墨、抽象表现主义 |
| Isolation 孤立 | negative space / held frame / single pencil line | 极简线描、色域绘画 |
| 重复与仪式 | flat pattern fill / gold leaf / screen-printed repeat | 民画、琳派、伊斯兰几何 |
| 可爱但不安 | flat vinyl colour / sticker outline / screentone | 超扁平、波普、Y2K |

---

## 二、艺术语汇库

- **2D Animation**：limited animation / cel animation / held frame / stepped
  animation / animation on twos / animation on threes / smear drawing / boiling
  lines / pose-to-pose / replacement animation
- **Drawing**：graphite / colored pencil / charcoal / ink / marker / oil pastel /
  brush line / contour drawing / scribble
- **Printing**：risograph / xerox / screen print / offset print / misregistration /
  halftone / newsprint
- **Collage**：paper collage / torn paper / cut paper / magazine collage /
  photocopy collage / mixed media
- **Graphic**：editorial design / modernist layout / constructivist composition /
  hard-edge abstraction / poster design / graphic grid / kinetic typography logic /
  color field

---

## 三、禁止的通用 Anime MV 元素

```
dreamy neon city / cyberpunk / magic butterflies / galaxy / stars / particle vortex /
beautiful sunset / anime school / rainy Tokyo / generic city rooftop / huge lens
flare / magic glow / random floating objects / 3D orbit / drone shot / FPV
```

除非歌词明确需要，否则不出现。**渲染器与校验器都会拦这些词。**

---

## 四、2D 摄影机

优先：locked / frontal / rostrum / flat push-in / flat pull-out / horizontal pan /
vertical pan / graphic crop / hard crop / snap crop / poster reframing / 2D
multiplane / paper wipe / graphic occlusion / match cut / hard cut。

禁止：3D orbit / 360 / drone / FPV / rapid fly-through / CG camera / spiraling /
extreme perspective / constant cinematic movement。

深度靠图层：foreground paper + character cel + background illustration + graphic
overlay + multiplane parallax。

---

## 五、风格库不可用时的六条降级池

| 路线 | 降级媒介 |
|---|---|
| `print-decay` | risograph / xerox / halftone / offset misregistration / newsprint / editorial grid |
| `paper-world` | paper collage / torn paper / cut paper / photocopy collage / flat cel / hard-edge abstraction |
| `ink-line` | graphite / brush ink / charcoal / erasure / cyanotype wash / boiling line |
| `gradient-dream` | airbrush banding / film grain / colour field / cel overlay / gradient wash |
| `folk-geometry` | flat pattern fill / mineral pigment / gold leaf / screen print repeat / geometric repeat |
| `pop-superflat` | flat vinyl colour / sticker outline / screentone / hard pixel edge / colour field |
