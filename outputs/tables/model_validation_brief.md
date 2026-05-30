# Model Validation Brief

## 목적

이 문서는 프로젝트 결과를 발표하거나 제출할 때 모델이 어느 정도 신뢰 가능한지 판단하기 위한 검증 요약입니다. 핵심은 높은 점수만 보여주는 것이 아니라, baseline 대비 개선, 실패 사례, OOD 한계, 생성 요약 검토를 함께 공개하는 것입니다.

## 한 줄 평가

현재 모델은 에너지/기후 PDF를 시장 분석용 주제 신호로 바꾸는 연구용 MVP로는 충분히 작동합니다. 다만 표본 규모가 작고 복합 주제 문서는 단일 라벨 평가가 어려우므로, 일반화 성능이나 투자 예측 성능으로 과장하면 안 됩니다.

## 핵심 지표

| 항목 | 값 | 해석 |
|---|---:|---|
| 검증 PDF 수 | 25 | 공개 에너지/기후 PDF 기반 소규모 검증셋 |
| 기대 방향 일치 | 18 / 25 | 사람이 정한 대표 자산/테마 방향과 모델 판정 비교 |
| Accuracy | 72.0% | 전체 표본 중 단일 라벨 일치율 |
| Macro-F1 | 0.675 | 라벨 불균형을 줄여 본 평균 F1 |
| Zero-shot baseline | 40.0% | MiniLM 임베딩 유사도만 사용한 기준선 |
| Few-shot head | 72.0% | 고정 MiniLM 임베딩 위 logistic head 사용 |

## 판단 기준

| 검토 포인트 | 통과 기준 | 현재 판단 |
|---|---|---|
| 기능 정상성 | PDF 업로드, 근거 검색, 점수 산출, 수익률 연결이 끝까지 실행됨 | 통과 |
| Baseline 대비 개선 | zero-shot보다 few-shot head가 명확히 좋아야 함 | 통과 |
| 근거 정합성 | 상위 근거 문단이 실제 테마 내용을 포함해야 함 | 대체로 통과, 목차 문단 필터 추가 완료 |
| OOD 방어 | 비에너지 PDF가 강한 투자 신호로 오인되지 않아야 함 | 부분 통과, climate-health overlap은 한계 |
| 생성 요약 안전성 | 근거 기반 요약이며 투자 추천/수익률 예측을 하지 않아야 함 | 부분 통과, 스타일 리뷰 필요 |
| 연구 설명 가능성 | 모델 구조, 데이터 한계, 실패 사례를 문서화해야 함 | 통과 |

## 실패 사례 해석

| 문서 | 기대 | 예측 | 해석 |
| --- | --- | --- | --- |
| NextEra Energy Annual Report 2023 | ETN | XLE/XOM transition pressure | utility annual report contains broad clean-energy and fossil/transition language; model maps it to fossil pressure rather than grid/electrification |
| IEA World Energy Outlook 2022 | ICLN/NEE | XLE/XOM transition pressure | broad world energy outlook mixes renewables, fossil fuels, grids, and policy; single-label expectation is too coarse |
| IEA Coal 2023 | XLE/XOM transition pressure | ICLN/NEE | coal report has transition and clean-energy terms around phase-down; model under-weights fossil-specific context |
| IEA Global EV Outlook 2023 | ICLN/NEE | ETN | mixed-theme or label ambiguity |
| IEA Batteries and Secure Energy Transitions 2024 | ETN | ICLN/NEE | battery reports mix clean-energy opportunity and grid/storage infrastructure, making the single ETN label ambiguous |
| ExxonMobil Advancing Climate Solutions 2024 | Climate risk | XLE/XOM transition pressure | mixed-theme or label ambiguity |
| ExxonMobil Advancing Climate Solutions 2025 | Climate risk | XLE/XOM transition pressure | mixed-theme or label ambiguity |

실패 사례의 공통 원인은 모델이 완전히 틀렸다기보다, 하나의 PDF 안에 재생에너지, 화석연료 전환, 전력망, 기후 리스크 표현이 같이 들어 있는 경우가 많다는 점입니다. 따라서 발표에서는 단일 라벨 분류기라기보다 복합 보고서를 시장 신호로 요약하는 도구라고 설명하는 것이 안전합니다.

## OOD 점검

| 문서 | 상위 테마 | 마진 | 판정 | 해석 |
| --- | --- | --- | --- | --- |
| WHO World Health Statistics 2023 | climate_risk | 0.629 | false_positive_domain_overlap | Health/education PDF tested as negative control; high climate risk on WHO shows climate-health domain overlap. |
| OECD Education at a Glance 2023 | climate_risk | 0.019 | reject_low_confidence | Low score margin indicates the classifier does not confidently map this education PDF to one market theme. |

OOD 결과는 비에너지 문서에서도 climate-risk 표현이 있으면 일부 흡수될 수 있음을 보여줍니다. 현재는 energy relevance와 score margin을 함께 보고 낮은 확신 또는 도메인 중복을 설명하는 방식이 적절합니다.

## 생성 요약 검토

- Gemini 표본 검토: pass 4, review 1
- 주요 체크 기준: 근거 문단과 요약의 주제 일치, 투자 추천/수익률 예측 문구 부재, 과장된 인과 표현 부재
- 발표 시 요약문만 단독으로 보여주지 말고 근거 문단과 함께 보여주는 것이 안전합니다.

## 라이브 웹 테스트 기록

| 응답 파일 | 자산 신호 | 상위 테마 | 확신도 | 에너지 관련성 | OOD | 캐시 |
| --- | --- | --- | --- | --- | --- | --- |
| test_oilgas_response.json | XLE/XOM transition pressure | fossil_pressure | 높음 | 0.9832 | in_domain | False |
| test_renewables_response.json | ICLN/NEE | renewable_opportunity | 높음 | 1.0 | in_domain | False |
| test_weo_response.json | ICLN/NEE | renewable_opportunity | 보통 | 0.9707 | in_domain | False |
| test_weo_response_after_fix.json | ICLN/NEE | renewable_opportunity | 보통 | 0.9707 | in_domain | True |
| test_weo_response_after_fix_live.json | XLE/XOM transition pressure | fossil_pressure | 낮음 | 0.9739 | in_domain | False |
| test_weo_response_after_fix_retry.json | ICLN/NEE | renewable_opportunity | 보통 | 0.9707 | in_domain | True |

## 완성도 판단

현재 완성도는 연구 프로젝트 기준 약 80점 수준으로 평가할 수 있습니다. 기능 흐름과 배포, baseline 비교, 실패 분석은 갖췄고, 남은 보완은 더 큰 라벨 데이터셋, 복합 주제 판정, OOD 전용 classifier입니다.

## 발표용 안전 문장

> 이 시스템은 PDF를 넣으면 미래 수익률을 예측하는 도구가 아니라, 에너지/기후 보고서의 근거 문단을 few-shot topic signal로 변환하고 뉴스 컨텍스트 및 과거 주가 반응과 연결해 분석하는 연구용 MVP입니다.
