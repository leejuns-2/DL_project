# Project Quality Audit

## 평가 요약

현재 프로젝트는 단순 PDF 요약 과제를 넘어, 에너지/기후 보고서를 정량 신호로 바꾸고 웹에서 테스트할 수 있는 연구용 MVP 수준까지 올라와 있습니다. PDF 업로드, 텍스트 추출, 근거 검색, MiniLM 임베딩, few-shot classifier head, 생성 요약, 뉴스/주가 downstream 연결, Hugging Face 배포가 모두 연결되어 있습니다.

다만 완성도를 높게 보이게 하려면 좋은 결과만 보여주면 안 됩니다. 검증 표본의 크기, 복합 주제 문서의 실패 사례, OOD 한계, 생성 요약 검토 결과를 같이 제시해야 합니다.

## 보완 완료 항목

| Issue | Why It Looked Weak | Fix |
|---|---|---|
| 검증 표본 부족 | 소수 PDF만으로는 일반화 검증처럼 보이기 어려웠음 | 공개 PDF 25개 검증셋과 label rationale 정리 |
| Baseline 부재 | foundation model을 썼다는 설명은 있지만 개선 근거가 약했음 | zero-shot embedding baseline과 few-shot head 비교 추가 |
| 실패 사례 은폐 위험 | 정확도만 말하면 과장처럼 보일 수 있음 | 오분류 7건의 원인 해석 CSV와 문서화 추가 |
| OOD 안정성 부족 | 비에너지 PDF도 기후 리스크로 흡수될 수 있음 | WHO/OECD 음성 대조군 결과 공개 및 energy relevance/OOD guard 추가 |
| PDF 근거 품질 | WEO 같은 긴 PDF에서 목차 문단이 근거로 잡힐 수 있었음 | 점선 리더/목차 패턴이 많은 저정보 문단 필터링 추가 |
| 뉴스 데이터 과장 위험 | 실제 GDELT지만 전체 뉴스가 아니라 weekly one-file sample | README와 결과 문서에 표본 한계 문구 유지 |
| 생성 요약 검증 부족 | Gemini 요약이 근거와 맞는지 별도 확인이 필요했음 | 표본 5개 human check CSV 유지 |

## 현재 성능을 설명하는 안전한 문장

> 같은 25개 PDF에서 zero-shot embedding similarity는 10개, few-shot classifier head는 18개의 기대 방향과 일치했습니다. 이는 범용 사전학습 임베딩 위에 소수 예시 기반 downstream head를 얹었을 때 도메인 분류가 개선되는 예비 결과입니다.

## 남은 약점

- 검증 PDF가 25개라 엄밀한 통계 일반화 평가로는 작습니다.
- 하나의 PDF 안에 재생에너지, 화석연료, 전력망, 기후 리스크가 섞인 경우 단일 라벨 평가가 불안정합니다.
- WHO 보건 문서처럼 climate-health 표현이 많은 OOD 문서는 기후 리스크로 일부 흡수될 수 있습니다.
- Gemini 요약은 생성형 출력이므로 항상 근거 문단과 함께 확인해야 합니다.
- 뉴스-주가 연결은 상관/이벤트 관찰이며 인과관계나 투자 예측이 아닙니다.

## 최종 판단

수업/졸업 프로젝트 관점에서는 제출 가능한 완성도입니다. 특히 `PDF -> 근거 문단 -> foundation embedding -> few-shot signal -> downstream market context -> web MVP` 흐름이 명확합니다.

발표에서는 성능을 과장하지 말고, 실패 사례와 한계를 먼저 인정하는 방식이 가장 설득력 있습니다. 이 프로젝트의 강점은 완벽한 예측 정확도가 아니라, 비정형 PDF를 재현 가능한 분석 신호로 바꾸는 전체 파이프라인을 구현했다는 점입니다.
