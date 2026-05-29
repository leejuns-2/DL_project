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
| Expanded PDF validation | `data/processed/reports/expanded_pdf_validation.csv` | 추가 PDF 15개 |
| Test PDF manifest | `data/processed/reports/sample_pdf_manifest.csv` | 로컬 저장 PDF 15개 목록 |
| News context signal | `data/processed/news_sentiment_weekly.csv` | 실제 GDELT GKG weekly sample tone |
| Climate anomaly | `data/processed/climate_monthly_gistemp_tai.csv` | NASA GISTEMP monthly anomaly |
| Report-news bridge | `data/processed/reports/report_news_bridge.csv` | 뉴스 컨텍스트 연결 완료 |
| Actual climate-news lag | `data/processed/reports/actual_climate_news_lag_corr.csv` | H1 예비 검증 |
| Actual news-stock lag | `data/processed/reports/actual_news_stock_best_lag.csv` | H2 예비 검증 |
| PDF validation metrics | `data/processed/reports/pdf_validation_metrics.csv` | confusion matrix, macro-F1 |
| Gemini summary check | `data/processed/reports/gemini_summary_human_check.csv` | 표본 5개 근거 점검 |

## Expanded PDF Validation

추가 검증 표본은 IRENA 보고서뿐 아니라 NextEra, Siemens Energy, IPCC, IEA 전력망·전력·석유·가스·석탄 자료를 포함해 라벨 다양성을 늘렸습니다.

| Metric | Value |
|---|---:|
| Validation PDFs | 15 |
| Matched expected direction | 15 |
| Interpretation | 소규모 MVP 검증 |

주의:

> 15/15 일치는 소규모 검증 결과입니다. 이를 정량 일반화 성능으로 발표하면 안 됩니다.

## News-PDF Bridge

이전에는 뉴스 분석과 PDF 앱이 분리되어 보일 수 있었습니다. 현재는 `report_news_bridge.csv`를 통해 각 보고서 날짜 이전 4주 뉴스 감성 평균과 추세를 연결합니다.

현재 뉴스 CSV는 GDELT GKG 공개 원자료에서 매주 금요일 12:00 UTC 파일을 표본 수집해 만든 실제 뉴스 tone 신호입니다. 전체 뉴스 모집단이 아니라 weekly one-file sample이므로 다음처럼 말하는 것이 안전합니다.

> 뉴스 감성 신호는 실제 GDELT GKG 주간 샘플에서 계산한 시장 분위기 컨텍스트이고, PDF 신호는 보고서 기반 이벤트 신호입니다. 두 신호를 보고서 날짜 기준으로 연결해 주가 downstream 분석과 함께 확인했습니다.

## Actual Preliminary Hypothesis Checks

| Hypothesis | Data | Preliminary result | Interpretation |
|---|---|---|---|
| H1: TAI -> News sentiment | NASA GISTEMP monthly anomaly + actual GDELT GKG monthly aggregated tone | lag +1 month `r≈0.406`, `p≈0.0004` | 예비 지지. 단 월별 집계와 GDELT 표본 방식의 한계가 있음 |
| H2: News sentiment -> ET_SPREAD | actual GDELT GKG weekly tone + weekly stock returns | best lag +2 weeks `r≈-0.130`, `p≈0.022` | 통계적으로는 약하게 관찰되지만 기대한 양의 방향과 반대 |
| H3: rolling/event pattern | actual GDELT GKG weekly tone + weekly stock returns | rolling correlation varies over time | 기술적 관찰. 인과관계 아님 |

## Interpretation

본 프로젝트는 예측 시스템이 아니라 관계 분석 파이프라인입니다. PDF, 뉴스, 주가 데이터를 하나의 흐름으로 연결해 비정형 문서가 어떻게 정량 신호로 바뀌고 downstream task에 활용되는지 보여주는 것이 핵심입니다.

안전한 발표 문장:

> 이 시스템은 PDF를 넣으면 미래 수익률을 예측하는 도구가 아니라, 보고서 근거 문단을 few-shot topic signal로 변환하고, 뉴스 분위기 및 과거 주가 반응과 연결해 분석하는 연구용 MVP입니다.

## Limitations

- 검증 PDF 수가 아직 작습니다.
- 뉴스 컨텍스트는 실제 GDELT 기반이지만 주간 1시점 표본이므로 대량 뉴스 기반 일반화 검증은 추가로 필요합니다.
- Gemini 요약은 생성형 모델 출력이므로 근거 문단과 함께 확인해야 합니다.
- 과거 수익률 연결은 예측이나 투자 추천이 아닙니다.
- 상관관계와 수익률 연결은 인과관계 증명이 아닙니다.
