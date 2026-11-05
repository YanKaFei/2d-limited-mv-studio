<div align="center">

# 2D Limited MV Studio

<p align="center" data-ecosystem-nav="1"><sub><a href="https://github.com/YanKaFei/Costume-Director-Vault-Starter">Costume</a> · <a href="https://github.com/YanKaFei/art-aesthetic-vault">Art</a> · <a href="https://github.com/YanKaFei/ascii-cinema-engine">ASCII Cinema</a> · <a href="https://github.com/YanKaFei/ascii-h3-director">ASCII H3</a> · <a href="https://github.com/YanKaFei/2d-limited-mv-studio">2D MV</a> · <a href="https://github.com/YanKaFei/virtual-heroine-atlas">Virtual Heroine</a></sub></p>

**二次元 MV 工房 · 2D カメラ制約 · 1 枚の画像、1 曲、いくつもの世界**

*制約こそがスタイル。*
*世界は変異し、キャラクターは変わらない。*

[![Built with DeepSeek Harness](https://img.shields.io/badge/built%20with-DeepSeek%20Harness-4B4BFF)](#built-with-deepseek-harness)
[![DSH Skill](https://img.shields.io/badge/DSH-agent%20skill-111111)](#install)
[![Target](https://img.shields.io/badge/target-MiniMax%20H3-FF4E8A)](#platforms)
[![Best on](https://img.shields.io/badge/best%20on-小云雀%20%C2%B7%20MiniMax%20Design-3DD6D0)](#platforms)
[![Tests](https://img.shields.io/badge/tests-173%20passing-2E7D32)](#tests)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-8A9BA8)](#requirements)
[![Camera](https://img.shields.io/badge/camera-2D%20limited%20%C2%B7%20no%203D-6B4FBB)](#the-camera-never-leaves-the-paper)

[中文](README.zh-CN.md) · [English](README.md) · [한국어](README.ko.md) · **日本語** · [Français](README.fr.md)

</div>

---

> MV は美しいカットの連続ではない。**止まろうとしないひとつの身体**であり、その周囲の世界が
> 何度も描き直される——印刷され、破られ、刻まれ、溶かされ、版がずれる——それでも最後の
> フレームで、彼女は紛れもなく同じ人物のままだ。

**ワンクリックで二次元キャラクターの MV をつくる。** キャラクター画像 1 枚と曲 1 曲を渡すと、
**MiniMax H3** 用の機械検証済みプロンプトパッケージ一式を返します。音楽は **14.5 秒**で切り、
キャラクターは複数の美術運動を横断し、歌詞に登場する物体は背景に置かれ、カメラ語彙は H3 の
公式語彙だけに制限され、各セグメントは前セグメントの**実際のラストフレーム**でつながります。

## なぜ 14.5 秒なのか

H3 の `duration` は **4〜15 の整数のみ**を受け付けます。しかもフレームグリッド（`17k+5`）の
ため、15 秒を要求しても実際に届くのは **362 フレーム ≒ 15.083 秒**です。

だから 2 つの数字は意図的に分けています：

| | 値 | 理由 |
|---|---|---|
| 音楽のカット | **14.5 秒**、最寄りの小節線にスナップ | 音楽的にきれいで、ユーザーの単位でもある |
| H3 `duration` | **15** | 実出尺が音楽を覆える最小の合法な整数 |
| 実出 | **15.083 秒** | 実際の H3 出力で確認済み |
| 使用可能 | 14.5 秒 | 余った **0.58 秒は継ぎ目の重なり**——最も速い動きの中に縫い目を隠す |

素朴に切り上げると**音楽が黙って切り詰められます**（6 秒を要求しても 5.875 秒しか届かない）。
`2d-limited-mv-studio` は「実出尺が音楽を覆える最小の整数」を選びます。

## 六セクションのプロンプト

どのプロンプトも同じ固定形状を、この順番で使います：

```text
人物与参考保持一致性：   reference roles + full character canon + drift prohibitions
风格提示词：           2D · limited animation · hand-drawn · flat composition + this segment's movement
内容提示词：           the continuity clause, then shot by shot
integrated_multimodal_description:  how reference, lyrics, music, dance and edit co-operate
overall_soundscape:    ambience and the physical sounds of the body
non_diegetic_music: N/A
```

`N/A` は省略ではありません。**曲はすでにあなたがアップロードしている**からです。ここには
モデルに作曲を求める文は一行もなく、公式が挙げる失敗モード——音楽を求めながら同じ
プロンプトで禁じる——も同時に避けています。

## カメラは紙から離れない

これは「たまたま絵に向いている実写カメラ」ではなく、**紙の束の上に立つカメラ**です。
そこが要点です。

カメラに許されることは意図的に限定されています：

- **3D カメラは使わない。** 空間を回り込まず、ドローン上昇も、フライスルーも、
  透視の移動もなし。奥行きは**レイヤー**からだけ生まれます——前景の紙、キャラクターの
  セル、背景イラスト、グラフィックの重ね——決して動く視点からではありません。
- **動きは 2D で書く。** ロストラムの移動は画面を**平行移動し、透視はまったく変わらない**。
  セルスライドは背景を微動だにさせず、人物だけが動く。マルチプレーン・パララックスは
  レイヤー間の速度差で奥行きをつくる——2D が持つ唯一正直な「被写界深度」です。
- **リミテッド・アニメーションが質感そのもの。** 止め、ツー・オン、ステップド・モーション、
  ポーズ・トゥ・ポーズ、スマッシュ画。滑らかさは目的ではありません。**絵が絵らしく動く**
  ことが目的です。
- **版ずれは言語であり、事故ではない。** 色レイヤーが数ピクセルずれることこそ、
  「アイデンティティが緩んだ」とこのスキルが言う方法です。

動きの語彙は H3 公式の **20 語**に抑えています。まさにこの理由から——語彙が増えると
カメラは紙から離れたくなるからです。代わりに豊かにするのは、カメラが**何を見ているか**：
アングル、構図、フォーカス、そしてそのカットが何を明かすか。

> **私たちが自分に課している基準**：すべての 3D カメラ移動を外しても、この映像は立つか？
> 立たないなら、それは最初から 2D の映像ではなかった。

## カメラ：六層、ひとつの語彙

H3 が認識するのは公式の **20 のカメラ運動語**だけで、それ以外は読みません。だから
「豊かなカメラワーク」は新しい語を発明しては作れません。`crane shot` や `whip pan` は
そもそも読まれないのです。豊かさは**レイヤー化**から生まれます：

```
ショットサイズ → アングル → 構図 → フォーカス → 公式運動語 → 主客の関係 → 何を明かすか
```

| 層 | 数 | 例 |
|---|---|---|
| ショットサイズ | 10 | 大ロング → 大アップ |
| **アングル** | **12** | ロー / ハイ / ダッチ / 俯瞰 / 虫瞰 / 肩越し / POV / **平面正対（2D ネイティブ）** |
| 構図 | 12 | 三分割、対称、余白、フレーム内フレーム、ポスター配置 |
| フォーカス | 4 | 深焦点、浅焦点、ソフト、**ラック** |
| **2D 専用の動き** | **10** | ロストラム、マルチプレーン・パララックス、セルスライド、**版ずれ**、紙ワイプ、アイリス、ハードクロップ、分割画面、露出フラッシュ、止めフレームのドリフト |
| 関係 | 7 | 追従 / 先導 / 同速 / 観察 / 明かす / 対立 / 周回 |

**欠けていた層は運動語ではなく、*アングル*でした。** パンとプッシュインだけのライブラリが、
カメラを薄く感じさせていたのです。

ハードルールは 3 つ、すべて機械検証：

1. **固定ショットには明示的なロック文を。** モデルは特にロングで勝手に流れます。すべての
   `Static Shot` に「シーンの間、カメラは完全に静止し、動くのは被写体だけ」を付けます。
2. **動くショットは必ず主客の関係を書く。** 書かないと 2 つの動きが別々の時計で走り、
   画面の揺れと、滑っているように見える人物になります。
3. **豊かなカメラワークはカメラ見本市ではない。** 1 セグメント内で動くのは**最大半分**まで。
   残りは固定し、エネルギーは **2D 専用の動き**が供給します——固定したカメラの上で、
   絵が生きている。

実写の用語は**思考のため**だけに使い、出力はすべて公式 20 語へ写像します
（`crane_up → Pedestal Up`、`whip_pan → Pan Right + large + fast`）。写像先が本当に
公式語かどうかはテストが強制します——モデルが読まない語を書かせないスキルです。
出典と完全な表：`references/camera-vocabulary.md`。

## ダンスを「魔性」にする

ダンスが記憶に残るのは複雑だからではなく、**自分で真似できるまで繰り返される**からです。
だから動作レイヤーの中心は、長い語彙リストではなく**反復の設計**です。

| 層 | フィールド | 決めること |
|---|---|---|
| **魔性度** | `seg.motion.viral_level` | このセグメントをどれだけ繰り返すか——0 抑制 → 3 洗脳 |
| **反復スケジュール** | `seg.motion.*` | 動作ユニット長、サイクル長、反復回数、どこで変異するか、どの変奏か |
| **フック** | `plan.motion_design.hook_id` | 映像**唯一**の看板動作。すべてのサビに必須 |

魔性度は音楽からセグメントごとに導かれ、**終盤に向かって上がります**。魔性は積み上げて
から爆発させるものだからです。平坦なエネルギー曲でも、A メロ抑制 → サビ魔性 → ラスト洗脳に
なります。

```bash
python3 scripts/mvstudio.py motion                          # メニュー + 現在の設計
python3 scripts/mvstudio.py motion --hook shoulder_pop_8
python3 scripts/mvstudio.py motion --viral 3                # 全編を洗脳へ
python3 scripts/mvstudio.py motion --segment C2 --viral 0   # 1 セグメントだけ抑制
```

**8 つのフック動作**、それぞれ別の「癖になる」味のために：身体は完全に静止して頭だけ
うなずく**ヘッドノッド・ロック**、数えること自体がギャグになる**肩ポップ 8 連**、
回を追うごとに長く止まる**ストンプ・ポーズ**、スクワッシュ＆ストレッチが最短で
「愛嬌」に届く**スクワット・パルス**、3 回途中で止めてから超過して応える**ハーフスピン**。

**5 つの反復変奏**——アクセント増加、倍速、半速、半拍ずらしのカノン、そして
**最後の 1 回を落とす**（ずっと口ずさんでいた動きが途中で終わる）。鉄則：
**変異は同じ動作の変奏であり、動作を置き換えない。** 置き換えた瞬間、記憶が切れます。

スケジュールは**拍グリッド**から駆動され、「4 回繰り返す」と当てずっぽうに書くのでは
ありません——公開されている音楽条件付きダンス生成モデルが共有する前提です。原理だけを取り、
依存は取りません。パイプラインはゼロ依存のままです。

## 最後のジェスチャー

立ったまま終わるのは最も怠惰な終わり方です。観客が持ち帰るのは最後の動作です。
`2d-limited-mv-studio` は **8 つの演出可能な終わり方**を、楽曲自身の終わり方の性格に
照らして提供します：

| id | 終わり方 | 何が起きるか |
|---|---|---|
| `jump_freeze` | **ジャンプ＆フリーズ** | 全力で跳び、頂点で停止。背景は抜かれ、オフセットした一本の輪郭だけが残る |
| `reach_and_crack` | **リーチ＆クラック** | 指先をレンズに押し込むと、画面全体がガラスのようにひび割れ、白い光が透ける |
| `swipe_to_black` | **スワイプ・トゥ・ブラック** | 腕がレンズを掃き、ダウンビートで正確に暗転。残像がひとつ残る |
| `frame_drop_vanish` | **フレームドロップ・ヴァニッシュ** | 腕が消え、胴が消え、動きは続き、最後に輪郭線だけが残る |
| `misregistration_exit` | **版ずれ退場** | レイヤーごとに刷りが引く：色 → 線 → トンボだけ |
| `spin_to_line` | **ラインへ回転** | 回転の途中で身体が一本の縦線に畳まれ、下から上へ消される |
| `paper_tear_exit` | **紙破り退場** | 画面が真ん中から破れ、彼女は裂け目から踊り出る |
| `look_back_fade` | **振り返り、フェード** | 映像で唯一の完全な停止——振り返り、画面が古い写真のように褪せる |

どの終わり方もアイデンティティを保ちます。**消えるのは「絵」であり、「人」ではない。**

## ラストフレーム・チェイニング

```
C1 ──その最後のフレーム──▶ C2 ──その最後のフレーム──▶ C3 ──▶ C4
```

前セグメントの**最終フレーム**が、次セグメントの**最初のフレーム**になります。
これはモデルが抗弁できない唯一の連続性の証拠です——同じ画像を見ているのですから。

そこから 2 つのハード制約が生まれ、うち 1 つは名指しする価値のある設計上の緊張です：

1. **画風の転換はセグメントの*内側*で起きる。** 連結された最初のフレームは、前セグメントの
   画風を引きずり込みます。「つながる」か「毎回画風が変わる」かを選ぶ代わりに、
   `2d-limited-mv-studio` は両方をやります：`0–1.5 秒`は前の画風とポーズを保ち、その後
   世界が**同じショットの中で**転換します。転換がカットではなく事件になります。
2. **連結中にポーズを変えない。** 第三者の現場報告（未検証——`references/platform-playbook.md`
   参照）では、連結する 2 フレーム間の垂直変位が**画面高の 12%**を超えると四肢の破綻が
   起きやすいとされます。私たちは保守的な側を取ります。

フレーム取得のラダー：`ffmpeg` → **macOS AVFoundation**（インストール不要。2560×1440 の
15.034 秒地点のフレーム抽出を実測済み）→ プラットフォームのタイムライン書き出し。
**最初のフレームを最後のフレームの代わりにすることは決してありません。**

## すべてのステップがあなたを待つ

```bash
python3 scripts/mvstudio.py confirm --status
python3 scripts/mvstudio.py confirm --step canon --note "人设没问题"
python3 scripts/mvstudio.py confirm --all
```

確認ポイントは `workspace/confirmations.json` に書き出され、監査可能・取消可能です：

```
gate → analyze → lyrics → canon → threeview → styles → segments
     → prompt-01 … prompt-N      すべてのプロンプト
     → chain-01  … chain-N       各セグメントの出力とラストフレーム
     → ending → render → validate → pack
```

未確認のままでは `render` と `pack` は**続行を拒否します（exit 5）**。明示的に
`--unattended` を渡さない限り。（MiniMax Design 自身の実機レビューは、ユーザーの動作を
「確認、そして待つ」の 2 つだけと書いています。リズムが一致しています。）

## 機械が検証するもの

「良さそう」ではなく、断言できること：

```
セグメント数 = ceil(尺 / 14.5)、各 ≤15 秒、隙間なく連続
カメラ語はすべて H3 公式 20 語の語彙内
背景の歌詞要素はすべてそのセグメントの歌詞から導出可能
映像全体で ≥3 種の美術運動、同じものが連続しない
六セクションが順序どおり揃い、Markdown ゼロ、1 プロンプト ≤7000 文字
音楽生成の指示がどこにもない
レンダリングに重要な Canon 6 フィールドが埋まっている
```

## クイックスタート

```bash
git clone <this repo> ~/Desktop/2d-limited-mv-studio && cd ~/Desktop/2d-limited-mv-studio

python3 scripts/mvstudio.py doctor          # 環境チェック
python3 scripts/mvstudio.py all             # 決定論的パイプライン
python3 scripts/mvstudio.py endings         # 最後のジェスチャーを選ぶ
python3 scripts/mvstudio.py confirm --all   # 各ステップを確認
python3 scripts/mvstudio.py render          # 六セクションのパッケージ
python3 scripts/mvstudio.py validate        # exit 0 でなければならない
python3 scripts/mvstudio.py pack --platform xiaoyunque
```

どのディレクトリからでも `--project <書き込み可能なディレクトリ>` で動きます。スキルの
フォルダ自体が読み取り専用（共有インストール、サンドボックス）なら、CLI が代わりに走らせる
べきコマンドを明示します。

## プラットフォーム

**最適なのは 小云雀 と MiniMax Design** —— 本スキルは両者のカット、先頭/末尾フレーム、
AI 編集機能に合わせて調整されています。**他のプラットフォームでも動きます**：アップロード
素材とセグメントごとのプロンプトを受け付ける画布なら何でも実行でき、`--platform generic`
では特定プラットフォームに依存しない手順書が得られます。

| | 小云雀 | MiniMax Design |
|---|---|---|
| カット | スマート絵コンテ / タイムライン切断 | AI 編集（自然言語）——「最後の 2 秒を切る」を実測で通過 |
| 先頭フレーム | 先頭/末尾フレームモード | 末尾フレームを先頭フレームの参照に、または 3D 監督台で先にポーズ |
| アイデンティティ固定 | キャラクターライブラリ / 部分再編集 | アセットセンター（人物アンカー） |
| リズム | 1 本ずつ提出 | Agent が**先に問い返して**から動く |

分業は：**音楽は本スキルが切り、画面はプラットフォームが切る。** 完全な手順書、各
プラットフォームの落とし穴、各主張の出典と信頼度は `references/platform-playbook.md`。

## インストール

<a id="install"></a>

```bash
bash install-to-dsh.sh ~/my-project    # <project>/.dsh/skills/2d-limited-mv-studio にシンボリックリンク
```

## DeepSeek Harness で構築

これは **DeepSeek Harness（DSH）のエージェントスキル**です。どの DSH エージェントでも
マウントでき、`SKILL.md` とゼロ依存の Python だけでできているので Claude Code / Codex /
Cursor でも同じように使えます。

**コミュニティタグ：** `deepseek-harness` `dsh` `agent-skill` `ai-video` `minimax-h3`
`music-video` `prompt-engineering` `2d-animation` `lyrics` `art-direction` `xiaoyunque`

## 動作要件

- **Python ≥ 3.7**、標準ライブラリのみ。パイプライン全体が**第三者依存ゼロ**で動きます
  （3.9.6 のシステム Python でテスト済み）。
- 以下はすべて任意で、それぞれ純粋に追加要素です：
  - `ffmpeg` **または** macOS `afconvert` —— 非 WAV 音声のカット
  - macOS **AVFoundation**（内蔵）—— 正確なラストフレームの抽出
  - `numpy` / `librosa` —— より鋭い BPM とスペクトル解析
  - 画風ライブラリ（147 の画派と階層化プロンプト）—— パスは設定可能。無い場合は内蔵の
    メディアパレットに降格し、その旨を明示します

## テスト

<a id="tests"></a>

```bash
python3 -m unittest discover -s tests -t tests
# Ran 173 tests … OK
```

173 のテスト、依存ゼロ。エンドツーエンド実行（合成素材 → `all` → ドラフトはレンダリングを
拒否 → 充填 → レンダリング → 検証 → パッケージ）と、プロジェクト固有の名前、非公開の
プロンプト群、ハードコードされたローカルパスがパッケージに入るとビルドを失敗させる
**プライバシーガード**を含みます。

## リポジトリ構成

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

## 設計ノート

自明ではなかったいくつかの決定と、その理由：

**キャラクター Canon は本文ではなく公式スロットに置く。**
ある手法はすべてのプロンプトで完全な人物設定を復唱せよと言い、別の手法は本文で外見を
説明してはならないと言う。テキストと参照画像が喧嘩してモデルが流れるからです。どちらも
正しく、場所が違うだけです。H3 の完全参照モードには `subject_definitions` と
`retention_analysis` という、まさにこのためのスロットがあります。Canon はそこへ、
本文はクリーンに。

**降格は大声で、決して静かに行わない。**
`ffmpeg` が無ければ、ミリ秒精度のカット表を渡し、自分で切るよう伝えます——黙って間違った
結果を返すことはありません。フレーム抽出器が無ければ、エラーとプラットフォーム自身の
書き出しへの道を示します。すべてのフォールバックはその影響とともに記録されます。

**色は装飾ではない。**
美術運動の選択は歌詞から索引され、背景のすべての要素はその下にある一行へ遡れなければ
なりません。ランダムな飾りは検証失敗であり、スタイルではありません。

## ライセンス

MIT —— [LICENSE](LICENSE) を参照。

<div align="center">

*ひとつの身体。いくつもの世界。最後のフレームでも同じ顔。*

</div>



## DSH ecosystem

- [Costume](https://github.com/YanKaFei/Costume-Director-Vault-Starter) — 衣装の視覚知識
- [Art](https://github.com/YanKaFei/art-aesthetic-vault) — 美術・映画スタイルのレイヤー
- [ASCII Cinema](https://github.com/YanKaFei/ascii-cinema-engine) — 文字グリッド・シネマ
- [ASCII H3](https://github.com/YanKaFei/ascii-h3-director) — ASCII / キネティック・タイポグラフィ演出
- [2D MV](https://github.com/YanKaFei/2d-limited-mv-studio) — 2D アニメ MV プロンプト
- [Virtual Heroine](https://github.com/YanKaFei/virtual-heroine-atlas) — バーチャルキャラクター研究
