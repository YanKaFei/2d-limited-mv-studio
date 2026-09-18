# Contributing

## 语言 / Language

Issues and PRs are welcome in **中文 or English** — either is fine.

## 这个仓库的两条硬规矩 / Two house rules

**1. 零第三方依赖。** `scripts/` 下的东西必须只用 Python 标准库跑通整条管线
（Python ≥ 3.7）。`ffmpeg` / `numpy` / `librosa` 只能作为**可选**增强，
而且必须有纯标准库的降级路径。

**2. 宁可不生成，也不生成编造的内容。** 缺字段就 `exit 2` 拒绝渲染，
而不是替用户瞎编歌词、舞蹈或语义。降级要**说出来**（记录影响），不许静默。

## 加新东西时

- **行为改动先写失败测试。** 跑 `python3 -m unittest discover -s tests -t tests`，
  先看它红，再改，再看它绿。
- **不要往仓库里带具体项目的内容。** 人物名、歌名、私人的提示词定稿、
  本机绝对路径都不许进来 —— `tests/test_prism.py::TestNoPrivateContent`
  会拦。定稿请写在 `workspace/`（已在 `.gitignore` 里）。
- **提示词里的文字零 Markdown。** 粘贴区是要交给模型的，加粗会被当成画面要求。
- **画风术语先查库**，不要凭记忆编造流派名。
