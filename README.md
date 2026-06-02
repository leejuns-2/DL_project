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

에너지·기후 PDF 보고서를 텍스트로 변환하고, 근거 문단을 추출한 뒤, 사전학습 Transformer 임베딩 모델과 few-shot 분류 헤드를 이용해 시장 분석용 신호로 바꾸는 연구용 MVP입니다.

이 앱은 투자 추천 도구가 아닙니다. PDF 내용, 뉴스 컨텍스트, 과거 주가 수익률을 연결해 “보고서 신호가 시장 데이터와 어떻게 함께 보이는지”를 탐색하는 downstream 분석 예시입니다.

## 핵심 기능

- PDF 업로드 분석: 에너지 보고서를 업로드하면 문단 추출, 근거 검색, 주제 점수화, Gemini 요약을 수행합니다.
- Few-shot learning: MiniLM 임베딩 모델은 고정하고, 사람이 작성한 소수의 라벨 예시로 Logistic Regression 분류 헤드를 학습합니다.
- Zero-shot vs few-shot 비교: 사전학습 임베딩 유사도만 쓴 baseline과 few-shot classifier head를 같은 25개 PDF에서 비교합니다.
- Mixed-signal 판정: WEO처럼 상위 두 테마가 모두 강한 복합 보고서는 단일 자산 힌트 대신 복합 전환 신호로 표시합니다.
- Chunk multi-label 보완: PDF 단일 라벨 외에 근거 문단별 weak multi-label 테이블을 만들어 복합 주제 문서를 더 세밀하게 점검합니다.
- OOD subtype 판정: WHO 보건 문서처럼 climate-health 표현이 많은 문서는 climate risk 확정 대신 overlap/review 대상으로 표시할 수 있게 합니다.
- Evidence-grounded Gemini 요약: `gemini-3.5-flash`를 사용할 때 요약과 함께 `evidence_chunk_ids`, `support_level`을 반환해 근거 문단 확인을 강제합니다.
- 뉴스-PDF 연결: 실제 GDELT GKG 공개 원자료에서 주간 샘플을 수집해 보고서 날짜 주변 뉴스 tone 컨텍스트를 PDF 신호와 연결합니다.
- Downstream stock link: 보고서 날짜 전후의 실제 과거 수익률을 연결해 시나리오로 보여줍니다.
- 포트폴리오 시뮬레이터: 사용자가 투자금과 비중을 넣으면 과거 수익률 기반 가상 손익을 계산합니다.

## 사용 모델

| 모델 | 역할 |
|---|---|
| `sentence-transformers/all-MiniLM-L6-v2` | PDF 문단과 라벨 예시 문장을 임베딩 |
| Logistic Regression heads | 소수 라벨 예시 기반 downstream few-shot topic classification |
| `gemini-3.5-flash` | 근거 문단 기반 생성형 한국어 요약 |

주의: MiniLM 자체의 파라미터를 fine-tuning하지는 않습니다. 본 프로젝트의 few-shot learning은 고정된 foundation embedding 위에 작은 downstream 분류 헤드를 학습하는 방식입니다.

## 분석 흐름

```text
PDF Upload
  -> Text Extraction (PyMuPDF)
  -> Evidence Retrieval (TF-IDF)
  -> MiniLM Embedding
  -> Few-shot Logistic Classifier Heads
  -> Report Topic Scores
  -> Single or Mixed Signal Decision
  -> Chunk-level Weak Multi-label Audit
  -> Evidence-grounded Gemini Summary
  -> News Context Bridge
  -> Historical Stock-return Link
```

## 데이터 요약

| 데이터 | 현재 상태 |
|---|---|
| Stock weekly returns | 2019-2024 주간 수익률 CSV 포함 |
| Report signals | 핵심 에너지 PDF 5개 분석 결과 포함 |
| Validation PDF catalog | `data/sample_pdfs`에 로컬 검증 PDF 50개 준비 |
| Expanded PDF validation | 기존 25개 결과 포함, 50개 카탈로그 기준 재검증 가능 |
| PDF validation chunk labels | 검증 재생성 시 문단 단위 weak multi-label 검토 테이블 생성 |
| Zero-shot vs few-shot comparison | zero-shot 10/25, few-shot 18/25 비교 결과 포함 |
| News sentiment context | 실제 GDELT GKG weekly sample tone signal 포함 |
| Report-stock link | 보고서 날짜 이후 4주 과거 수익률 연결 포함 |

검증 요약은 `outputs/tables/model_validation_brief.md`에 정리되어 있습니다. 여기에는 핵심 지표, baseline 비교, 실패 사례, OOD 점검, Gemini 요약 검토, 라이브 웹 테스트 기록이 포함됩니다.

뉴스 컨텍스트 CSV는 GDELT GKG 공개 파일에서 매주 금요일 12:00 UTC 파일을 표본 수집해 만든 실제 뉴스 tone 신호입니다. 전체 뉴스 모집단이 아니라 주간 1시점 샘플이므로, Bloomberg/NewsAPI 전체 히스토리와 같은 완전한 뉴스 원자료 분석으로 과장하면 안 됩니다.

## 해석 주의

- 이 앱은 미래 수익률을 예측하지 않습니다.
- 포트폴리오 계산은 과거 특정 기간의 실제 수익률을 적용한 시나리오입니다.
- 기존 PDF 검증 결과는 25개 중 18개 일치 기준입니다. 표본이 아직 작고 복합 주제 문서의 단일 라벨 평가가 어려워 정량 일반화 성능으로 해석하면 안 됩니다.
- 현재 로컬에는 50개 검증 PDF 카탈로그가 준비되어 있습니다. 그래도 일반화 성능을 주장하려면 문서 유형별 층화 샘플링으로 최소 100개 이상 PDF와 사람이 검수한 chunk multi-label 평가셋이 필요합니다.
- WHO 보건 문서처럼 climate-health 표현이 많은 OOD 문서는 climate risk와 겹칠 수 있으므로, `ood_subtype=climate_health_overlap` 또는 review 판정을 별도로 확인해야 합니다.
- Gemini 요약은 생성형 출력이므로 단독 근거로 쓰지 말고, 함께 반환되는 evidence chunk와 support level을 확인해야 합니다.
- 뉴스 컨텍스트는 현재 샘플 신호이므로, 대량 뉴스 원자료 기반 정량 검증으로 과장하면 안 됩니다.
- 상관관계와 수익률 연결은 인과관계 증명이 아닙니다.

## 로컬 실행

```bash
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

브라우저에서 `http://localhost:8000` 접속

## 검증 자료 재생성

```bash
python scripts/build_model_validation_brief.py
python scripts/smoke_check.py
```

생성되는 핵심 문서는 `outputs/tables/model_validation_brief.md`입니다.

## Gemini 설정

Hugging Face Space의 Variables/Secrets에 아래 값을 넣으면 Gemini 요약이 활성화됩니다.

```bash
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-3.5-flash
GENAI_PROVIDER=gemini
GEMINI_THINKING_LEVEL=high
GEMINI_MAX_OUTPUT_TOKENS=600
```

API 키는 코드나 Git에 직접 넣으면 안 됩니다.
