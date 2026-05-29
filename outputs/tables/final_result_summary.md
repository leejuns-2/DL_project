# Final Result Summary

## Project Status

본 프로젝트는 교수님이 제시한 `PDF -> Text -> Summary` 예시를 에너지 시장 분석 문제로 확장한 MVP입니다. 단순 요약에서 끝내지 않고, PDF 근거 문단을 주제 신호로 변환하고, 뉴스 컨텍스트 및 과거 주가 수익률과 연결했습니다.

## Current Pipeline

1. PDF 보고서 업로드 또는 사전 수집 보고서 사용
2. PyMuPDF 기반 텍스트 추출
3. TF-IDF 기반 에너지 전환 관련 근거 문단 검색
4. MiniLM 임베딩 생성
5. 소수 라벨 예시 기반 few-shot Logistic Regression 분류 헤드 학습
6. 재생에너지, 화석연료 압력, 전력망, 기후 리스크 점수 산출
7. Gemini 3.5 Flash 기반 근거 요약 생성
8. 보고서 날짜 주변 뉴스 감성 컨텍스트 연결
9. 보고서 날짜 이후 과거 주가 수익률과 downstream 연결
10. 포트폴리오 시나리오 계산 및 웹 MVP 제공

## Foundation Model Usage

| Model | Role |
|---|---|
| `sentence-transformers/all-MiniLM-L6-v2` | PDF 문단과 예시 문장을 벡터로 변환하는 사전학습 Transformer 임베딩 모델 |
| Logistic Regression heads | 고정된 임베딩 위에서 소수 라벨 예시로 학습되는 downstream few-shot classifier |
| `gemini-3.5-flash` | PDF 근거 문단을 한국어 연구 요약으로 생성 |

정확한 표현:

> 본 프로젝트는 MiniLM foundation embedding을 고정하고, 사람이 정의한 소수 라벨 예시를 이용해 downstream 분류 헤드를 few-shot 방식으로 학습했습니다.

과장하면 안 되는 표현:

> 대형 foundation model 전체를 fine-tuning했다.

## Data Summary

| Dataset | File | Status |
|---|---|---|
| Stock weekly returns | `data/processed/stock_returns_weekly.csv` | 배포 포함 |
| Report signals | `data/processed/reports/report_signals.csv` | 핵심 PDF 5개 |
| Report-stock link | `data/processed/reports/report_stock_link.csv` | 핵심 PDF 5개 |
| Expanded PDF validation | `data/processed/reports/expanded_pdf_validation.csv` | 추가 PDF 8개 |
| News context signal | `data/processed/news_sentiment_weekly.csv` | 보고서 날짜 주변 sample weekly context |
| Report-news bridge | `data/processed/reports/report_news_bridge.csv` | 뉴스 컨텍스트 연결 완료 |

## Expanded PDF Validation

추가 검증 표본은 IRENA 보고서뿐 아니라 NextEra, Siemens Energy, IPCC 자료를 포함해 라벨 다양성을 늘렸습니다.

| Metric | Value |
|---|---:|
| Validation PDFs | 8 |
| Matched expected direction | 8 |
| Interpretation | 소규모 MVP 검증 |

주의:

> 8/8 일치는 소규모 검증 결과입니다. 이를 일반화 성능이나 정확도 100%로 발표하면 안 됩니다.

## News-PDF Bridge

이전에는 뉴스 분석과 PDF 앱이 분리되어 보일 수 있었습니다. 현재는 `report_news_bridge.csv`를 통해 각 보고서 날짜 이전 4주 뉴스 감성 평균과 추세를 연결합니다.

현재 뉴스 CSV는 대량 원자료 전체가 아니라, 보고서 날짜 주변 sample news-context signal입니다. 따라서 발표에서는 다음처럼 말하는 것이 안전합니다.

> 뉴스 감성 신호는 시장 분위기 컨텍스트이고, PDF 신호는 보고서 기반 이벤트 신호입니다. 두 신호를 보고서 날짜 기준으로 연결해 주가 downstream 분석과 함께 확인했습니다.

## Interpretation

본 프로젝트는 예측 시스템이 아니라 관계 분석 파이프라인입니다. PDF, 뉴스, 주가 데이터를 하나의 흐름으로 연결해 비정형 문서가 어떻게 정량 신호로 바뀌고 downstream task에 활용되는지 보여주는 것이 핵심입니다.

안전한 발표 문장:

> 이 시스템은 PDF를 넣으면 미래 수익률을 예측하는 도구가 아니라, 보고서 근거 문단을 few-shot topic signal로 변환하고, 뉴스 분위기 및 과거 주가 반응과 연결해 분석하는 연구용 MVP입니다.

## Limitations

- 검증 PDF 수가 아직 작습니다.
- 뉴스 컨텍스트는 sample signal이므로 대량 뉴스 기반 일반화 검증은 추가로 필요합니다.
- Gemini 요약은 생성형 모델 출력이므로 근거 문단과 함께 확인해야 합니다.
- 과거 수익률 연결은 예측이나 투자 추천이 아닙니다.
- 상관관계와 수익률 연결은 인과관계 증명이 아닙니다.
