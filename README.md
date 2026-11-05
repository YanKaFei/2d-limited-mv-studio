<div align="center">

# 2D Limited MV Studio

**Anime music-video workshop · 2D camera discipline · One image, one song, many worlds.**

*The limitation is the style.*
*The world mutates. The character does not.*

[![Built with DeepSeek Harness](https://img.shields.io/badge/built%20with-DeepSeek%20Harness-4B4BFF)](#built-with-deepseek-harness)
[![DSH Skill](https://img.shields.io/badge/DSH-agent%20skill-111111)](#install)
[![Target](https://img.shields.io/badge/target-MiniMax%20H3-FF4E8A)](#platforms)
[![Best on](https://img.shields.io/badge/best%20on-小云雀%20%C2%B7%20MiniMax%20Design-3DD6D0)](#platforms)
[![Tests](https://img.shields.io/badge/tests-173%20passing-2E7D32)](#tests)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-8A9BA8)](#requirements)
[![Camera](https://img.shields.io/badge/camera-2D%20limited%20%C2%B7%20no%203D-6B4FBB)](#the-camera-never-leaves-the-paper)

[中文](README.zh-CN.md) · **English** · [한국어](README.ko.md) · [日本語](README.ja.md) · [Français](README.fr.md)

</div>

---

> A music video is not a sequence of pretty frames.
> It is a single body that refuses to stop dancing while the world around it is repeatedly
> redrawn — printed, torn, engraved, dissolved, re-registered — and it is still unmistakably
> the same person at the last frame.

**One-click anime character music videos.** Give it a character image and a song; it hands back a
complete, machine-checked prompt package for **MiniMax H3** — the music cut at **14.5 s**, a cast of
art movements your character dances through, lyric objects written into the background, camera
language restricted to H3's official vocabulary, and every segment chained to the previous one by
its **actual last frame**.

## Why 14.5 seconds

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

## The six-section prompt

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

## The camera never leaves the paper

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

## Camera: six layers, one vocabulary

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

## Making the dance addictive

A dance becomes memorable not by being complex but by being **repeated until you can do it
yourself**. So the motion layer is not a longer word list — it is a **repetition design**.

| Layer | Field | What it decides |
|---|---|---|
| **Viral level** | `seg.motion.viral_level` | how hard this segment repeats — 0 restrained → 3 brainworm |
| **Repeat schedule** | `seg.motion.*` | move-unit length, cycle length, repeat count, where it mutates, which variation |
| **Hook** | `plan.motion_design.hook_id` | the film's **single** signature move, mandatory in every chorus |

Viral level is derived per segment from the music — and **it escalates toward the end**, because
addictiveness is something you build and then detonate. Even on a flat-energy track you get
verse-restrained → chorus-hooky → ending-brainworm.

```bash
python3 scripts/mvstudio.py motion                          # the menu + current design
python3 scripts/mvstudio.py motion --hook shoulder_pop_8
python3 scripts/mvstudio.py motion --viral 3                # whole film to brainworm
python3 scripts/mvstudio.py motion --segment C2 --viral 0   # one segment restrained
```

**Eight hook moves**, each designed for a different flavour of addictive: a head that nods while
the body stays perfectly still; eight shoulder-pops where *the count is the joke*; a stomp that
pauses longer each time; a squat pulse whose squash-and-stretch is the fastest route to
endearing awkwardness; a half-spin that stops short three times and then over-delivers.

**Five repeat variations** — growing accent, double time, half time, half-beat offset canon, and
*drop the last rep* (the hook you have been humming stops halfway). The hard rule: **a mutation
varries the same move; it never replaces it.** Replace the move and the memory breaks.

The schedule is **driven by the beat grid**, not by a guessed "repeat 4 times" — the same premise
every published music-conditioned dance-generation model shares. We take the principle and none
of the dependencies; the pipeline is still zero-dependency.

## The last gesture

A standing pose is the laziest way to end a film. The last gesture is what the audience keeps.
`2d-limited-mv-studio` offers **eight directable endings**, ranked against the music's own ending character:

| id | Ending | What happens |
|---|---|---|
| `jump_freeze` | **Jump & Freeze** | full jump, freeze at the apex, background pulled away to a single offset contour |
| `reach_and_crack` | **Reach & Crack** | she pushes a fingertip into the lens; the whole image cracks like glass, white showing through |
| `swipe_to_black` | **Swipe to Black** | arm sweeps the lens, screen cuts to black exactly on the downbeat, one afterimage lingers |
| `frame_drop_vanish` | **Frame-Drop Vanish** | arms go, then torso, motion continues, until only a contour line is left |
| `misregistration_exit` | **Misregistration Exit** | de-prints in layers: colour → line → nothing but registration marks |
| `spin_to_line` | **Spin to a Line** | mid-spin the body collapses into one vertical line, then is erased upward |
| `paper_tear_exit` | **Paper Tear Exit** | the frame tears down the middle; she dances out through the rip |
| `look_back_fade` | **Look Back, Fade** | the only full stop in the film — she looks back, the frame fades to an old photograph |

Every ending preserves identity. **What disappears is the drawing, never the person.**

## Last-frame chaining

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

## Every step waits for you

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
*"confirm, and wait."* The rhythm matches.)

## What is machine-checked

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

**Best on Xiaoyunque and MiniMax Design** — this skill is tuned for their cut, first/last-frame and
AI-edit features. **Other platforms work too**: anything that accepts an uploaded asset plus a
per-segment prompt can run the package; with `--platform generic` you get a canvas-agnostic
playbook instead of a platform-specific one.

| | Xiaoyunque | MiniMax Design |
|---|---|---|
| cut | smart storyboard / timeline cut | AI edit (natural language) — "cut the last 2 seconds" verified |
| first frame | first/last-frame mode | last frame as first-frame reference; or pose first in the 3D director stage |
| identity lock | character library / local re-edit | asset centre (character anchor) |
| rhythm | submit prompt by prompt | the Agent **asks back first**, then acts |

The division of labour: **the skill cuts the music, the platform cuts the picture.**
Full playbook, each platform's pitfalls, and the provenance and confidence of every claim:
`references/platform-playbook.md`.

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

<a id="tests"></a>

```bash
python3 -m unittest discover -s tests -t tests
# Ran 173 tests … OK
```

173 tests, zero dependencies, including an end-to-end run (synthetic assets → `all` → the draft
must refuse to render → fill → render → validate → pack) and a **privacy guard** that fails the
build if a project-specific name, a private prompt set or a hardcoded local path ever enters the
package.

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
