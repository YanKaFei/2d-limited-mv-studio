<div align="center">

# 2D Limited MV Studio

**2D MV 공방 · 2D 카메라 제약 · 이미지 하나, 노래 하나, 여러 개의 세계**

*제약이 곧 스타일이다.*
*세계는 변이하고, 캐릭터는 변하지 않는다.*

[![Built with DeepSeek Harness](https://img.shields.io/badge/built%20with-DeepSeek%20Harness-4B4BFF)](#built-with-deepseek-harness)
[![DSH Skill](https://img.shields.io/badge/DSH-agent%20skill-111111)](#install)
[![Target](https://img.shields.io/badge/target-MiniMax%20H3-FF4E8A)](#platforms)
[![Best on](https://img.shields.io/badge/best%20on-小云雀%20%C2%B7%20MiniMax%20Design-3DD6D0)](#platforms)
[![Tests](https://img.shields.io/badge/tests-173%20passing-2E7D32)](#tests)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-8A9BA8)](#requirements)
[![Camera](https://img.shields.io/badge/camera-2D%20limited%20%C2%B7%20no%203D-6B4FBB)](#the-camera-never-leaves-the-paper)

[中文](README.zh-CN.md) · [English](README.md) · **한국어** · [日本語](README.ja.md) · [Français](README.fr.md)

</div>

---

> MV는 예쁜 컷의 연속이 아니다. **멈추기를 거부하는 하나의 몸**이고, 그 주변의 세계는
> 반복해서 다시 그려진다——인쇄되고, 찢기고, 새겨지고, 녹고, 판이 어긋난다——그래도 마지막
> 프레임에서 그녀는 분명히 같은 사람이다.

**원클릭 2D 캐릭터 MV.** 캐릭터 이미지 하나와 노래 하나를 주면, **MiniMax H3**용으로 기계
검증된 프롬프트 패키지를 돌려줍니다. 음악은 **14.5초**로 자르고, 캐릭터는 여러 미술 사조를
가로지르며, 가사 속 사물은 배경에 놓이고, 카메라 어휘는 H3 공식 어휘로만 제한되며, 각
세그먼트는 이전 세그먼트의 **실제 마지막 프레임**으로 이어집니다.

## 왜 14.5초인가

H3의 `duration`은 **4–15 사이의 정수만** 받습니다. 게다가 프레임 그리드(`17k+5`) 때문에
15초를 요청해도 실제로는 **362프레임 ≒ 15.083초**가 전달됩니다.

그래서 두 숫자를 의도적으로 분리합니다:

| | 값 | 이유 |
|---|---|---|
| 음악 컷 | **14.5초**, 가장 가까운 마디선에 스냅 | 음악적으로 깔끔하고, 사용자의 단위이기도 하다 |
| H3 `duration` | **15** | 실측 길이가 음악을 덮는 가장 작은 합법 정수 |
| 실측 | **15.083초** | 실제 H3 출력으로 확인 |
| 사용 가능 | 14.5초 | 남는 **0.58초는 이음새 겹침**——가장 빠른 동작 안에 이음매를 숨긴다 |

단순히 올림하면 **음악이 조용히 잘립니다**(6초를 요청해도 5.875초만 전달).
`2d-limited-mv-studio`는 "실측 길이가 음악을 덮는 가장 작은 정수"를 고릅니다.

## 여섯 섹션 프롬프트

모든 프롬프트는 하나의 고정된 형태를 이 순서로 사용합니다:

```text
人物与参考保持一致性：   reference roles + full character canon + drift prohibitions
风格提示词：           2D · limited animation · hand-drawn · flat composition + this segment's movement
内容提示词：           the continuity clause, then shot by shot
integrated_multimodal_description:  how reference, lyrics, music, dance and edit co-operate
overall_soundscape:    ambience and the physical sounds of the body
non_diegetic_music: N/A
```

`N/A`는 생략이 아닙니다. **노래는 이미 당신이 업로드했기** 때문입니다. 여기에는 모델에게
작곡을 요구하는 문장이 한 줄도 없고, 공식이 지적한 실패 모드——음악을 요구하면서 같은
프롬프트에서 금지하는 것——도 동시에 피합니다.

## 카메라는 종이를 떠나지 않는다

이것은 "우연히 그림을 향한 실사 카메라"가 아니라, **종이 더미 위에 서 있는 카메라**입니다.
그게 핵심입니다.

카메라가 할 수 있는 일은 의도적으로 제한됩니다:

- **3D 카메라를 쓰지 않는다.** 공간을 돌지 않고, 드론 상승도, 플라이스루도, 투시 이동도
  없다. 깊이는 **레이어**에서만 나온다——전경 종이, 캐릭터 셀, 배경 일러스트, 그래픽
  오버레이——움직이는 시점에서는 절대 나오지 않는다.
- **움직임은 2D로 쓴다.** 로스트럼 이동은 화면을 **평행 이동하며 투시는 전혀 변하지
  않는다**. 셀 슬라이드는 배경을 미동도 없이 두고 인물만 움직인다. 멀티플레인 패럴랙스는
  레이어 간 속도 차이로 깊이를 만든다——2D가 가진 유일하게 정직한 "심도"다.
- **리미티드 애니메이션이 질감 그 자체.** 홀드, 온 투스, 스텝드 모션, 포즈 투 포즈,
  스미어 드로잉. 부드러움이 목표가 아니다. **그림이 그림답게 움직이는 것**이 목표다.
- **판 어긋남은 언어이지 사고가 아니다.** 색 레이어가 몇 픽셀 어긋나는 것, 그것이 이
  스킬이 "정체성이 풀렸다"고 말하는 방식이다.

움직임 어휘를 H3 공식 **20개**로 묶어 둔 이유가 바로 이것입니다——어휘가 커지면 카메라가
종이를 떠나고 싶어 하니까. 대신 풍부하게 만드는 것은 카메라가 **무엇을 보고 있는가**다.
앵글, 구도, 포커스, 그리고 이 컷이 무엇을 드러내는가.

> **우리가 스스로에게 거는 기준**: 모든 3D 카메라 이동을 걷어내도 이 영상은 서는가?
> 서지 않는다면, 그것은 애초에 2D 영상이 아니었다.

## 카메라: 여섯 겹, 하나의 어휘

H3가 인식하는 것은 공식 **20개의 카메라 운동 단어**뿐이며, 그 외에는 읽지 않습니다. 그래서
"풍부한 카메라워크"는 새 단어를 발명해서 만들 수 없습니다. `crane shot`과 `whip pan`은
애초에 읽히지 않습니다. 풍부함은 **레이어링**에서 나옵니다:

```
샷 사이즈 → 앵글 → 구도 → 포커스 → 공식 운동 단어 → 주체와 카메라의 관계 → 무엇을 드러내는가
```

| 층 | 수 | 예 |
|---|---|---|
| 샷 사이즈 | 10 | 익스트림 와이드 → 익스트림 클로즈업 |
| **앵글** | **12** | 로우 / 하이 / 더치 / 오버헤드 / 웜즈아이 / 오버 더 숄더 / POV / **평면 정면(2D 네이티브)** |
| 구도 | 12 | 삼분할, 대칭, 여백, 프레임 속 프레임, 포스터 배치 |
| 포커스 | 4 | 딥, 셜로, 소프트, **랙** |
| **2D 전용 무브** | **10** | 로스트럼 카메라, 멀티플레인 패럴랙스, 셀 슬라이드, **레지스트레이션 시프트**, 페이퍼 와이프, 아이리스, 하드 크롭, 분할 화면, 노출 플래시, 홀드 프레임 드리프트 |
| 관계 | 7 | 따라감 / 이끎 / 같은 속도 / 관찰 / 드러냄 / 대립 / 선회 |

**빠져 있던 층은 운동 단어가 아니라 *앵글*이었습니다.** 팬과 푸시인만 있는 라이브러리가
카메라를 얇게 느껴지게 했던 것입니다.

하드 룰 세 개, 전부 기계 검증:

1. **고정 샷에는 명시적 잠금 문장을.** 모델은 특히 와이드에서 스스로 흐릅니다. 모든
   `Static Shot`에 "장면 내내 카메라는 완전히 정지해 있고, 움직임은 피사체에서만 발생한다"를
   붙입니다.
2. **움직이는 샷은 주체와의 관계를 반드시 쓴다.** 쓰지 않으면 두 움직임이 서로 다른 시계로
   돌아, 화면 떨림과 미끄러지는 듯한 인물로 나타납니다.
3. **풍부한 카메라워크는 카메라 쇼릴이 아니다.** 한 세그먼트에서 움직이는 샷은 **최대
   절반**. 나머지는 고정하고, 에너지는 **2D 전용 무브**가 공급합니다——고정된 카메라 위에서
   살아 있는 그림.

실사 용어는 **사고를 위해서만** 쓰고, 출력은 전부 공식 20개로 매핑합니다
(`crane_up → Pedestal Up`, `whip_pan → Pan Right + large + fast`). 매핑 대상이 실제 공식
용어인지 테스트가 강제합니다——모델이 읽지 않는 단어를 쓰도록 가르치지 않는 스킬입니다.
출처와 전체 표: `references/camera-vocabulary.md`.

## 댄스를 "중독성 있게" 만들기

댄스가 기억되는 것은 복잡해서가 아니라, **따라 할 수 있을 때까지 반복**되기 때문입니다.
그래서 모션 레이어의 핵심은 더 긴 단어 목록이 아니라 **반복의 설계**입니다.

| 층 | 필드 | 결정하는 것 |
|---|---|---|
| **중독도** | `seg.motion.viral_level` | 이 세그먼트를 얼마나 세게 반복하는가——0 절제 → 3 뇌세척 |
| **반복 스케줄** | `seg.motion.*` | 동작 단위 길이, 사이클 길이, 반복 횟수, 어디서 변이하는지, 어떤 변주인지 |
| **훅** | `plan.motion_design.hook_id` | 영상 **단 하나**의 시그니처 동작, 모든 후렴에 필수 |

중독도는 음악에서 세그먼트마다 도출되며, **후반으로 갈수록 올라갑니다**. 중독성은 쌓아
올린 뒤 터뜨리는 것이니까요. 에너지가 평탄한 곡에서도 절제된 벌스 → 훅 있는 후렴 →
뇌세척 엔딩이 나옵니다.

```bash
python3 scripts/mvstudio.py motion                          # 메뉴 + 현재 설계
python3 scripts/mvstudio.py motion --hook shoulder_pop_8
python3 scripts/mvstudio.py motion --viral 3                # 전편을 뇌세척으로
python3 scripts/mvstudio.py motion --segment C2 --viral 0   # 한 세그먼트만 절제
```

**여덟 가지 훅 동작**, 각기 다른 "멈출 수 없음"을 위해: 몸은 완전히 멈추고 머리만 끄덕이는
**헤드 노드 락**, 숫자 세기 자체가 웃음 포인트인 **숄더 팝 8연타**, 매번 더 길게 멈추는
**스톰프 포즈**, 스쿼시 앤 스트레치가 가장 빠르게 "애교"에 닿는 **스쿼트 펄스**, 세 번
모자라게 돌다가 초과해 응답하는 **하프 스핀**.

**다섯 가지 반복 변주**——악센트 증가, 배속, 반속, 반박 오프셋 카논, 그리고 **마지막 1회
생략**(계속 흥얼거리던 동작이 중간에 끊깁니다). 철칙: **변이는 같은 동작의 변주이며, 동작을
대체하지 않는다.** 동작을 바꾸면 기억이 끊깁니다.

스케줄은 **비트 그리드**에서 구동되며, "4번 반복"을 찍어 쓰는 것이 아닙니다——공개된 모든
음악 조건부 댄스 생성 모델이 공유하는 전제입니다. 원리만 가져오고 의존성은 가져오지
않습니다. 파이프라인은 여전히 제로 의존성입니다.

## 마지막 제스처

서 있는 자세로 끝내는 것은 가장 게으른 마무리입니다. 관객이 가져가는 것은 마지막 동작입니다.
`2d-limited-mv-studio`는 **여덟 가지 연출 가능한 엔딩**을 곡 자체의 마무리 성격에 비추어
제공합니다:

| id | 엔딩 | 무슨 일이 일어나는가 |
|---|---|---|
| `jump_freeze` | **점프 & 프리즈** | 전력으로 뛰어 올라 정점에서 정지, 배경은 빠지고 어긋난 윤곽선 하나만 남는다 |
| `reach_and_crack` | **리치 & 크랙** | 손끝으로 렌즈를 밀면 화면 전체가 유리처럼 갈라지고 흰 빛이 새어 나온다 |
| `swipe_to_black` | **스와이프 투 블랙** | 팔이 렌즈를 쓸고, 다운비트에서 정확히 암전, 잔상 하나가 남는다 |
| `frame_drop_vanish` | **프레임 드롭 배니시** | 팔이 사라지고, 몸통이 사라지고, 움직임은 계속되다가 마지막에 윤곽선만 남는다 |
| `misregistration_exit` | **판 어긋남 퇴장** | 레이어별로 인쇄가 빠진다: 색 → 선 → 톤보만 |
| `spin_to_line` | **선으로 회전** | 회전 도중 몸이 하나의 수직선으로 접히고, 아래에서 위로 지워진다 |
| `paper_tear_exit` | **종이 찢기 퇴장** | 화면이 가운데에서 찢어지고, 그녀는 그 틈으로 춤추며 나간다 |
| `look_back_fade` | **뒤돌아보고 페이드** | 영상에서 유일한 완전한 정지——뒤를 돌아보고, 화면이 낡은 사진처럼 바랜다 |

모든 엔딩은 정체성을 유지합니다. **사라지는 것은 "그림"이지 "사람"이 아닙니다.**

## 마지막 프레임 체이닝

```
C1 ──그 마지막 프레임──▶ C2 ──그 마지막 프레임──▶ C3 ──▶ C4
```

이전 세그먼트의 **마지막 프레임**이 다음 세그먼트의 **첫 프레임**이 됩니다.
이것이 모델이 반박할 수 없는 유일한 연속성 증거입니다——같은 이미지를 보고 있으니까요.

그로부터 두 가지 하드 제약이 생기고, 그중 하나는 이름 붙일 가치가 있는 설계상의 긴장입니다:

1. **화풍 전환은 세그먼트 *안에서* 일어난다.** 연결된 첫 프레임은 이전 세그먼트의 화풍을
   끌고 옵니다. "이어진다"와 "매번 화풍이 바뀐다" 중 하나를 고르는 대신,
   `2d-limited-mv-studio`는 둘 다 합니다: `0–1.5초`는 이전 화풍과 포즈를 유지하고, 그 뒤
   세계가 **같은 샷 안에서** 전환됩니다. 전환이 컷이 아니라 사건이 됩니다.
2. **연결 중에는 포즈를 바꾸지 않는다.** 제3자 현장 보고(미검증——`references/platform-playbook.md`
   참조)에 따르면 연결되는 두 프레임 사이 수직 변위가 **화면 높이의 12%**를 넘으면 사지
   찢어짐이 나기 쉽습니다. 우리는 보수적인 쪽을 택합니다.

프레임 추출 사다리: `ffmpeg` → **macOS AVFoundation**(설치 불필요, 2560×1440의 15.034초
지점 프레임 추출 실측) → 플랫폼 타임라인 내보내기.
**첫 프레임을 마지막 프레임인 척하지 않습니다.**

## 모든 단계가 당신을 기다린다

```bash
python3 scripts/mvstudio.py confirm --status
python3 scripts/mvstudio.py confirm --step canon --note "人设没问题"
python3 scripts/mvstudio.py confirm --all
```

확인 지점은 `workspace/confirmations.json`에 기록되어 감사 가능하고 취소 가능합니다:

```
gate → analyze → lyrics → canon → threeview → styles → segments
     → prompt-01 … prompt-N      모든 프롬프트
     → chain-01  … chain-N       각 세그먼트의 출력과 마지막 프레임
     → ending → render → validate → pack
```

확인되지 않은 동안 `render`와 `pack`은 **계속을 거부합니다(exit 5)**. 명시적으로
`--unattended`를 넘기지 않는 한.(MiniMax Design 자체의 실사용 리뷰는 사용자의 행동을
"확인, 그리고 기다림" 두 가지로만 서술합니다. 리듬이 맞습니다.)

## 기계가 검증하는 것

"좋아 보인다"가 아니라, 단언할 수 있는 것:

```
세그먼트 수 = ceil(길이 / 14.5), 각 ≤15초, 빈틈없이 연속
모든 카메라 단어가 H3 공식 20단어 어휘 안에 있음
모든 배경 가사 요소가 해당 세그먼트 가사에서 도출 가능
영상 전체에서 ≥3가지 미술 사조, 같은 것이 연속하지 않음
여섯 섹션이 순서대로 존재, Markdown 0, 프롬프트당 ≤7000자
음악 생성 지시가 어디에도 없음
렌더링에 중요한 Canon 6개 필드가 채워져 있음
```

## 빠른 시작

```bash
git clone <this repo> ~/Desktop/2d-limited-mv-studio && cd ~/Desktop/2d-limited-mv-studio

python3 scripts/mvstudio.py doctor          # 환경 점검
python3 scripts/mvstudio.py all             # 결정론적 파이프라인
python3 scripts/mvstudio.py endings         # 마지막 제스처 고르기
python3 scripts/mvstudio.py confirm --all   # 단계별 확인
python3 scripts/mvstudio.py render          # 여섯 섹션 패키지
python3 scripts/mvstudio.py validate        # 반드시 exit 0
python3 scripts/mvstudio.py pack --platform xiaoyunque
```

어느 디렉터리에서든 `--project <쓰기 가능한 디렉터리>`로 실행됩니다. 스킬 폴더 자체가
읽기 전용이면(공유 설치, 샌드박스 세션), CLI가 대신 실행할 명령을 정확히 알려줍니다.

## 플랫폼

**최적은 小云雀과 MiniMax Design** —— 이 스킬은 두 플랫폼의 컷, 처음/마지막 프레임, AI
편집 기능에 맞춰 조정되었습니다. **다른 플랫폼에서도 동작합니다**: 업로드 소재와 세그먼트별
프롬프트를 받아들이는 캔버스라면 무엇이든 실행되며, `--platform generic`은 특정 플랫폼에
종속되지 않는 범용 운영서를 제공합니다.

| | 小云雀 | MiniMax Design |
|---|---|---|
| 컷 | 스마트 스토리보드 / 타임라인 분할 | AI 편집(자연어)——"마지막 2초 자르기" 실측 통과 |
| 첫 프레임 | 처음/마지막 프레임 모드 | 마지막 프레임을 첫 프레임 참조로, 또는 3D 감독대에서 먼저 포즈 |
| 정체성 고정 | 캐릭터 라이브러리 / 부분 재편집 | 에셋 센터(인물 앵커) |
| 리듬 | 한 건씩 제출 | Agent가 **먼저 되물어 확인**한 뒤 행동 |

분업은: **음악은 이 스킬이 자르고, 화면은 플랫폼이 자릅니다.** 전체 실무 매뉴얼, 각
플랫폼의 함정, 모든 주장의 출처와 신뢰도는 `references/platform-playbook.md`.

## 설치

<a id="install"></a>

```bash
bash install-to-dsh.sh ~/my-project    # <project>/.dsh/skills/2d-limited-mv-studio로 심볼릭 링크
```

## DeepSeek Harness로 구축

이것은 **DeepSeek Harness(DSH) 에이전트 스킬**입니다. 어떤 DSH 에이전트든 마운트할 수
있고, `SKILL.md`와 제로 의존성 Python일 뿐이라 Claude Code / Codex / Cursor에서도 똑같이
쓸 수 있습니다.

**커뮤니티 태그:** `deepseek-harness` `dsh` `agent-skill` `ai-video` `minimax-h3`
`music-video` `prompt-engineering` `2d-animation` `lyrics` `art-direction` `xiaoyunque`

## 요구 사항

- **Python ≥ 3.7**, 표준 라이브러리만. 파이프라인 전체가 **서드파티 의존성 없이** 실행됩니다
  (3.9.6 시스템 Python에서 테스트).
- 아래는 모두 선택 사항이며, 각각 순수하게 추가 요소입니다:
  - `ffmpeg` **또는** macOS `afconvert` —— 비 WAV 오디오 자르기
  - macOS **AVFoundation**(내장) —— 정확한 마지막 프레임 추출
  - `numpy` / `librosa` —— 더 예리한 BPM과 스펙트럼 분석
  - 화풍 라이브러리(147개 사조, 계층화 프롬프트) —— 경로 설정 가능. 없으면 내장 미디어
    팔레트로 강등하고 그 사실을 명시합니다

## 테스트

<a id="tests"></a>

```bash
python3 -m unittest discover -s tests -t tests
# Ran 173 tests … OK
```

173개 테스트, 의존성 0. 엔드투엔드 실행(합성 소재 → `all` → 초안이 렌더링을 거부해야 함 →
채우기 → 렌더링 → 검증 → 패키징)과, 프로젝트 전용 이름·비공개 프롬프트 세트·하드코딩된
로컬 경로가 패키지에 들어오면 빌드를 실패시키는 **프라이버시 가드**를 포함합니다.

## 저장소 구조

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

## 설계 노트

자명하지 않았던 몇 가지 결정과 그 이유:

**캐릭터 Canon은 본문이 아니라 공식 슬롯에 둔다.**
한 방법론은 모든 프롬프트에서 완전한 캐릭터 설정을 다시 말하라고 하고, 다른 방법론은
본문에서 외모를 절대 묘사하지 말라고 합니다. 텍스트와 참조 이미지가 싸우면 모델이 흐르기
때문입니다. 둘 다 옳고, 위치만 다릅니다. H3의 완전 참조 모드에는 `subject_definitions`와
`retention_analysis`——정확히 이 일을 위해 마련된 슬롯이 있습니다. Canon은 그리로,
본문은 깨끗하게.

**강등은 크게, 절대 조용히 하지 않는다.**
`ffmpeg`가 없으면? 밀리초 정확도의 컷 표를 받고 직접 자르라는 안내를 받습니다——조용히
틀린 결과를 받지 않습니다. 프레임 추출기가 없으면? 오류와 함께 플랫폼 자체 내보내기
경로를 안내합니다. 모든 폴백은 그 영향과 함께 기록됩니다.

**색은 장식이 아니다.**
미술 사조 선택은 가사에서 색인되고, 배경의 모든 요소는 그 아래 놓인 한 줄로 거슬러 올라갈
수 있어야 합니다. 무작위 장식은 검증 실패이지 스타일이 아닙니다.

## 라이선스

MIT —— [LICENSE](LICENSE) 참조.

<div align="center">

*하나의 몸. 여러 개의 세계. 마지막 프레임에서도 같은 얼굴.*

</div>

<p align="center" data-ecosystem-nav="1"><sub><a href="https://github.com/YanKaFei/Costume-Director-Vault-Starter">Costume</a> · <a href="https://github.com/YanKaFei/art-aesthetic-vault">Art</a> · <a href="https://github.com/YanKaFei/ascii-cinema-engine">ASCII Cinema</a> · <a href="https://github.com/YanKaFei/ascii-h3-director">ASCII H3</a> · <a href="https://github.com/YanKaFei/2d-limited-mv-studio">2D MV</a> · <a href="https://github.com/YanKaFei/virtual-heroine-atlas">Virtual Heroine</a></sub></p>


## DSH ecosystem

- [Costume](https://github.com/YanKaFei/Costume-Director-Vault-Starter) — 의상 시각 지식
- [Art](https://github.com/YanKaFei/art-aesthetic-vault) — 예술·영화 스타일 레이어
- [ASCII Cinema](https://github.com/YanKaFei/ascii-cinema-engine) — 문자 그리드 시네마
- [ASCII H3](https://github.com/YanKaFei/ascii-h3-director) — ASCII / 키네틱 타이포그래피 연출
- [2D MV](https://github.com/YanKaFei/2d-limited-mv-studio) — 2D 애니메이션 MV 프롬프트
- [Virtual Heroine](https://github.com/YanKaFei/virtual-heroine-atlas) — 버추얼 캐릭터 연구
