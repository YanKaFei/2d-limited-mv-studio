# 画风图鉴 · 六条融合路线

> **不要问用户「你想要什么风格」。** 那样得到的通常是「日系」「赛博朋克」这类泛化词。
> 真正决定成片差别的是**融合语法**——人物在世界里被什么媒介不断重印。
>
> 风格词一律**先查 art-aesthetic-vault**（AGENTS.md 硬规则），
> **禁止凭记忆编造流派术语**。

---

## 一、六条路线

| id | 路线 | 媒介 | 为什么是它 |
|----|------|------|-----------|
| `print-decay` | **PRINT DECAY · 印刷衰减** | risograph / xerox / halftone / 错版套印 / 报纸网线 | 人物是唯一清晰的印版，世界每段错版套印一次。适合社评、被评价、自我怀疑、表格/标签类歌词 |
| `paper-world` | **PAPER WORLD · 纸与剪** | 撕纸拼贴 / 剪纸层 / 复印质感 / 平涂赛璐珞 | 世界真的是纸片，深度靠图层不靠透视。适合童年、伙伴、房间、记忆碎片 |
| `ink-line` | **INK LINE · 线即世界** | 石墨 / 毛笔水墨 / 炭笔 / 擦除 / 蓝晒 | 画面由线构成、由线消失，轨迹可以被擦掉一半。适合孤独、遗忘、告别、水面/影子/风 |
| `gradient-dream` | **GRADIENT DREAM · 渐变幻景** | 新版画渐变 / 喷笔分带 / 胶片颗粒 / 赛璐珞叠加 | 世界在人物背后一整块一整块换色，人物一帧不变。适合夕阳、季节、思念、旅途 |
| `folk-geometry` | **FOLK GEOMETRY · 民俗几何** | 平涂纹样 / 金箔 / 矿物颜料 / 丝网重复 | 纹样当节拍器，每过一个重拍多生成一层。适合祝福、团圆、民俗、反复副歌 |
| `pop-superflat` | **POP SUPERFLAT · 平面波普** | 平涂乙烯色 / 贴纸描边 / 网点 / 硬像素边 | 一切压成一个贴纸面，人物是面上唯一会动的东西。适合可爱但不安、网络、副歌反复 |

每条路线**自带 ≥3 种画风的递进**（`movement_per_segment`），排序按**歌词意象命中数**。

---

## 二、库怎么查

```bash
VAULT=~/Desktop/art-aesthetic-vault/.repo

python3 $VAULT/artvault.py categories                      # 6 大类
python3 $VAULT/artvault.py search "霓虹 雨夜"               # 模糊
python3 $VAULT/artvault.py search "压抑但华丽的光" --semantic # 描述性说法用语义
python3 $VAULT/artvault.py layers 巴洛克                    # 七层提示词（省 token）
python3 $VAULT/artvault.py palette 赛博朋克                 # 配色
python3 $VAULT/artvault.py related 立体主义                 # 关联流派
```

**拼提示词**（把创意直接交给它，自动按意图分层）：

```bash
python3 $VAULT/artvault.py compose \
  "雨夜霓虹街头的赏金猎人，要巴洛克的光照，赛博朋克的构图" \
  --subject "a female bounty hunter in a wet neon alley"
```

输出：分层结果 + 正向 + 负向 + 配色 + 视频层 + **冲突消解记录**。

---

## 三、⚠️ 冲突消解：拿掉了什么，必须说出来

跨流派混搭时**负向词会打架**。例：浮世绘禁止 `cast shadows`，
巴洛克光照却要 `deep shadows`。

`compose` 默认把打架的负向词**从负向提示词里拿掉**，拿掉了什么在 `dropped` 字段里。

> **交付时要提一句你拿掉了什么、为什么** —— 别默默丢掉。

想看未处理的原样合集（自己判断）：加 `--keep-conflicts`。

**注意**：`compose` 只能抓**词串包含**层面的冲突。
语义冲突（例：`op-art` 的「representational subject」vs 我们要放人）要人判断。

---

## 四、用库里的一层，不是整段照抄

1. `artvault.py --json layers <流派>` 拿到七层
2. **只取光照层 / 色彩层 / 构图层 / 媒介层**
3. 把主体描述接在最前面

七层结构大致是：主体 / 风格 / 光照 / 色彩 / 构图 / 媒介 / 情绪。

---

## 五、与 2D 限制感的关系（最容易漏的一步）

库里的流派多半是**静态画面**语言。落到 H3 时必须补上动画机制：

```
animation on twos / held frame / stepped animation / replacement animation /
smear frame / boiling line
```

否则会漂成「会动的插画」，而不是「有动画限制感的影像」。

**每个 `style_prompt` 必须同时含**：

```
2D · limited animation · hand-drawn · flat composition
```

（这是机器校验项，缺一个就红。）

---

## 六、色彩叙事

色彩第一来源：**Character Canon 的 `dominant_colors`**，再结合歌词与情绪变化。

- 压迫 → desaturated / grey / black / bureaucratic palette
- 主体重新出现 → character original colors dominate again

例：`print-decay` 用 `#E8503A / #1D4ED8 / #F4EFE6 / #111111`——
两组互补色相对峙，正好是「纸底 vs 颜料」的色彩骨架。

---

## 七、库不可用时

降级到 `art-medium-map.md` 的内置媒介表 + 各路线自带的 `fallback_medium`。
**手法仍然正确，只是流派术语不如库中精确**——这一点必须在报告里写明，
不要假装查过库。
