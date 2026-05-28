# Public Web Deployment Guide

이 문서는 PDF 업로드 MVP를 `localhost`가 아니라 누구나 접속 가능한 웹주소로 배포하는 방법을 정리합니다.

## 결론

`localhost`는 내 컴퓨터 전용 주소입니다. 홈페이지 주소처럼 누구나 접속하게 하려면 앱을 클라우드 서버에 올려야 합니다.

추천 방식:

1. GitHub에 프로젝트 업로드
2. Streamlit Community Cloud에서 GitHub 저장소 연결
3. 메인 파일을 `streamlit_app.py`로 지정
4. 배포 후 생성되는 `https://...streamlit.app` 주소 공유

## 배포 전 파일 구성

필수 파일:

```text
streamlit_app.py
app_pdf_mvp.py
requirements.txt
src/
.streamlit/config.toml
```

주의:

- `data/raw/reports/*.pdf` 같은 원본 PDF는 용량이 커서 GitHub에 올리지 않는 편이 좋습니다.
- 이 앱은 사용자가 PDF를 업로드하면 분석하므로 기존 원본 PDF가 없어도 실행됩니다.
- 주가 연결 파일이 없으면 PDF 점수화와 요약은 동작하고, 4주 수익률 연결만 표시되지 않을 수 있습니다.

## Streamlit Community Cloud 배포 순서

1. GitHub에 새 저장소를 만듭니다.
2. 이 프로젝트 파일을 GitHub에 push합니다.
3. Streamlit Community Cloud에 로그인합니다.
4. `Create app` 또는 `New app`을 선택합니다.
5. GitHub 저장소를 선택합니다.
6. Main file path를 아래처럼 입력합니다.

```text
streamlit_app.py
```

7. Deploy를 누릅니다.
8. 배포가 끝나면 `https://앱이름.streamlit.app` 형태의 주소가 생성됩니다.

## 배포 후 사용 방법

사용자는 웹주소에 접속해서 다음 순서로 사용합니다.

1. PDF 업로드
2. 보고서 제목, 발행 기관, 기준일 입력
3. `PDF 분석 실행` 클릭
4. 주제 점수, 모델 확신도, 근거 문단, 요약, 시장 연결 결과 확인
5. 필요하면 점수 CSV와 근거 문단 CSV 다운로드

## 예상 이슈

| 문제 | 원인 | 해결 |
|---|---|---|
| 첫 실행이 느림 | Hugging Face 모델 다운로드 | 첫 실행 후에는 캐시되어 빨라짐 |
| 메모리 부족 | `torch`, `transformers` 모델 로딩 | 더 작은 모델 사용 또는 유료/더 큰 서버 사용 |
| PDF가 너무 큼 | 업로드 제한 또는 처리 시간 증가 | 앱에서 분석 페이지 수를 줄임 |
| 4주 수익률이 안 나옴 | 주가 CSV가 없거나 날짜 범위 밖 | PDF 점수화 결과 중심으로 해석 |
| 외부 접속 불가 | 로컬에서만 실행 중 | Streamlit Cloud, Hugging Face Spaces, Render, ngrok 사용 |

## 대안 배포 방법

| 방식 | 장점 | 단점 |
|---|---|---|
| Streamlit Community Cloud | Streamlit 앱 배포가 가장 간단함 | GitHub 공개/연동 필요 |
| Hugging Face Spaces | AI 데모 배포에 적합 | 설정이 약간 더 필요 |
| Render | 일반 웹서비스처럼 배포 가능 | 무료 인스턴스는 느릴 수 있음 |
| ngrok | 로컬 앱을 임시 공개 가능 | 임시 주소이며 장기 운영에는 부적합 |

## 발표용 설명

> 기존에는 `localhost`에서만 동작하는 로컬 MVP였지만, Streamlit Cloud에 배포하면 사용자가 웹주소만 입력해서 PDF를 업로드하고 Foundation Model 기반 분석 결과를 확인할 수 있는 웹앱 형태가 됩니다.
