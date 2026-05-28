# Energy Climate Report-to-Market Signal Project

에너지·기후 뉴스와 PDF 리포트를 Foundation Model 기반 파이프라인으로 처리해 시장 분석용 신호로 변환하는 프로젝트입니다.

## 분석 목표

- 뉴스 헤드라인을 FinBERT로 감성 점수화
- PDF 리포트에서 에너지 전환 관련 근거 문단 추출
- 범용 Transformer 임베딩 모델로 few-shot 산업 점수 생성
- NASA POWER 기온 데이터로 기후 이상 지수(TAI) 생성
- yfinance로 에너지 ETF/기업 주간 수익률 생성
- `TAI`, `NSS_ADJ`, `ET_SPREAD`, `report_signal` 간 관계 분석

쉬운 설명:

> 뉴스와 보고서를 AI 모델로 읽게 해서 숫자 신호로 바꾸고, 그 숫자가 에너지 관련 주가와 어떤 관계가 있는지 확인합니다.

## 기본 실행 흐름

1. 패키지 설치

```bash
pip install -r requirements.txt
```

2. 주가 데이터 수집

```bash
python src/collect_stock.py
```

3. 기후 데이터 수집

```bash
python src/collect_climate.py
```

4. 뉴스 데이터 수집 및 FinBERT 감성 추출

```bash
python src/collect_news.py
python src/sentiment_extractor.py
```

5. 이후 `notebooks/`에서 시계열 정렬, 상관 분석, 시각화를 진행합니다.

6. PDF 리포트 신호 생성

```bash
python src/report_signal_pipeline.py
```

7. 2023년 외 PDF 일반화 검증

```bash
python src/validate_pdf_generalization.py
```

현재 검증 세트는 `IEA Renewables 2022`, `IEA World Energy Outlook 2022`, `IEA Electricity 2024`입니다.
검증 결과는 `outputs/tables/pdf_generalization_validation.md`에 저장됩니다.

## PDF 업로드 MVP 실행

직접 PDF를 넣어서 분석 결과를 보고 싶으면 Streamlit 앱을 실행합니다.

```bash
streamlit run app_pdf_mvp.py
```

브라우저가 열리면 왼쪽 사이드바에서 PDF를 업로드하고 `PDF 분석 실행` 버튼을 누릅니다.

PowerShell에서 바로 실행하려면 아래 스크립트를 사용할 수 있습니다.

```powershell
.\run_pdf_mvp_local.ps1
```

`localhost`는 현재 컴퓨터에서만 접속되는 주소입니다. 같은 와이파이/LAN에 있는 다른 사람도 접속하게 하려면 아래 스크립트를 사용합니다.

```powershell
.\run_pdf_mvp_network.ps1
```

이 경우 터미널에 출력되는 `http://내_PC_IP:8501` 주소를 같은 네트워크의 다른 기기에서 열면 됩니다. Windows 방화벽이 막으면 Python 또는 포트 `8501` 허용이 필요합니다. 학교 밖이나 다른 네트워크의 사람이 접속하려면 Streamlit Community Cloud, Hugging Face Spaces, Render, ngrok 같은 배포/터널링 방식이 필요합니다.

## 공개 웹페이지로 배포

홈페이지 주소처럼 누구나 접속하게 하려면 로컬 실행이 아니라 클라우드 배포가 필요합니다.

배포용 엔트리포인트는 아래 파일입니다.

```text
streamlit_app.py
```

Streamlit Community Cloud에 배포할 때 main file path를 `streamlit_app.py`로 지정하면 됩니다.
자세한 절차는 `DEPLOYMENT.md`를 참고합니다.

앱에서 확인할 수 있는 것:

- 업로드 PDF의 재생에너지, 화석연료 압력, 전력망/전기화, 기후 리스크 점수
- 가장 강한 자산 힌트
- Foundation Model 기반 few-shot 점수 차트
- 주제별 근거 문단
- 보고서 날짜 이후 4주 수익률 연결 결과

## 핵심 산출물

- `data/processed/stock_returns_weekly.csv`
- `data/processed/climate_weekly_tai.csv`
- `data/processed/news_sentiment_weekly.csv`
- `data/processed/aligned_weekly_panel.csv`
- `outputs/tables/cross_corr_full.csv`
- `outputs/tables/rolling_corr_nss_adj_et_spread.csv`
- `outputs/tables/company_sensitivity_best_lags.csv`
- `outputs/tables/final_result_summary.md`
- `data/processed/reports/report_signals.csv`
- `data/processed/reports/report_stock_link.csv`
- `outputs/tables/report_signal_summary.md`
- `outputs/tables/pdf_generalization_validation.md`
- `outputs/figures/fig1_timeseries.png`
- `outputs/figures/fig2_lag_heatmap.png`
- `outputs/figures/fig3_rolling_corr.png`
- `outputs/figures/fig4_company_sensitivity.png`
- `outputs/figures/fig5_report_signals.png`
- `outputs/mvp_dashboard.html`
- `app_pdf_mvp.py`

## 현재 결론

- H1: TAI가 뉴스 감성보다 선행한다는 가설은 지지되지 않았습니다.
- H2: 뉴스 감성이 ICLN-XLE 스프레드를 양의 방향으로 움직인다는 가설은 지지되지 않았습니다.
- H3: 이벤트 기간별 관계 변화는 rolling correlation에서 부분적으로 관찰되지만, 인과나 예측으로 해석하지 않습니다.
- 기업 단위에서는 `NSS_ADJ -> XOM`, `NSS_ADJ -> ETN`에서 약한 유의 상관이 관찰되었습니다.
- PDF 리포트 파이프라인은 `PDF -> Text -> Evidence Retrieval -> Few-shot Scoring -> Stock Link`까지 구현되었습니다.

자세한 해석은 `outputs/tables/final_result_summary.md`와 `project_guideline.md`의 최종 완료 섹션을 참고합니다.
