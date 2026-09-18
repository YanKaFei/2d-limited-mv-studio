# 降级阶梯与失败处理

> 原则：**任何单个工具缺失都不许让流程死掉。**
> 每一级降级都要被记录，并且明确写出**影响是什么**。
> 不要静默编造。

---

## 音频探测

| 级别 | 工具 | 说明 |
|---|---|---|
| T1 | `ffprobe` | 最准 |
| T2 | `afinfo`（macOS 自带） | Mac 上覆盖 mp3/m4a/wav/aac/flac |
| T3 | 纯 Python 解析器 | MP3 帧头 / WAV / FLAC STREAMINFO / MP4 moov / Ogg granule |

三级全失败 → 明确报「无法解析该音频」，**不猜**。

## 音频解码与切分

| 级别 | 工具 | 能做什么 |
|---|---|---|
| T1 | `ffmpeg` | 任意格式 → WAV → 按毫秒切 |
| T2 | `afconvert`（macOS 自带） | 同上 |
| T3 | 源本身是 WAV | 标准库 `wave` 直接切，最准 |
| T4 | 都没有 | **只产出切分清单**（`manifest.json` + `cut_sheet.md`），
并明确告诉用户在 DAW / 画布里自己切 |

T4 时的正确说法：

```
本机既没有 ffmpeg 也没有 afconvert，无法解码非 WAV 音频。
已产出精确到毫秒的切分清单：workspace/segments/manifest.json
请在 DAW / 画布里按下表切，切好后放进 input/music_segments/ 再重跑。
```

**绝不假装切成功。**

## 音乐分析

| 级别 | 依赖 | 产出 |
|---|---|---|
| T1 | `librosa` | BPM / 拍网格 / onset / RMS / 频谱质心 |
| T2 | `numpy` | RMS / onset / FFT 质心 |
| T3 | 标准库 `wave` + `audioop` | RMS / 过零率 / onset / 自相关测速 |

T3 的 BPM 是自相关估计，**可能差一个倍频**，用耳朵复核或参考歌词密度。
全失败 → 分析降级为「只有时长」，标 `degraded: true`，并写明
「节奏相关的剪辑/动作幅度判断需要人工补充」。

## 歌词识别

| 级别 | 来源 |
|---|---|
| 01 | 音频内嵌（ID3 USLT/SYLT、Vorbis LYRICS、MP4 ©lyr） |
| 02–05 | 同目录 `.lrc` / `.srt` / `.vtt` / `.txt` |
| 06 | ASR：`whisperx` → `faster-whisper` → `mlx-whisper` → `openai-whisper` → `whisper.cpp` |

- 有人声分离（Demucs）时优先 `song → vocals → whisper`；
  Demucs 不在就直接 ASR，**不能因此停止任务**。
- **ASR 结果一律标 `[ASR uncertain]` 并要求人工核对。**
  实测把「王子」转成过「滑走」。
- 全都没有 → 状态 `needs_manual_lyrics`，切 **Music-Semantic Mode**，
  并把「请把 .lrc/.srt/.vtt/.txt 放进 `input/lyrics/`」写进报告。
- `.txt` 无时间轴且没有 ASR 时，允许「按整曲时长均分」兜底，
  但必须标 `estimated: true` 并写进警告。

## 艺术风格库

art-aesthetic-vault 不可用 → 用 `references/art-medium-map.md` +
各路线自带的 `fallback_medium`。
**手法仍然正确，只是流派术语不如库中精确**——必须在报告里写明。

## 视频生成（MiniMax H3）

| 情况 | 处理 |
|---|---|
| 画布不支持音频复用 | 用 I2VA（参考图当首帧）或 T2VA，并说明人物一致性会下降 |
| 画布不认 Ref2VA 六段 | 用 `--route i2va` 出三核心段格式 |
| 中文平台 | 用 `--lang zh` 出中文自然语言（**不要与英文混粘**） |
| 末段余下 < 2.5 秒 | 不交给模型，直接出静帧在剪辑里做 |

---

## 失败信息模板

失败时必须写清楚：

```text
哪一步失败：analyze 音频解码
为什么：ffmpeg 与 afconvert 都不可用
回退方案：只保留时长与容器信息（degraded=true）
是否影响最终结果：音乐结构不可测 → 分段只能按 14.5 秒均分，
              节奏相关的剪辑/动作幅度判断需要人工补充
```

**不要静默编造。**

---

## 一次性安装（可选，全部提能力）

```bash
bash scripts/setup_env.sh            # 建 .venv 并装 numpy/librosa/soundfile
bash scripts/setup_env.sh --asr      # 追加 faster-whisper（自动歌词识别）
bash scripts/setup_env.sh --demucs   # 追加 demucs（人声分离）
brew install ffmpeg                  # 系统级：解码任意格式
```

装完后重跑 `python3 scripts/mvstudio.py doctor` 确认层级提升。

> **注意**：本技能的**核心管线零第三方依赖**（Python 3.9 标准库即可跑完整条流程）。
> 上面这些是**加分项**，不是必需项。
