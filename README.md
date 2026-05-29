---
title: PDF Report-to-Market Signal
emoji: 📄
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
app_port: 7860
---

# PDF Report-to-Market Signal

에너지·기후 보고서 PDF를 Foundation Model 기반 파이프라인으로 분석해 시장 신호를 생성하는 웹 애플리케이션입니다.

## 기능

- **PDF 업로드 분석**: 에너지 보고서를 업로드하면 4가지 주제 점수(재생에너지, 화석연료 압력, 전력망/전기화, 기후 리스크)를 즉시 산출
- **Few-shot 학습**: `sentence-transformers/all-MiniLM-L6-v2` 임베딩 모델로 사람이 작성한 예시 문장과 의미 유사도 비교
- **주가 연결**: 보고서 날짜 전후 ICLN·XLE·NEE·XOM·ETN 수익률 연결
- **프로젝트 대시보드**: 기존 분석 결과(5개 리포트), 가설 검증, 분석 그래프 5개 제공

## 사용 모델

| 모델 | 역할 |
|---|---|
| `ProsusAI/finbert` | 뉴스 헤드라인 감성 분류 |
| `sentence-transformers/all-MiniLM-L6-v2` | PDF 문단 few-shot 점수화 |

## 로컬 실행

```bash
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

브라우저에서 `http://localhost:8000` 접속

## Hugging Face Spaces 배포

1. HuggingFace에서 새 Space 생성 (SDK: Docker)
2. 이 저장소를 연결하거나 파일 업로드
3. Space가 자동 빌드 후 `https://huggingface.co/spaces/{username}/{space-name}` 접속

## 파이프라인

```
PDF 업로드
  → 텍스트 추출 (PyMuPDF)
  → 에너지 전환 관련 문단 검색 (TF-IDF)
  → MiniLM-L6-v2 임베딩
  → Few-shot 주제 점수화
  → 보고서 날짜 전후 ETF·기업 수익률 연결
```

## 핵심 결론

| 가설 | 결과 |
|---|---|
| H1: TAI → 뉴스 감성 선행 | 기각 (r=−0.12, p=0.236) |
| H2: NSS_ADJ → ET_SPREAD 양의 방향 | 기각 (r=−0.19, p=0.062) |
| H3: 이벤트 기간 관계 강화 | 부분 관찰 (기술적) |
| NSS_ADJ → XOM (lag+4) | r=0.216, **p=0.033** |
| NSS_ADJ → ETN (lag+3) | r=0.200, **p=0.048** |
