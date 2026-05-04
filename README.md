# Seoul Mouse's Guide 🐭🧀

> 서울의 동네별 패션 코디를 추천해주는 AI 챗봇 웹 애플리케이션

시골에서 올라온 **시골쥐**를 위해 힙한 **서울쥐** 캐릭터가 동네 분위기에 맞는 옷차림을 알려줍니다.

🔗 **[choibigo.github.io/fashion_ai](https://choibigo.github.io/fashion_ai)**

---

## 주요 기능

- **인터랙티브 서울 지도**: Leaflet.js 기반으로 서울 주요 동네 13곳이 마커로 표시되며, 클릭하면 해당 동네 코디 추천이 시작됩니다.
- **AI 패션 챗봇**: Google Gemini API(`gemini-2.5-flash-lite`)를 활용해 동네별 맞춤 코디를 대화형으로 추천합니다.
- **AI 이미지 생성**: Gemini 이미지 모델(`gemini-2.5-flash-image`)로 추천 코디를 패션 화보 스타일 이미지로 생성합니다.
- **성별 맞춤 추천**: 남성/여성 토글 스위치로 성별에 맞는 패션 아이템을 추천합니다.
- **대화 히스토리 유지**: 멀티턴 대화를 지원하며 `/reset` API로 초기화할 수 있습니다.

---

## 지원 동네

성수동, 한남동, 홍대, 압구정, 청담, 이태원, 여의도, 북촌, 신용산(용리단길), 망원, 합정, 상수, 을지로(힙지로)

---

## 프로젝트 구조

```
fashion_ai/
├── index.html    # 웹 프론트엔드
├── server.py         # Flask API 서버
├── gemini_chat.py    # Google Gemini API 연동 모듈
└── README.md
```

---

## 아키텍처

```
브라우저 (index.html)
        ↓ fetch
Flask API 서버 (server.py)
        ↓
Gemini API (gemini_chat.py)
  ├── 텍스트: gemini-2.5-flash-lite
  └── 이미지: gemini-2.5-flash-image
```

---

## 기술 스택

| 구분 | 사용 기술 |
|------|-----------|
| 프론트엔드 | HTML, CSS, Vanilla JS |
| 지도 | Leaflet.js 1.9.4 |
| 백엔드 | Python, Flask, gunicorn |
| AI | Google Gemini API (`google-genai`) |
| 텍스트 모델 | `gemini-2.5-flash-lite` |
| 이미지 모델 | `gemini-2.5-flash-image` |
| 폰트 | Noto Sans KR, Outfit (Google Fonts) |

---

## 디자인 컨셉

치즈를 모티브로 한 노란색 계열 컬러 팔레트를 사용합니다.

| 역할 | 컬러 | 설명 |
|------|------|------|
| 배경 | `#fffdf2` | 크림 치즈 |
| 유저 말풍선 | `#ffb703` | 체다 치즈 |
| AI 말풍선 | `#fef08a` | 에멘탈 치즈 |
| 포인트 | `#fb8500` | 오렌지 치즈 |