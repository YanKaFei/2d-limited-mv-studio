# 2D Limited MV Studio

**One character image + one song → a complete 2D anime music-video prompt package.**

A DeepSeek Harness agent skill that turns a character image and a song into a machine-checked prompt package for **MiniMax H3**: a 14.5-second music cut, art movements the character dances through, lyric objects in the background, a camera that never leaves the paper, and segments chained by the previous last frame.

[中文](README.md) · **English** · [한국어](README.ko.md) · [日本語](README.ja.md) · [Français](README.fr.md)

## What it gives you

- music cut at 14.5 s
- 2D limited-animation camera language
- a cast of art movements
- lyric objects written into the scene
- segment-to-segment continuity
- no 3D, no generated video by the skill itself

## Install

```bash
./install-to-dsh.sh
```

Or read `SKILL.md` and use it in a compatible agent environment.

## Use

Give the skill a character image and a song. It returns a prompt package and a shot plan for MiniMax H3. It is **text-only**; it does not generate the final video.

## Licence

See [LICENSE](LICENSE).
