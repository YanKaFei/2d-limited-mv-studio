把材料丢进这些目录，然后跑 `python3 scripts/mvstudio.py all`：

  input/music/       一首歌（mp3 / wav / flac / m4a / aac / ogg，≤3 分钟）
  input/character/   一张人物参考图（png / jpg / webp）
                     可以再放一张 threeview.png（三视图），会自动被识别
  input/lyrics/      可选：人工核对过的 .lrc / .srt / .vtt / .txt

多文件时的选择优先级见 SKILL.md Step 1。
原始文件永远只读，绝不修改、移动、改名、删除。
