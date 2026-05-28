# 프로젝트 가이드라인
## Foundation Model 기반 에너지 리포트·뉴스 신호 생성과 시장 반응 분석

---

## 1. 프로젝트 목표

에너지·기후 관련 뉴스와 PDF 리포트를 Foundation Model 기반 파이프라인으로 처리해 수치 신호로 변환하고, 이 신호가 에너지 관련 ETF/기업 주가 수익률과 어떤 관계를 갖는지 분석한다.

이 프로젝트는 주가 예측 모델이 아니라 **문서/뉴스를 시장 분석용 신호로 바꾸는 downstream 분석 프로젝트**로 진행한다.

쉽게 말하면:

> 긴 뉴스와 PDF 보고서를 AI 모델로 읽게 한 뒤, "재생에너지에 좋은 내용인지", "화석연료 기업에는 부담인지", "전력망 기업에 기회인지"를 숫자로 바꾸고, 그 숫자를 주가 데이터와 비교하는 프로젝트다.

---

## 2. 연구 질문과 가설

### 연구 질문

> 에너지·기후 뉴스와 PDF 리포트에서 추출한 Foundation Model 기반 신호는 재생에너지·화석연료·전력 인프라 기업의 주가 수익률과 관계를 보이는가?

### 가설

| 가설 | 내용 | 검증 방법 |
|------|------|-----------|
| H1 | 기후 이상 지수(TAI)는 에너지 뉴스 감성(NSS/NSS_ADJ)보다 1~2주 선행한다 | TAI와 NSS/NSS_ADJ의 lag correlation |
| H2 | 뉴스 감성이 높아진 후 2~3주 내 ICLN-XLE 스프레드가 양의 방향으로 움직인다 | NSS_ADJ와 ET_SPREAD의 lag correlation |
| H3 | 2022 에너지 위기, 2023 엘니뇨 등 이벤트 기간에 관계가 강해진다 | 52주 rolling correlation 및 이벤트 마커 해석 |
| H4 | PDF 리포트에서 추출한 에너지 전환 신호는 관련 ETF/기업의 이후 수익률과 비교 가능한 downstream feature가 된다 | Report signal과 4주 후 수익률 비교 |

---

## 2-1. 확장된 Foundation Model 파이프라인

기존 뉴스 감성 분석에 더해, 교수님이 예시로 든 `PDF -> Text -> Summary` 흐름을 다음처럼 확장한다.

```text
PDF Report
-> Text Extraction
-> Section / Paragraph Segmentation
-> Key Evidence Retrieval
-> Foundation Embedding
-> Few-shot Risk / Opportunity Scoring
-> Extractive Summary
-> Report-to-Market Signal
-> ETF / Company Return Comparison
```

쉬운 설명:

```text
PDF를 그냥 요약하는 것이 아니라,
중요한 문단을 찾고,
그 문단이 어떤 산업에 좋은지/나쁜지 점수화하고,
그 점수를 주가 데이터와 연결한다.
```

사용한 Foundation Model 계열:

| 모델 | 역할 | 입력 | 출력 |
|------|------|------|------|
| `sentence-transformers/all-MiniLM-L6-v2` | 범용 문장 임베딩 | PDF 문단, few-shot 예시 문장 | 의미 벡터 |
| `ProsusAI/finbert` | 금융 뉴스 감성 분류 | 뉴스 헤드라인 | positive/negative/neutral + confidence |

Few-shot 방식:

- 사람이 만든 예시 문장 몇 개를 라벨별로 둔다.
- 새 PDF 문단과 예시 문장의 의미 벡터 유사도를 계산한다.
- 가장 가까운 의미를 기준으로 아래 점수를 만든다.

```text
renewable_opportunity
fossil_pressure
grid_infrastructure
climate_risk
transition_signal
```

---

## 3. 분석 대상

### ETF

| 티커 | 설명 | 역할 |
|------|------|------|
| ICLN | iShares Global Clean Energy ETF | 재생에너지 대표 |
| XLE | Energy Select Sector SPDR ETF | 전통 에너지 대표 |

### 기업

| 티커 | 기업 | 역할 |
|------|------|------|
| NEE | NextEra Energy | 재생에너지·전력 유틸리티 |
| XOM | ExxonMobil | 전통 에너지 |
| ETN | Eaton Corporation | 전력관리·전기화 인프라 |

### 핵심 파생 지표

```text
ET_SPREAD = ICLN 주간수익률 - XLE 주간수익률
```

분석 기간은 `2019-01-01`부터 `2024-12-31`까지로 한다.  
단, COVID 구간(`2020-03-01` ~ `2021-06-30`)은 기본 분석에서 제외하거나 별도 표시한다.

---

## 4. 프로젝트 구조

```text
energy_climate_project/
├── data/
│   ├── raw/
│   │   ├── climate/
│   │   ├── news/
│   │   ├── reports/
│   │   └── stock/
│   └── processed/
│       ├── climate_weekly_tai.csv
│       ├── news_sentiment_weekly.csv
│       ├── stock_returns_weekly.csv
│       ├── aligned_weekly_panel.csv
│       └── reports/
│           ├── report_paragraphs.csv
│           ├── report_evidence.csv
│           ├── report_signals.csv
│           ├── report_summaries.csv
│           └── report_stock_link.csv
├── notebooks/
│   ├── 01_data_collection.ipynb
│   ├── 02_finbert_sentiment.ipynb
│   ├── 03_time_series_alignment.ipynb
│   ├── 04_correlation_analysis.ipynb
│   └── 05_visualization.ipynb
├── src/
│   ├── collect_stock.py
│   ├── collect_climate.py
│   ├── collect_news.py
│   ├── sentiment_extractor.py
│   ├── align_timeseries.py
│   ├── correlation_analysis.py
│   ├── visualization.py
│   └── report_signal_pipeline.py
├── outputs/
│   ├── figures/
│   └── tables/
├── requirements.txt
└── README.md
```

---

## 5. 환경 설정

`requirements.txt`에는 아래 패키지를 포함한다.

```text
pandas>=2.0
numpy>=1.24
scipy>=1.11
yfinance>=0.2.36
requests>=2.31
transformers>=4.38
torch>=2.1
matplotlib>=3.8
seaborn>=0.13
jupyter>=1.0
python-dotenv>=1.0
gdelt>=0.1.10
tqdm>=4.66
```

설치:

```bash
pip install -r requirements.txt
```

FinBERT 모델은 첫 실행 시 Hugging Face에서 자동 다운로드된다.

---

## 6. 데이터 파일 규칙

| 데이터 | 저장 위치 | 필수 컬럼 |
|--------|-----------|-----------|
| 주가 주간 수익률 | `data/processed/stock_returns_weekly.csv` | `ICLN`, `XLE`, `NEE`, `XOM`, `ETN`, `ET_SPREAD` |
| 기후 주간 지표 | `data/processed/climate_weekly_tai.csv` | `TAI` |
| 뉴스 주간 감성 | `data/processed/news_sentiment_weekly.csv` | `NSS`, `NEWS_COUNT`, `NSS_ADJ` |
| 통합 패널 | `data/processed/aligned_weekly_panel.csv` | `TAI`, `NSS_ADJ`, `ET_SPREAD`, `IS_COVID` |
| 상관 분석 결과 | `outputs/tables/cross_corr_full.csv` | `signal`, `target`, `lag_weeks`, `r`, `p_value`, `significant` |
| PDF 리포트 신호 | `data/processed/reports/report_signals.csv` | `renewable_opportunity`, `fossil_pressure`, `grid_infrastructure`, `climate_risk`, `transition_signal` |
| 리포트-주가 연결 | `data/processed/reports/report_stock_link.csv` | `forward_4w_ICLN`, `forward_4w_XLE`, `forward_4w_ETN`, `forward_4w_ET_SPREAD` |

모든 주간 데이터는 `W-FRI` 기준으로 맞춘다.

---

## 7. 단계별 수행 가이드

### Step 1. 프로젝트 폴더와 환경 만들기

완료 조건:

- 위 디렉토리 구조 생성
- `requirements.txt` 생성
- 패키지 설치 완료

---

### Step 2. 주가 데이터 수집

사용 데이터:

- `ICLN`
- `XLE`
- `NEE`
- `XOM`
- `ETN`

처리 방식:

1. yfinance로 일별 종가를 수집한다.
2. 금요일 기준 주간 종가로 변환한다.
3. 주간 수익률을 계산한다.
4. `ET_SPREAD = ICLN - XLE`을 추가한다.
5. `data/processed/stock_returns_weekly.csv`로 저장한다.

주의:

- ETN은 2019년 이전부터 상장되어 있어 전체 분석 기간에 결측 없이 사용할 수 있다.
- ETF 분석과 기업 비교 모두 2019~2024 전체 기간을 기본으로 진행한다.

완료 조건:

- `stock_returns_weekly.csv` 생성
- `ET_SPREAD` 컬럼 존재

---

### Step 3. 기후 데이터 수집

사용 데이터:

- NASA POWER API
- 기본 좌표: 유럽 중심부 또는 분석 목적에 맞는 대표 좌표

처리 방식:

1. 일별 기온 데이터를 수집한다.
2. 기온 이상 지수 `TAI`를 계산한다.
3. 금요일 기준 주간 평균으로 변환한다.
4. `data/processed/climate_weekly_tai.csv`로 저장한다.

TAI 기본 정의:

```text
TAI = 일별 기온 - 30일 이동평균 기온
```

완료 조건:

- `climate_weekly_tai.csv` 생성
- `TAI` 컬럼 존재

---

### Step 4. 뉴스 데이터 수집

우선순위:

1. GDELT Python 패키지
2. GDELT 직접 API 또는 BigQuery
3. NewsAPI
4. Kaggle 등 공개 뉴스 데이터셋

필수 조건:

- 뉴스 데이터는 최소한 `date`, `title` 컬럼을 가져야 한다.
- 주제는 에너지, 기후, 재생에너지, 화석연료, 전력망, 탄소 정책 등으로 제한한다.

대표 키워드:

```text
renewable energy
solar energy
wind power
climate change
carbon tax
energy crisis
fossil fuel
oil price
natural gas
power grid
electricity demand
```

완료 조건:

- `data/raw/news/` 아래 원본 뉴스 CSV 저장
- `date`, `title` 컬럼 확인

---

### Step 5. FinBERT 감성 점수 추출

사용 모델:

```text
ProsusAI/finbert
```

처리 방식:

1. 뉴스 제목을 FinBERT에 입력한다.
2. 감성 라벨을 점수로 변환한다.
3. 주간 단위로 평균 감성을 계산한다.
4. 뉴스 수를 반영한 조정 감성 점수를 만든다.

감성 점수 변환:

| FinBERT 라벨 | 점수 |
|--------------|------|
| positive | `+confidence` |
| negative | `-confidence` |
| neutral | `0` |

주간 감성 지표:

```text
NSS = 주간 평균 감성 점수
NEWS_COUNT = 주간 뉴스 수
NSS_ADJ = NSS × log(NEWS_COUNT + 1)
```

완료 조건:

- `data/processed/news_sentiment_weekly.csv` 생성
- `NSS`, `NEWS_COUNT`, `NSS_ADJ` 컬럼 존재

---

### Step 6. 시계열 정렬

처리 방식:

1. 주가, 기후, 뉴스 감성 데이터를 불러온다.
2. 날짜 인덱스를 기준으로 병합한다.
3. COVID 구간 플래그를 추가한다.
4. `data/processed/aligned_weekly_panel.csv`로 저장한다.

COVID 플래그:

```text
IS_COVID = 2020-03-01 <= date <= 2021-06-30
```

완료 조건:

- `aligned_weekly_panel.csv` 생성
- `TAI`, `NSS`, `NSS_ADJ`, `ET_SPREAD`, `IS_COVID` 컬럼 존재

---

### Step 7. Cross-correlation 분석

분석 대상:

```text
signals = TAI, NSS, NSS_ADJ
targets = ET_SPREAD, ICLN, XLE, NEE, XOM, ETN
lags = -4주 ~ +4주
```

해석 기준:

- `lag_weeks < 0`: signal이 target보다 선행
- `lag_weeks > 0`: signal이 target보다 후행
- 기본 분석은 COVID 구간 제외

완료 조건:

- `outputs/tables/cross_corr_full.csv` 생성
- H1, H2에 대한 lag별 상관계수와 p-value 확인

---

### Step 8. Rolling correlation 분석

목적:

- 시간에 따라 뉴스 감성과 주가 스프레드의 관계가 어떻게 변하는지 확인한다.

기본 설정:

```text
window = 52주
min_periods = 30주
대상 = NSS_ADJ와 ET_SPREAD
```

이벤트 마커:

| 날짜 | 이벤트 |
|------|--------|
| 2022-02-24 | 러시아-우크라이나 전쟁 |
| 2022-08-01 | 유럽 폭염 |
| 2022-10-01 | 에너지 위기 정점 |
| 2023-06-01 | 엘니뇨 시작 |
| 2024-01-01 | AI 전력 수요 이슈 |

완료 조건:

- rolling correlation 계산 완료
- 이벤트 구간에서 상관 강도 변화 해석

---

### Step 9. 시각화

최종 그림은 4개를 만든다.

| 그림 | 내용 | 저장 위치 |
|------|------|-----------|
| Figure 1 | TAI, NSS_ADJ, ET_SPREAD 시계열 | `outputs/figures/fig1_timeseries.png` |
| Figure 2 | lag별 cross-correlation heatmap | `outputs/figures/fig2_lag_heatmap.png` |
| Figure 3 | NSS_ADJ와 ET_SPREAD의 rolling correlation | `outputs/figures/fig3_rolling_corr.png` |
| Figure 4 | NEE, XOM, ETN 기업별 감성 반응 비교 | `outputs/figures/fig4_company_sensitivity.png` |

완료 조건:

- 위 4개 그림 파일 생성
- 발표 자료에 바로 넣을 수 있는 해상도로 저장

---

### Step 10. 결과 해석과 발표 준비

정리해야 할 내용:

1. H1, H2, H3가 지지되는지 여부
2. 가장 강한 상관을 보인 signal-target-lag 조합
3. COVID 제외 여부에 따른 결과 차이
4. 기업별 사업 구조 차이로 인한 해석 한계
5. 이 분석이 예측이 아니라 관계 분석이라는 점
6. FinBERT를 Foundation Model로 사용한 부분

발표 구성:

| 순서 | 내용 |
|------|------|
| 1 | 연구 동기 |
| 2 | 연구 질문과 가설 |
| 3 | 데이터 파이프라인 |
| 4 | FinBERT와 Foundation Model 연결 |
| 5 | 결과 Figure 1~4 |
| 6 | 가설 검증 결과 |
| 7 | 한계와 확장 방향 |

---

### Step 11. PDF 리포트 기반 Report-to-Market Signal 생성

사용 PDF:

| 파일 | 설명 |
|------|------|
| `iea_world_energy_outlook_2023.pdf` | IEA World Energy Outlook 2023 |
| `iea_renewables_2023.pdf` | IEA Renewables 2023 |
| `iea_oil_gas_net_zero_2023.pdf` | IEA Oil and Gas Industry in Net Zero Transitions |
| `exxon_acs_2023.pdf` | ExxonMobil Advancing Climate Solutions 2023 |
| `eaton_annual_2023.pdf` | Eaton Annual Report 2023 |

처리 방식:

1. PDF에서 텍스트를 추출한다.
2. 문단 단위로 나눈다.
3. TF-IDF로 에너지 전환 관련 근거 문단을 먼저 찾는다.
4. 범용 Transformer 임베딩 모델로 few-shot 예시 문장과 문단의 의미 유사도를 계산한다.
5. 보고서별로 아래 점수를 만든다.

```text
renewable_opportunity
fossil_pressure
grid_infrastructure
climate_risk
transition_signal
```

6. 보고서 날짜 이후 4주간 ETF/기업 수익률과 연결한다.

완료 조건:

- `data/processed/reports/report_signals.csv` 생성
- `data/processed/reports/report_stock_link.csv` 생성
- `outputs/tables/report_signal_summary.md` 생성
- `outputs/figures/fig5_report_signals.png` 생성

쉬운 설명:

> 보고서마다 "어느 산업에 좋은 내용이 많은가?"를 숫자로 만든다. 예를 들어 전력망 이야기가 많고 의미상 관련성이 높으면 ETN에 가까운 신호로 본다.

---

## 8. 자주 생기는 문제와 대응

| 문제 | 원인 | 대응 |
|------|------|------|
| 특정 종목 데이터 결측 | 상장 시점 또는 다운로드 문제 | 결측 원인을 확인하고 필요 시 대체 종목 사용 |
| NASA POWER API timeout | 요청 기간이 길거나 API 응답 지연 | 연도별로 나눠 수집 후 병합 |
| GDELT 수집 실패 | 패키지/API 구조가 불안정 | NewsAPI 또는 공개 데이터셋으로 대체 |
| FinBERT 실행이 느림 | CPU 실행 또는 데이터 과다 | 샘플 테스트 후 전체 실행, batch size 조정 |
| GPU 메모리 부족 | batch size 과대 | batch size 축소 또는 CPU 사용 |
| 상관 분석 결과가 약함 | 실제 관계가 약하거나 데이터 품질 문제 | 결과를 과장하지 않고 한계와 함께 해석 |

---

## 9. 최종 산출물 체크리스트

```text
[ ] requirements.txt
[ ] src/collect_stock.py
[ ] src/collect_climate.py
[ ] src/collect_news.py
[ ] src/sentiment_extractor.py
[ ] data/processed/stock_returns_weekly.csv
[ ] data/processed/climate_weekly_tai.csv
[ ] data/processed/news_sentiment_weekly.csv
[ ] data/processed/aligned_weekly_panel.csv
[ ] outputs/tables/cross_corr_full.csv
[ ] outputs/figures/fig1_timeseries.png
[ ] outputs/figures/fig2_lag_heatmap.png
[ ] outputs/figures/fig3_rolling_corr.png
[ ] outputs/figures/fig4_company_sensitivity.png
[ ] 발표용 결과 요약
```

---

## 10. 발표에서 반드시 언급할 문장

> 이 프로젝트에서 FinBERT는 Foundation Model을 fine-tuning 없이 frozen 상태로 활용한 사례입니다.  
> 금융 텍스트로 사전학습된 모델을 에너지 뉴스 헤드라인에 적용해 비정형 텍스트를 주간 감성 신호로 변환했고, 이를 기후 지표 및 주가 수익률과 결합해 시차 관계를 분석했습니다.

---

## 11. 현재 프로젝트 완료 상태

현재 프로젝트는 확장된 Step 11까지 완료되었다.

완료된 핵심 산출물:

```text
data/processed/stock_returns_weekly.csv
data/processed/climate_weekly_tai.csv
data/raw/news/news_headlines_raw.csv
data/processed/news_sentiment_weekly.csv
data/processed/aligned_weekly_panel.csv
outputs/tables/cross_corr_full.csv
outputs/tables/rolling_corr_nss_adj_et_spread.csv
outputs/tables/company_sensitivity_best_lags.csv
outputs/tables/final_result_summary.md
outputs/tables/report_signal_summary.md
outputs/figures/fig1_timeseries.png
outputs/figures/fig2_lag_heatmap.png
outputs/figures/fig3_rolling_corr.png
outputs/figures/fig4_company_sensitivity.png
outputs/figures/fig5_report_signals.png
```

데이터 현황:

| 데이터 | 상태 |
|--------|------|
| 주가 데이터 | 312주, 2019-01-11 ~ 2024-12-27, 결측 없음 |
| 기후 데이터 | 311주, 2019-01-18 ~ 2024-12-27, 결측 없음 |
| 원본 뉴스 | 3,340건, 2019-01-05 ~ 2024-12-14 |
| 뉴스 감성 | 100개 관측 주차, NSS/NSS_ADJ 결측 없음 |
| 통합 패널 | 312주, 주가·기후·뉴스 감성 정렬 완료 |
| PDF 리포트 | 5개 보고서 처리 완료 |
| 리포트 신호 | renewable/fossil/grid/climate 점수 생성 완료 |

주의:

- GDELT rate limit으로 인해 뉴스 데이터는 모든 주차를 완전하게 덮는 전수 데이터가 아니다.
- 뉴스 감성 분석은 실제 수집된 뉴스 주차를 기준으로 수행했다.
- 따라서 결과는 예측 성능 주장보다 Foundation Model 기반 비정형 텍스트 신호화 및 시차 관계 분석으로 해석해야 한다.

---

## 12. 최종 가설 검증 결과

| 가설 | 결론 | 근거 |
|------|------|------|
| H1: TAI가 NSS/NSS_ADJ보다 1~2주 선행 | 지지되지 않음 | TAI -> NSS_ADJ의 최대 절대 상관은 lag +2, `r=-0.1208`, `p=0.2360` |
| H2: NSS_ADJ 상승 후 ET_SPREAD가 양의 방향으로 이동 | 지지되지 않음 | NSS_ADJ -> ET_SPREAD의 최대 절대 상관은 lag +4, `r=-0.1891`, `p=0.0622`로 약하고 음의 방향 |
| H3: 이벤트 기간에 관계 강화 | 부분적·기술적으로 관찰 | rolling correlation이 2022년 하반기와 2023년 초에 더 강한 음의 값을 보임 |
| H4: PDF 리포트 신호를 downstream 시장 분석 feature로 활용 | 구현 완료 | 5개 PDF 보고서를 점수화하고 4주 후 수익률과 연결 |

기업별 결과:

| 관계 | Best lag | r | p-value | 해석 |
|------|---------:|---:|--------:|------|
| NSS_ADJ -> NEE | +2 | -0.1809 | 0.0731 | 약하지만 유의하지 않음 |
| NSS_ADJ -> XOM | +4 | 0.2161 | 0.0326 | 약하지만 통계적으로 유의 |
| NSS_ADJ -> ETN | +3 | 0.1995 | 0.0477 | 약하지만 통계적으로 유의 |

최종 해석:

> FinBERT 기반 에너지 뉴스 감성은 시장·기후 시계열과 결합 가능한 수치 신호로 만들 수 있었지만, 현재 수집 데이터에서는 ICLN-XLE 스프레드에 대한 강한 예측적 관계는 확인되지 않았다. 다만 XOM, ETN 같은 기업 단위 반응에서는 약한 유의 신호가 관찰되었다.

확장 파이프라인 해석:

> PDF 리포트 기반 분석은 단순 요약이 아니라, 보고서에서 관련 근거 문단을 찾고 few-shot 예시와 비교해 산업별 점수로 바꾸는 pipeline이다. 이 부분이 강의에서 말한 "Foundation Model의 입력/출력을 이해하고 downstream task에 연결하는 작업"에 더 직접적으로 부합한다.

---

## 13. 최종 산출물 체크리스트

```text
[x] requirements.txt
[x] src/collect_stock.py
[x] src/collect_climate.py
[x] src/collect_news.py
[x] src/sentiment_extractor.py
[x] src/align_timeseries.py
[x] src/correlation_analysis.py
[x] src/visualization.py
[x] src/report_signal_pipeline.py
[x] data/processed/stock_returns_weekly.csv
[x] data/processed/climate_weekly_tai.csv
[x] data/processed/news_sentiment_weekly.csv
[x] data/processed/aligned_weekly_panel.csv
[x] outputs/tables/cross_corr_full.csv
[x] outputs/tables/rolling_corr_nss_adj_et_spread.csv
[x] outputs/tables/company_sensitivity_best_lags.csv
[x] outputs/tables/final_result_summary.md
[x] outputs/tables/report_signal_summary.md
[x] data/processed/reports/report_paragraphs.csv
[x] data/processed/reports/report_evidence.csv
[x] data/processed/reports/report_signals.csv
[x] data/processed/reports/report_summaries.csv
[x] data/processed/reports/report_stock_link.csv
[x] outputs/figures/fig1_timeseries.png
[x] outputs/figures/fig2_lag_heatmap.png
[x] outputs/figures/fig3_rolling_corr.png
[x] outputs/figures/fig4_company_sensitivity.png
[x] outputs/figures/fig5_report_signals.png
[x] 발표용 결과 요약
```

---

*마지막 업데이트: 2026-05-29*

