# Project Quality Audit

## 냉정한 평가

학부 딥러닝/Foundation Model 프로젝트 기준으로 보면 현재 결과물은 단순 구현 과제보다 높은 편입니다. PDF 업로드 앱, 텍스트 추출, 사전학습 임베딩, few-shot classifier head, Gemini 요약, 뉴스/주가 downstream 연결, 배포까지 갖췄기 때문입니다.

다만 부실해 보일 수 있는 지점도 있습니다. 검증 표본이 아직 크지 않고, 에너지 보고서는 재생에너지·화석연료·전력망·정책 전환 내용이 한 문서에 섞이는 경우가 많아 단일 라벨 평가가 완벽하지 않습니다.

## 보완 완료한 핵심 문제

| Issue | Why It Looked Weak | Fix |
|---|---|---|
| 검증 표본 부족 | 15개 PDF만으로는 일반화 검증처럼 보이기 어려웠음 | 공개 PDF를 10개 추가해 25개로 확장 |
| 쉬운 사례 편향 | IRENA/IEA 단일 테마 보고서가 많았음 | EV, 태양광 공급망, 배터리, EIA 전력 연감, ExxonMobil, IPCC 완화 보고서 추가 |
| Foundation model 실험성 부족 | 앱 기능은 보이지만 zero-shot 대비 개선 근거가 약했음 | zero-shot embedding baseline 10/25 vs few-shot head 18/25 비교 추가 |
| 실패 사례 은폐 위험 | 높은 정확도만 말하면 과장으로 보일 수 있음 | 오분류 7건의 원인 분석을 별도 CSV와 앱 표로 공개 |
| 뉴스 데이터 과장 위험 | 실제 GDELT지만 전체 뉴스가 아니라 weekly one-file sample | README, 앱, 보고서에 예비 분석/표본 한계 문구 유지 |
| OOD 안정성 부족 | 비에너지 PDF도 climate-risk로 끌려갈 수 있음 | WHO/OECD 음성 대조군 결과 공개 |

## 현재 성능을 발표할 때의 안전한 문장

> 같은 25개 PDF에서 zero-shot embedding similarity는 10개, few-shot classifier head는 18개의 기대 방향과 일치했습니다. 이는 범용 사전학습 임베딩 위에 소수 예시 기반 downstream head를 얹었을 때 도메인 분류가 개선되는 예비 결과입니다.

## 아직 남은 약점

- 검증 PDF가 25개라서 엄밀한 통계 평가에는 아직 작습니다.
- 라벨이 사람이 정한 기대 방향이므로 gold label의 객관성이 제한됩니다.
- 복합 주제 문서는 단일 라벨로 평가하기 어렵습니다.
- Gemini 요약은 생성형 모델 출력이므로 근거 문단과 함께 확인해야 합니다.
- 뉴스-주가 연결은 상관관계이며 인과 또는 예측이 아닙니다.

## 학부 프로젝트 관점 최종 판단

현재 상태는 학부 프로젝트로는 충분히 제출 가능한 수준입니다. Foundation Model 과제에서 중요한 `범용 모델 사용`, `downstream task`, `few-shot adaptation`, `모델 연결`, `MVP 배포`가 모두 들어 있습니다.

다만 발표에서는 성능을 과장하지 말고 실패 사례와 한계를 먼저 인정해야 합니다. 그렇게 하면 오히려 프로젝트가 더 성숙해 보입니다.
