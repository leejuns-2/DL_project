# Expanded PDF Validation

## 목적

핵심 분석 PDF 5개 외에 공개 PDF 25개를 추가로 사용해, PDF 신호화 파이프라인이 기대한 시장 테마 방향과 얼마나 일치하는지 점검했습니다.

## 방법

1. PDF에서 텍스트를 추출했습니다.
2. 에너지 전환 관련 근거 문단을 검색했습니다.
3. MiniLM 임베딩을 생성했습니다.
4. 소수 라벨 예시로 학습한 Logistic Regression classifier head가 문단을 주제별로 점수화했습니다.
5. 사람이 사전에 정한 기대 방향과 모델의 `asset_hint`를 비교했습니다.

## 결과 요약

| 항목 | 값 |
|---|---:|
| 검증 PDF | 25 |
| 기대 방향과 일치 | 18 |
| Accuracy | 0.72 |
| Macro-F1 | 0.675 |
| Zero-shot 일치 | 10/25 |
| Few-shot 일치 | 18/25 |

## 해석

few-shot classifier head는 zero-shot embedding similarity보다 더 많은 PDF에서 기대 방향과 일치했습니다. 다만 이 결과는 소규모 예비 검증이며, 복합 주제 보고서에서는 단일 라벨 평가가 애매할 수 있습니다.

## 주의

이 검증은 정량 일반화 성능 평가가 아니라 MVP 수준의 방향성 점검입니다. 발표에서는 “25개 공개 PDF에서 few-shot 방식이 18개 기대 방향과 일치했다” 정도로 설명하는 것이 안전합니다.
