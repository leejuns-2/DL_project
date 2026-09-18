---
title: Energy Report-to-Market Signal Analyzer
emoji: ⚡
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
app_port: 7860
---

# Energy Report-to-Market Signal Analyzer

에너지·기후 관련 PDF에서 근거 문단을 검색하고, 문서의 주요 테마를 분류한 뒤
Gemini를 이용해 근거 기반 요약을 생성하는 분석 파이프라인입니다.

단순한 문서 요약보다 **어떤 근거를 바탕으로 어떤 테마가 탐지되었는지 확인할 수 있는 구조**를 만드는 것을 목표로 했습니다.

> This project is a course project developed with generative AI coding assistance.  
> I focused on experiment execution, result analysis, debugging, evaluation refinement, and iterative improvement.

---

## Project Context

- Course: Deep Learning
- Type: Individual project
- Domain: Energy / Climate documents
- Main tasks:
  - Evidence retrieval
  - Theme classification
  - Evidence-grounded summarization
  - Development-set evaluation

---

## Key Result

공개 PDF 50개로 구성한 **development catalog**에서
zero-shot embedding similarity와 supervised linear probe를 비교했습니다.

| Method | Dominant-theme top-1 alignment |
|---|---:|
| Zero-shot embedding similarity | 17/50 (34%) |
| Supervised linear probe | 36/50 (72%) |

Supervised linear probe가 development catalog 기준으로
dominant-theme top-1 alignment를 **34%에서 72%로 개선**했습니다.

다만 이 결과는 독립적인 held-out benchmark가 아니라
개발 과정에서 사용한 소규모 development set의 결과입니다.

---

## My Contribution

이 프로젝트에서 중점적으로 수행한 작업은 다음과 같습니다.

- 전체 report analysis pipeline의 구성 및 실행
- retrieval 및 theme classification 결과 비교
- zero-shot 방식과 supervised linear probe 실험
- 실험 결과와 failure case 분석
- OOD 및 mixed-theme 사례 점검
- Gemini 기반 evidence-grounded summary 연결
- 오류 수정과 evaluation 방식 개선
- 결과의 해석 범위와 한계 정리

구현 과정에서는 **generative AI coding tools를 보조적으로 활용**했으며,
실험 실행, 결과 확인, 오류 수정, 평가 방식과 실험 조건의 조정 과정을 직접 수행했습니다.

---

## Pipeline

```text
PDF
  ↓
Text Extraction
  ↓
Evidence Retrieval
  ↓
MiniLM Embedding
  ↓
Theme Classification
  ↓
Mixed-theme / OOD Checks
  ↓
Evidence-grounded Gemini Summary
  ↓
News & Historical Market Context
```

## Model

| Component | Role |
|---|---|
| `sentence-transformers/all-MiniLM-L6-v2` | 보고서 문단과 라벨 예시를 384차원 임베딩으로 변환 |
| Logistic Regression heads | 고정된 임베딩에서 renewable, fossil pressure, grid infrastructure, climate risk를 독립적으로 점수화 |
| Gemini | 검색된 근거 문단을 설명하고 요약. 분류 점수 계산에는 사용하지 않음 |

MiniLM 파라미터는 fine-tuning하지 않습니다. 학습되는 부분은 사람이 작성한 소수 예시를 사용한 작은 downstream 분류 헤드입니다. 각 테마는 상호 배타적이지 않기 때문에 단일 softmax 대신 독립적인 logistic head를 사용합니다.

`confidence`는 보정된 확률이 아니라 테마 점수와 상위 점수 간 차이에 기반한 값입니다. `asset_hint`도 매수·매도 신호가 아니라 관련 시장 범주를 표시하는 태그입니다.

## Validation

현재 저장된 검증 결과는 공개 PDF 50개로 만든 소규모 개발 카탈로그에서 생성했습니다.

| Method | Dominant-theme top-1 alignment |
|---|---:|
| Zero-shot embedding similarity | 17/50 (34%) |
| Supervised linear probe | 36/50 (72%) |

`36/50`은 문서마다 사람이 정한 하나의 dominant theme과 모델의 top-1 결과가 일치한 횟수입니다. 전체 multi-label 정확도가 아닙니다. 상세 결과와 실패 사례는 [`outputs/tables/model_validation_brief.md`](outputs/tables/model_validation_brief.md)에 있습니다.

> On a 50-document development catalog, dominant-theme top-1 agreement improved from 34% for the zero-shot baseline to 72% for the supervised linear probe. This is a development-set result, not an independent held-out benchmark.

카탈로그 내부의 `development_main`과 `development_diagnostic` 표시는 재현 가능한 진단용 부분집합일 뿐입니다. 두 부분집합과 전체 카탈로그가 개발 과정에서 활용되었으므로 어느 쪽도 독립 test set으로 해석하지 않습니다.

평가 범위는 component별로 분리합니다.

| Component | Current evidence | What it does not establish |
|---|---|---|
| Evidence retrieval | 검색된 문단과 score를 저장해 사례별 검토 가능 | 사람이 판정한 retrieval precision/recall benchmark 없음 |
| Theme classification | 50개 개발 문서의 dominant-theme top-1 agreement 72% | 독립 holdout, multi-label accuracy, calibrated probability 아님 |
| Mixed-theme detection | 문단 weak label과 heuristic 사례 점검 | 사람이 검수한 multi-label benchmark 없음 |
| OOD detection | WHO/OECD negative control 2건; WHO는 false positive overlap | 일반화된 OOD accuracy 아님 |
| Gemini summary | 5건 수동 evidence-alignment 점검 | 정량 summary accuracy나 faithfulness benchmark 없음 |
| Market context | 과거 뉴스·수익률 연결 및 상관 요약 | 수익률 예측 또는 투자 성과 검증 아님 |

남아 있는 평가 한계는 다음과 같습니다.

- 50개 문서는 일반화 성능을 주장하기에는 작습니다.
- 실제 문서는 여러 테마를 함께 다루므로 단일 dominant label이 내용을 충분히 표현하지 못합니다.
- WHO 보건 문서처럼 climate-health 표현이 있는 OOD 문서는 climate risk와 겹칠 수 있습니다.
- mixed/OOD 기준값은 개발 카탈로그에서 경험적으로 정한 heuristic입니다.
- 문단 단위 테이블은 weak label이며, 사람이 검수한 multi-label 정답셋이 아닙니다.
- 다음 독립 평가에는 새 PDF 50–100개 이상, human-reviewed multi-label, label별 precision/recall/F1과 macro F1, 전용 OOD negative set이 필요합니다.

## Data and Context

저장소에는 대표 보고서 신호, 검증 결과, GDELT GKG 주간 표본에서 만든 뉴스 톤, NASA GISTEMP 기후 이상치, 과거 주간 수익률 연결 결과가 포함되어 있습니다. GDELT 데이터는 주간 한 시점 표본이므로 전체 뉴스 모집단 분석으로 해석하면 안 됩니다. 시장 연결 역시 설명용 과거 상관·이벤트 컨텍스트입니다.

## Run

Python 환경에 의존성을 설치하고 API를 실행합니다.

```bash
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

브라우저에서 `http://localhost:8000`에 접속합니다. Gemini 요약은 `GEMINI_API_KEY`가 설정된 경우에만 활성화되며, 키는 저장소에 커밋하지 않습니다.

검증 자료를 처음부터 다시 만들 때는 PDF를 먼저 내려받아야 합니다.

```bash
python scripts/download_validation_pdfs.py
python scripts/build_model_validation_brief.py
python scripts/smoke_check.py
```

첫 번째 명령은 외부 PDF 호스트에 대한 네트워크 접근이 필요합니다. 주요 요약은 `outputs/tables/model_validation_brief.md`에 생성됩니다.

## Limitations

- 분류 헤드는 적은 수의 사람이 작성한 예시로 학습되어 라벨과 문서 유형 변화에 민감합니다.
- 현재 OOD 처리는 완전한 도메인 분류기가 아니라 relevance와 키워드 기반 규칙을 포함합니다.
- Gemini 출력은 생성형 요약이므로 반환된 evidence chunk와 함께 검토해야 합니다.
- 뉴스·시장 분석은 예비 상관 및 컨텍스트 분석이며, 인과 추론이나 투자 예측이 아닙니다.
