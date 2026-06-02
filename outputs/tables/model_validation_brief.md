# Model Validation Brief

## 목적

이 문서는 에너지/기후 PDF 분석 모델을 발표 또는 제출용 결과로 해석할 때 필요한 검증 요약입니다. 단순 정확도만 제시하지 않고, baseline 비교, 실패 사례, OOD 한계, mixed-signal 문서, 생성형 요약 검증을 함께 공개합니다.

## 한줄 평가

현재 모델은 연구용 MVP로는 동작하지만, 검증 PDF 25개는 통계적 일반화 평가로 보기에는 작습니다. 따라서 현재 수치는 pilot evaluation으로만 해석하고, 문단 단위 multi-label 평가셋과 OOD 전용 평가를 확장해야 합니다.

## 핵심 지표

| 항목 | 값 | 해석 |
|---|---:|---|
| 검증 PDF 수 | 25 | 공개 PDF 기반 소규모 pilot 검증셋 |
| 기대 방향 일치 | 18 / 25 | 사람이 정한 자산/테마 방향과 모델 판정 비교 |
| Accuracy | 72.0% | 단일 라벨 기준의 참고값 |
| Macro-F1 | 0.675 | 라벨 불균형 영향을 줄인 평균 F1 |
| Zero-shot baseline | 40.0% | MiniLM 임베딩 유사도만 사용한 기준선 |
| Few-shot head | 72.0% | 고정 MiniLM 임베딩 위 logistic head 사용 |
| Chunk weak labels | 0 | 문단 단위 multi-label 확장용 약지도 테이블 |
| Mixed chunks | 0 | 복합 문단으로 검토해야 할 chunk 수 |

## 개선된 판정 기준

| 검증 포인트 | 통과 기준 | 현재 판정 |
|---|---|---|
| 기능 정상성 | PDF 업로드, 근거 검색, 점수 산출, 과거 수익률 연결까지 실행 | 통과 |
| Baseline 대비 개선 | zero-shot보다 few-shot head가 명확히 좋아야 함 | 통과 |
| 근거 정합성 | 요약과 점수에 evidence chunk ID가 붙어야 함 | 개선됨 |
| OOD 방어 | 비에너지 PDF가 강한 시장 신호로 오인되지 않아야 함 | 부분 통과, climate-health는 review 필요 |
| 복합 주제 처리 | 하나의 PDF 안의 여러 테마를 mixed-signal로 드러내야 함 | 개선됨 |
| Chunk multi-label | PDF 단일 라벨 외 문단 단위 라벨 테이블이 있어야 함 | 추가됨 |
| 생성형 요약 안전성 | Gemini 요약은 근거 문단과 함께 확인되어야 함 | 개선됨 |

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

주요 실패 원인은 모델이 완전히 틀렸다기보다 하나의 PDF 안에 재생에너지, 화석연료 전환, 전력망, 기후 리스크 표현이 함께 들어가는 경우가 많다는 점입니다. 이 경우 단일 라벨 정답으로만 평가하면 오류처럼 보이므로, 문서 단위 mixed-signal과 문단 단위 multi-label 결과를 함께 제시해야 합니다.

## OOD 점검

| 문서 | 상위 테마 | 마진 | 판정 | 해석 |
| --- | --- | --- | --- | --- |
| WHO World Health Statistics 2023 | climate_risk | 0.629 | false_positive_domain_overlap | Health/education PDF tested as negative control; high climate risk on WHO shows climate-health domain overlap. |
| OECD Education at a Glance 2023 | climate_risk | 0.019 | reject_low_confidence | Low score margin indicates the classifier does not confidently map this education PDF to one market theme. |

WHO 보건 문서처럼 climate-health 표현이 많은 OOD 문서는 climate risk와 겹칠 수 있습니다. 이번 수정에서는 OOD subtype을 추가해 `climate_health_overlap`은 자동 확정 대신 review 대상으로 표시할 수 있게 했습니다.

## 생성형 요약 검증

- Gemini 표본 검토 pass 4, review 1
- 주요 체크 기준: 요약 문장이 evidence chunk와 맞는지, 투자 추천이나 미래 수익률 예측처럼 들리지 않는지, 과장된 인과 표현이 없는지 확인합니다.
- API 응답에는 `evidence_chunk_ids`, `support_level`, `support_note`를 붙여 생성형 출력만 단독으로 보지 않게 했습니다.

## 라이브 테스트 기록

_No rows available._

## 완성도 판단

현재 완성도는 연구 프로젝트 기준으로는 충분히 설명 가능한 수준입니다. 다만 일반화 성능 주장에는 아직 이르며, 남은 핵심 보완은 100개 이상 PDF 확장, 사람이 검수한 chunk multi-label 평가셋, climate-health/OOD 전용 negative set입니다.

## 발표용 안전 문장

> 이 시스템은 PDF를 넣으면 미래 수익률을 예측하는 도구가 아닙니다. 에너지/기후 보고서의 근거 문단을 few-shot topic signal로 변환하고, 뉴스 컨텍스트 및 과거 주가 반응과 연결해 탐색하는 연구용 MVP입니다.
