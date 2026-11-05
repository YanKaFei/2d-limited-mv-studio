# 2D Limited MV Studio

**キャラクター画像 1 枚 + 曲 1 曲 → 完全な 2D アニメ MV プロンプトパッケージ。**

DeepSeek Harness の Agent Skill。キャラクター画像と曲を **MiniMax H3** 用の機械検証済みプロンプトパッケージに変換します。14.5 秒のミュージックカット、キャラクターが踊り抜ける美術運動、背景に置かれる歌詞オブジェクト、紙から離れない 2D カメラ、前のラストフレームで継ぐセグメント。

[中文](README.md) · [English](README.en.md) · [한국어](README.ko.md) · **日本語** · [Français](README.fr.md)

<p align="center">
  <sub>DSH ecosystem: <a href="https://github.com/YanKaFei/Costume-Director-Vault-Starter">Costume Director</a> · <a href="https://github.com/YanKaFei/art-aesthetic-vault">Art Aesthetic Vault</a> · <a href="https://github.com/YanKaFei/ascii-h3-director">ASCII H3 Director</a> · <a href="https://github.com/YanKaFei/2d-limited-mv-studio">2D Limited MV Studio</a> · <a href="https://github.com/YanKaFei/virtual-heroine-atlas">Virtual Heroine Atlas</a> · <a href="https://github.com/YanKaFei/smartstaff-ai-deepseek-plugin">SmartStaff AI</a></sub>
</p>


## 提供するもの

- 14.5 秒のミュージックカット
- 2D リミテッドアニメーションのカメラ言語
- 美術運動のキャスト
- シーンに置かれる歌詞オブジェクト
- セグメント間の連続性
- 3D なし、Skill 自体は動画を生成しない

## インストール

```bash
./install-to-dsh.sh
```

または `SKILL.md` を互換環境で使用します。

## 使い方

キャラクター画像と曲を渡すと、MiniMax H3 用のプロンプトパッケージとショットプランを返します。**テキスト専用**で、最終動画は生成しません。

## ライセンス

[LICENSE](LICENSE) を参照。
