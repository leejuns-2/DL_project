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
- Gemini 생성 요약: `gemini-3.5-flash`를 사용해 근거 문단을 조심스러운 한국어 연구 요약으로 변환합니다.
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
  -> Gemini Evidence Summary
  -> News Context Bridge
  -> Historical Stock-return Link
```

## 데이터 요약

| 데이터 | 현재 상태 |
|---|---|
| Stock weekly returns | 2019-2024 주간 수익률 CSV 포함 |
| Report signals | 핵심 에너지 PDF 5개 분석 결과 포함 |
| Expanded PDF validation | 추가 검증 PDF 25개 결과 포함 |
| Zero-shot vs few-shot comparison | zero-shot 10/25, few-shot 18/25 비교 결과 포함 |
| News sentiment context | 실제 GDELT GKG weekly sample tone signal 포함 |
| Report-stock link | 보고서 날짜 이후 4주 과거 수익률 연결 포함 |

뉴스 컨텍스트 CSV는 GDELT GKG 공개 파일에서 매주 금요일 12:00 UTC 파일을 표본 수집해 만든 실제 뉴스 tone 신호입니다. 전체 뉴스 모집단이 아니라 주간 1시점 샘플이므로, Bloomberg/NewsAPI 전체 히스토리와 같은 완전한 뉴스 원자료 분석으로 과장하면 안 됩니다.

## 해석 주의

- 이 앱은 미래 수익률을 예측하지 않습니다.
- 포트폴리오 계산은 과거 특정 기간의 실제 수익률을 적용한 시나리오입니다.
- PDF 검증은 현재 재현 가능한 기준으로 25개 중 18개 일치입니다. 표본이 아직 작고 복합 주제 문서의 단일 라벨 평가가 어려워 정량 일반화 성능으로 해석하면 안 됩니다.
- 뉴스 컨텍스트는 현재 샘플 신호이므로, 대량 뉴스 원자료 기반 정량 검증으로 과장하면 안 됩니다.
- 상관관계와 수익률 연결은 인과관계 증명이 아닙니다.

## 로컬 실행

```bash
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

브라우저에서 `http://localhost:8000` 접속

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
