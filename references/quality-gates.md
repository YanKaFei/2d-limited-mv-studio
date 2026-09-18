# 质量闸门与导演稿 Schema

> **没有断言的规则等于没有规则。** 能机器判定的全部进 `scripts/lib/gates.py`；
> 判定不了的写进导演自检（六问）。

---

## A. 四组机器闸门（`python3 scripts/prism.py validate`）

退出码 `0` 通过 / `1` 有问题。**未通过不许说 DONE。**

### A 时间
- [ ] 段数 = `ceil(duration / 14.5)` 且 ≤ 13
- [ ] 每段 ≤ 15s、时间连续无缝、不重不漏
- [ ] 每段有 `shots`

### B 人物
- [ ] Canon 六个渲染字段齐全：`hair / eyes / face / costume / accessories / silhouette`
- [ ] `stable_identifiers` 非空
- [ ] 粘贴区含 `character reference` / `fully_preserved` / `the only character`
- [ ] 粘贴区**零**人物漂移词

### C 歌词
- [ ] 每段 `background_lyric_elements` 非空
- [ ] **每个元素都能从该段歌词推出**（最长公共子串 / 整词匹配）
- [ ] `continuity_from_previous` 与 `hook_to_next` 都有内容
- [ ] 整条穿越 ≥3 种画风；不是所有段同一画风
- [ ] `mv_concept` 非空

### D 格式
- [ ] 运镜全在官方 20 词表内；幅度/速度写法合法
- [ ] `style_prompt` 含 `2D` / `limited animation` / `hand-drawn` / `flat composition`
- [ ] 无被禁通用元素
- [ ] 粘贴区零 Markdown、每条 ≤7000 字符
- [ ] `non_diegetic_music: N/A` 恰好每条一次
- [ ] 有 `<Audio N>: fully_copy`
- [ ] 英文路线下正文不夹整句中文（逐字引用的歌词与实物名除外）

---

## B. 导演自检（机器判不了的六问）

1. **Character**：从第一秒到最后一秒，是不是明确同一个人？
2. **Lyrics**：为什么这个场景**只属于这首歌**？
   （把它换到另一首歌还完全成立 → **FAILED**，重做）
3. **Music**：画面变化是不是和音乐结构相关？
4. **Dance**：人物是不是在跳**一支持续**的舞？
5. **2D**：即使完全不用 3D 运镜，这条 MV 仍然成立吗？
6. **Art**：它是在做影像作品，还是在换漂亮背景？

---

## C. 渲染器的硬闸门（`prism.py render`，exit 2）

以下任一情况**拒绝渲染**并逐条列出缺什么：

- `_draft` 还是 true
- `mv_concept` 为空
- `character_canon` 任一渲染字段为空，或 `stable_identifiers` 为空
- `art_direction.movement_per_segment` 为空（没选画风路线）
- 任何一段缺创意字段，或缺 `shots`
- `style_prompt` 缺必含词
- 某个 `shots[].camera` 不在官方词表里

这是刻意的：**宁可不生成，也不生成编造的内容。**

---

## D. 导演稿 Schema（`workspace/analysis/director_plan.json`）

```jsonc
{
  "_draft": false,                     // true 时渲染器拒绝输出
  "meta": {
    "duration": 55.745,
    "segment_target_seconds": 14.5,
    "segment_count": 4,
    "bpm": 118.10, "beat_sec": 0.508044, "bar_sec": 2.032176,
    "lyric_mode": "lyrics",            // lyrics | instrumental
    "h3_route": "ref", "lang": "en",
    "style_route": "print-decay"
  },
  "mv_concept": "一句话核心概念",
  "logline": "可选",
  "visual_arc": [
    { "time_start": 0, "time_end": 14.2, "stage": "SINGLE OUTLINE",
      "description": "…" }
  ],
  "motif_dictionary": {
    "water": { "concept": "the self left behind",
               "visual_form": "flat ripple band",
               "evolution": ["水面","复制水纹","错版水纹","碎水纹","空水面"] }
  },
  "lyric_semantic_map": [
    { "time": 4.2, "lyric": "我把影子留在水面",
      "literal_meaning": "…", "emotional_meaning": "…",
      "psychological_meaning": "…", "primary_visual_metaphor": "…",
      "physical_object": "…", "character_action": "…", "transformation": "…" }
  ],
  "art_direction": {
    "route_id": "print-decay", "route_name": "PRINT DECAY · 印刷衰减",
    "movements": ["bauhaus","pop-art","rimpa"],
    "movement_per_segment": ["rimpa","bauhaus","pop-art","rimpa"],
    "primary_medium": "risograph misregistration, xerox grain, halftone dots",
    "palette": ["#E8503A","#1D4ED8","#F4EFE6","#111111"],
    "color_narrative": "…",
    "why_this_medium": "必答：这个媒介为什么属于这首歌",
    "style_negative": "…"
  },
  "character_canon": {
    "name": "@CHARACTER",
    "hair": "…", "eyes": "…", "face": "…",
    "costume": "…", "accessories": "…", "silhouette": "…",
    "stable_identifiers": ["red neck ribbon","blunt bangs"],
    "dominant_colors": ["#A8C8E8","#D94A4A"],
    "forbidden_drift": ["face change","…"]
  },
  "assets": {
    "character_reference": { "path": "input/character/character_ref.png",
                             "role": "character reference", "label": "<Picture 1>" },
    "turnaround_sheet":    { "path": "input/character/threeview.png",
                             "role": "character turnaround reference",
                             "label": "<Picture 2>" },
    "audio":               { "path": "input/music/song.mp3",
                             "role": "original song reused 1:1",
                             "label": "<Audio 1>" }
  },
  "segments": [
    {
      "id": 1, "label": "C1",
      "time_start": 0.0, "time_end": 14.225,
      "audio_seconds": 14.225, "request_seconds": 15,
      "delivered_seconds": 15.083, "headroom_seconds": 0.858,
      "seam_overlap_seconds": 0.858,
      "prompt_seconds": 15.083,
      "is_tail": false, "is_tail_pad": false, "tail_advice": null,
      "snapped_to": "bar", "offset_beats": -0.54,
      "bar_start": 1, "bar_end": 8, "beat_start": 0, "beat_end": 28,
      "lyrics": ["我把影子留在水面"],
      "lyric_lines": [ { "start": 4.2, "end": 9.1, "text": "我把影子留在水面" } ],
      "lyric_carry_over": false,
      "energy": "quiet",
      "art_movement": "rimpa",
      "animation_medium": "animation on twos with a held frame on every downbeat",
      "central_meaning": "不是字面复述：这一段真正在讲什么",
      "character_state": "…",
      "primary_metaphor": "…",
      "secondary_motif": "…",
      "background_lyric_elements": ["水面","影子","波纹"],
      "meaningful_objects": ["水面","波纹"],
      "lyric_action_binding": [
        { "lyric": "我把影子留在水面", "action": "slow arm sweep across the water",
          "beat": 8 }
      ],
      "choreography": "…",
      "environment_system": "环境作为剧作系统，不是背景",
      "style_prompt": "2D limited animation, hand-drawn, flat composition, …",
      "content_prompt": "0-7s … 7-14.2s …",
      "integrated_multimodal_description": "…",
      "overall_soundscape": "水声与衣料摩擦；不描述配乐",
      "camera": "见 shots",
      "transition_in": "paper wipe", "transition_out": "hard cut",
      "continuity_from_previous": "承接上一段结尾抬起的右臂",
      "hook_to_next": "右臂继续抬起，留给下一段",
      "shots": [
        { "index": 1, "start": 0.0, "end": 7.0,
          "beat_start": 0, "beat_end": 14,
          "camera": "Static Shot",
          "camera_amplitude": "", "camera_speed": "",
          "camera_target": "",
          "shot_size": "medium shot",
          "action": "she plants her weight and sweeps one arm across the water",
          "cut": "hard cut",
          "lyric": "我把影子留在水面" }
      ]
    }
  ],
  "quality_gates": { "character_same_all_the_way": true, "…": true }
}
```

### 注意

- `request_seconds` / `delivered_seconds` / `headroom_seconds` **由脚本算**，
  不要手改（改了就跟帧网格对不上）。
- `is_tail_pad` 为 true 时，渲染器会写入「音乐结束后没有声音：hold frame /
  visual decay / paper texture / final held cel，不要创造新音乐」。
- `tail_advice == "still_frame_in_edit"` 表示余下不足 2.5 秒，
  **建议干脆不交给视频模型**，直接在剪辑里放静帧。
