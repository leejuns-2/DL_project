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

## Overview

에너지·기후 PDF에서 관련 문단을 찾고, 문서의 주요 테마를 점수화한 뒤 뉴스와 과거 시장 데이터를 함께 보여주는 분석 도구입니다. 목표는 보고서의 근거를 잃지 않으면서 비정형 문서를 비교 가능한 신호로 바꾸는 것입니다.

이 도구는 수익률을 예측하거나 투자를 추천하지 않습니다. 뉴스와 시장 데이터는 보고서 해석을 위한 과거 컨텍스트이며, 관찰된 상관관계는 인과관계를 뜻하지 않습니다.

## What I Built

- PyMuPDF 기반 PDF 텍스트 추출과 문단 분할
- TF-IDF와 MiniLM 유사도를 함께 쓰는 근거 문단 검색
- 고정된 MiniLM 임베딩 위에서 동작하는 테마별 Logistic Regression 분류 헤드
- zero-shot 유사도 기준선과 supervised linear probe 비교
- 복합 테마 문서와 비에너지 문서를 위한 mixed/OOD 판정
- 검색 근거 ID를 함께 반환하는 Gemini 요약
- GDELT 뉴스 톤과 보고서 날짜 전후 과거 시장 데이터 연결

## Pipeline

```text
PDF
  -> text extraction
  -> evidence retrieval
  -> MiniLM embedding
  -> topic classifier
  -> mixed-theme / OOD checks
  -> evidence-grounded summary
  -> news and historical market context
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
| Gemini summary | 5건 수동 evidence-alignment 점검 | 정량 summary accuracy나 faithfulness benchmark 아님 |
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

## My Contribution

저장소에서 확인할 수 있는 구현 범위는 다음과 같습니다.

- end-to-end 보고서 분석 흐름 설계
- 근거 검색, 테마 점수화, mixed/OOD 판정 구현
- zero-shot과 supervised linear probe 비교 및 검증 스크립트 작성
- 개발 카탈로그 평가 helper를 `src/evaluation.py`로 분리하고 명칭 오해를 막는 단위 테스트 추가
- 보고서 신호를 뉴스·과거 시장 컨텍스트와 연결
- 실패 사례와 해석 한계 문서화

## Limitations

- 분류 헤드는 적은 수의 사람이 작성한 예시로 학습되어 라벨과 문서 유형 변화에 민감합니다.
- 현재 OOD 처리는 완전한 도메인 분류기가 아니라 relevance와 키워드 기반 규칙을 포함합니다.
- Gemini 출력은 생성형 요약이므로 반환된 evidence chunk와 함께 검토해야 합니다.
- 뉴스·시장 분석은 예비 상관 및 컨텍스트 분석이며, 인과 추론이나 투자 예측이 아닙니다.
