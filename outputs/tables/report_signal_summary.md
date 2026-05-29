# Report-to-Market Signal Summary

## 쉬운 설명

PDF 보고서를 단순히 요약하는 데서 끝내지 않고, 보고서 안의 에너지 전환 관련 근거 문단을 찾은 뒤 숫자 신호로 변환했습니다.  
쉽게 말하면 긴 보고서를 읽어서 `재생에너지`, `화석연료 전환 압력`, `전력망`, `기후 리스크` 점수표로 만든 것입니다.

## Foundation Model 연결

- 임베딩 모델: `sentence-transformers/all-MiniLM-L6-v2`
- Few-shot learning: MiniLM 본체는 고정하고, 소수 라벨 예시로 Logistic Regression 분류 헤드를 학습
- 생성형 모델: `gemini-3.5-flash`
- Downstream task: PDF 신호를 뉴스 컨텍스트 및 과거 주가 수익률과 연결

## 핵심 보고서 신호

| report_id | asset_hint | 해석 |
|---|---|---|
| exxon_acs_2023 | XLE/XOM transition pressure | 화석연료 기업의 전환 압력과 기후 대응 내용이 강함 |
| iea_weo_2023 | ICLN/NEE | 재생에너지와 전력 시스템 전환 신호가 강함 |
| iea_oil_gas_nz_2023 | XLE/XOM transition pressure | 석유·가스 산업의 net-zero 전환 압력 신호가 강함 |
| iea_renewables_2023 | ICLN/NEE | 재생에너지 성장 기회 신호가 강함 |
| eaton_annual_2023 | ETN | 전력망, 전기화, power management 관련 신호가 강함 |

## 뉴스 연결

`report_news_bridge.csv`는 각 보고서 날짜 이전 4주 뉴스 컨텍스트의 평균 감성과 추세를 연결합니다. 현재 포함된 뉴스 CSV는 대량 원자료 전체가 아니라, 보고서 날짜 주변 연결을 보여주기 위한 sample weekly context입니다.

## 해석 주의

- 이 결과는 미래 수익률 예측이 아닙니다.
- 포트폴리오 시뮬레이터는 과거 수익률 기반 시나리오 계산기입니다.
- Gemini 요약은 근거 문단을 바탕으로 생성되며, 반드시 원문 근거와 함께 해석해야 합니다.
- PDF 검증 8/8은 소규모 MVP 검증이지 일반화 정확도 100%가 아닙니다.
