# PDF Generalization Validation

## 목적

2023년 리포트가 아닌 자료를 넣었을 때도 example-based PDF 신호화가 기대한 방향으로 작동하는지 확인했습니다.

## 검증 기준

- 사람이 보고 기대 라벨을 먼저 정했습니다.
- 모델이 예측한 `asset_hint`가 기대 라벨과 같으면 맞은 것으로 계산했습니다.
- 표본 수가 작으므로 이 값은 엄밀한 모델 정확도가 아니라 MVP 일반화 점검용 정확도입니다.

소규모 일반화 점검: `3 / 3` 일치

## 결과

| title                         | expected_asset_hint   | asset_hint   | asset_hint_correct   | top_theme             |   top_theme_score |   score_margin |   pages_extracted |   paragraphs_extracted |
|:------------------------------|:----------------------|:-------------|:---------------------|:----------------------|------------------:|---------------:|------------------:|-----------------------:|
| IEA World Energy Outlook 2022 | ICLN/NEE              | ICLN/NEE     | True                 | renewable_opportunity |          0.736141 |      0.0193718 |                96 |                    521 |
| IEA Renewables 2022           | ICLN/NEE              | ICLN/NEE     | True                 | renewable_opportunity |          0.740621 |      0.0152172 |               100 |                    556 |
| IEA Electricity 2024          | ETN                   | ETN          | True                 | grid_infrastructure   |          0.731048 |      0.0113052 |               100 |                    548 |

## 해석

- 기대 라벨과 맞으면, 기존 2023년 보고서가 아닌 자료에서도 주제 신호가 같은 방향으로 나온 것입니다.
- 틀린 항목은 모델 오류일 수도 있지만, 보고서가 여러 주제를 동시에 다루기 때문일 수도 있습니다.
- `score_margin`이 작으면 1등 주제와 2등 주제 차이가 작다는 뜻이라 확신도가 낮은 결과로 봐야 합니다.
