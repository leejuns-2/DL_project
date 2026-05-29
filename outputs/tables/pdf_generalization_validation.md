# Expanded PDF Validation

## 목적

핵심 분석 PDF 5개 외에 서로 성격이 다른 PDF를 추가로 넣었을 때 few-shot PDF 신호화가 기대 방향으로 작동하는지 점검했습니다.

## 방법

- PDF에서 텍스트를 추출했습니다.
- 에너지 전환 관련 근거 문단을 검색했습니다.
- MiniLM 임베딩을 만들었습니다.
- 소수 라벨 예시로 학습한 Logistic Regression 분류 헤드가 문단을 주제별로 점수화했습니다.
- 사람이 사전에 정한 기대 방향과 모델의 `asset_hint`를 비교했습니다.

## 결과 요약

| 항목 | 값 |
|---|---:|
| 추가 검증 PDF | 8 |
| 기대 방향과 일치 | 8 |
| 해석 | 소규모 MVP 검증 |

## 검증 결과

| report_id | expected_hint | predicted_hint | matched |
|---|---|---|---|
| irena_global_renewables_outlook_2020 | ICLN/NEE | ICLN/NEE | True |
| irena_renewable_energy_statistics_2020 | ICLN/NEE | ICLN/NEE | True |
| irena_renewable_power_costs_2022 | ICLN/NEE | ICLN/NEE | True |
| irena_world_energy_transitions_2023 | ICLN/NEE | ICLN/NEE | True |
| irena_renewable_energy_statistics_2024 | ICLN/NEE | ICLN/NEE | True |
| nextera_annual_2023 | ETN | ETN | True |
| siemens_energy_annual_2023 | ETN | ETN | True |
| ipcc_ar6_synthesis | Climate risk | Climate risk | True |

## 주의

이 결과는 소규모 검증입니다. 표본 수가 적고 라벨 정의가 사람이 정한 기준에 의존하므로, “정확도 100%”가 아니라 “추가 샘플에서 기대 방향과 일치했다”로 설명해야 합니다.
