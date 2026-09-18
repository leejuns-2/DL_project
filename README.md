---
title: Energy Report-to-Market Signal Analyzer
emoji: ⚡
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
app_port: 7860
---

# Energy Report-to-Market Signal Analyzer

에너지·기후 관련 PDF에서 근거 문단을 검색하고, 문서의 주요 테마를 분류한 뒤
Gemini를 이용해 근거 기반 요약을 생성하는 분석 파이프라인입니다.

단순한 문서 요약보다 **어떤 근거를 바탕으로 어떤 테마가 탐지되었는지 확인할 수 있는 구조**를 만드는 것을 목표로 했습니다.

> This project is a course project developed with generative AI coding assistance.
> I focused on experiment execution, result analysis, debugging, evaluation refinement, and iterative improvement.

---

## Project Context

- Course: Deep Learning
- Type: Individual project
- Domain: Energy / Climate documents
- Main tasks:
  - Evidence retrieval
  - Theme classification
  - Evidence-grounded summarization
  - Development-set evaluation

---

## Key Result

공개 PDF 50개로 구성한 **development catalog**에서
zero-shot embedding similarity와 supervised linear probe를 비교했습니다.

| Method | Dominant-theme top-1 alignment |
|---|---:|
| Zero-shot embedding similarity | 17/50 (34%) |
| Supervised linear probe | 36/50 (72%) |

Supervised linear probe가 development catalog 기준으로
dominant-theme top-1 alignment를 **34%에서 72%로 개선**했습니다.

다만 이 결과는 독립적인 held-out benchmark가 아니라
개발 과정에서 사용한 소규모 development set의 결과입니다.

---

## My Contribution

이 프로젝트에서 중점적으로 수행한 작업은 다음과 같습니다.

- 전체 report analysis pipeline의 구성과 실행
- retrieval 및 theme classification 결과 비교
- zero-shot 방식과 supervised linear probe 실험
- 실험 결과와 failure case 분석
- OOD 및 mixed-theme 사례 점검
- Gemini 기반 evidence-grounded summary 연결
- 오류 수정과 evaluation 방식 개선
- 결과의 해석 범위와 한계 정리

구현 과정에서는 **generative AI coding tools를 보조적으로 활용**했습니다.

AI가 생성한 코드를 그대로 사용하는 것보다,
직접 실행하고 결과를 확인하면서 오류를 수정하고,
평가 방식과 실험 조건을 반복적으로 조정하는 데 집중했습니다.

---

## Pipeline

```text
PDF
  ↓
Text Extraction
  ↓
Evidence Retrieval
  ↓
MiniLM Embedding
  ↓
Theme Classification
  ↓
Mixed-theme / OOD Checks
  ↓
Evidence-grounded Gemini Summary
  ↓
News & Historical Market Context
