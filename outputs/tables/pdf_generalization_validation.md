# Expanded PDF Validation

## 목적

핵심 분석 PDF 5개 외에 공개 PDF 50개를 추가로 사용해, PDF topic salience 파이프라인이 dominant reference theme과 얼마나 일치하는지 점검했습니다.

## 방법

1. PDF에서 텍스트를 추출했습니다.
2. 에너지 전환 관련 근거 문단을 검색했습니다.
3. MiniLM 임베딩을 생성했습니다.
4. 소수 라벨 예시로 학습한 Logistic Regression linear probe가 문단을 주제별로 점수화했습니다.
5. 사람이 사전에 정한 dominant reference theme과 모델의 top theme-linked sector context를 비교했습니다.

## 결과 요약

| 항목 | 값 |
|---|---:|
| 검증 PDF | 50 |
| Dominant theme 일치 | 36 |
| Accuracy | 0.72 |
| Macro-F1 | 0.658 |
| Zero-shot 일치 | 17/50 |
| Few-shot 일치 | 36/50 |

## 해석

Small-sample supervised logistic head는 zero-shot similarity baseline보다 더 많은 PDF에서 dominant reference theme과 일치했습니다. 다만 이 결과는 소규모 예비 검증이며, 복합 주제 보고서에서는 단일 라벨 평가가 애매할 수 있습니다.

## 주의

이 검증은 정량 일반화 성능 평가가 아니라 MVP 수준의 dominant-theme alignment 점검입니다. 발표에서는 “50개 공개 PDF에서 supervised linear probe가 36개 dominant reference theme과 일치했다” 정도로 설명하는 것이 안전합니다.
