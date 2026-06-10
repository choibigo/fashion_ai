# Seoul Mouse's Guide 🐭🧀

> 서울의 동네별 패션 코디를 날씨까지 반영해 추천해주는 AI 챗봇 웹 애플리케이션

시골에서 올라온 **시골쥐**를 위해 힙한 **서울쥐** 캐릭터가 동네 분위기와 그날의 날씨에 맞는 옷차림을 알려줍니다.

🔗 **[choibigo.github.io/fashion_ai](https://choibigo.github.io/fashion_ai)**

---

## 주요 기능

- **인터랙티브 서울 지도**: Leaflet.js 기반으로 서울 주요 동네가 마커로 표시되며, 클릭하면 해당 동네 코디 추천이 시작됩니다.
- **AI 패션 챗봇**: Google Gemini API(`gemini-3.1-flash-lite`)를 활용해 동네별 맞춤 코디를 멀티턴 대화로 추천합니다.
- **실시간 날씨 반영**: Open-Meteo API로 서울의 현재 기온·날씨를 가져와 화면 배지에 표시하고, 코디 추천과 이미지 생성 프롬프트에 함께 반영합니다.
- **AI 이미지 생성**: Gemini 이미지 모델(`gemini-2.5-flash-image`)로 추천 코디를 패션 화보 스타일 이미지로 생성합니다. 한국어 추천을 CoT(Chain-of-Thought) 단계로 영문 프롬프트로 변환해 트렌드·날씨에 맞는 결과를 만듭니다.
- **이미지 재생성**: "🔄 다시 그려줘" 버튼으로 같은 상황·날씨를 유지하되 완전히 다른 코디의 이미지를 다시 생성합니다.
- **성별 맞춤 추천**: 남성/여성 토글로 성별에 맞는 패션 아이템을 추천합니다.
- **세션 관리**: 지역을 바꾸면 대화 히스토리가 자동 초기화되고, "🔄 대화 초기화" 버튼이나 `/reset` API로 수동 초기화할 수 있습니다.

---

## 지원 동네

성수동, 청담동, 이태원

> 코드(`index.html`)에는 한남동·홍대·압구정·여의도·북촌·신용산·망원·합정·상수·을지로 등 추가 동네가 주석 처리되어 있어, 주석을 해제하면 바로 활성화할 수 있습니다.

---

## 프로젝트 구조

```
fashion_ai/
├── index.html               # 배포용 프론트엔드 (API: fashionai.duckdns.org)
├── index_api.html           # 로컬 개발용 프론트엔드 (API: 127.0.0.1:5001)
├── server.py                # Flask API 서버 (/chat, /image, /reset, /health)
├── gemini_chat.py           # Gemini 연동 (텍스트·이미지·날씨·CoT 프롬프트·재생성)
├── requirements.txt         # 서버 의존성 (flask, google-genai, gunicorn)
└── README.md
```

---

## 아키텍처

```
브라우저 (index.html)
   │  ├─ fetch ─────────────► Flask API 서버 (server.py)
   │  │                              │
   │  │                              ▼
   │  │                       Gemini API (gemini_chat.py)
   │  │                         ├── 텍스트: gemini-3.1-flash-lite
   │  │                         └── 이미지: gemini-2.5-flash-image
   │  │
   │  └─ fetch ─────────────► Open-Meteo API (현재 날씨)
   │
   └─ Leaflet.js 지도 (동네 마커)
```

---

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/chat` | 코디 추천 텍스트 생성 (`message`, `is_female`, `weather_info`, `location`) |
| `POST` | `/image` | 코디 이미지 생성 (`style`, `weather_info`, `regenerate`) |
| `POST` | `/reset` | 대화 히스토리 초기화 |
| `GET`  | `/health` | 서버 상태·모델 확인 |

---

## 실행 방법

### 백엔드 (로컬)

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="발급받은_API_키"
python server.py --port 5001
```

### 프론트엔드 (로컬)

`index_api.html`은 `API_BASE`가 `http://127.0.0.1:5001`로 설정되어 있어 로컬 서버와 바로 연동됩니다. 브라우저로 열어 사용하세요. (배포본은 `index.html`이 `https://fashionai.duckdns.org`를 바라봅니다.)

### 배포

- **백엔드**: AWS(EC2)에 gunicorn으로 배포합니다.
- **HTTPS 도메인**: 프론트엔드(GitHub Pages, HTTPS)에서 백엔드를 호출하려면 백엔드도 HTTPS여야 하므로, [DuckDNS](https://www.duckdns.org)로 무료 도메인 `fashionai.duckdns.org`를 발급받아 HTTPS를 적용했습니다.
- **프론트엔드**: `index.html`을 GitHub Pages로 서빙합니다.

---

## 기술 스택

| 구분 | 사용 기술 |
|------|-----------|
| 프론트엔드 | HTML, CSS, Vanilla JS |
| 지도 | Leaflet.js 1.9.4 |
| 날씨 | Open-Meteo API |
| 백엔드 | Python, Flask, gunicorn |
| AI | Google Gemini API (`google-genai`) |
| 텍스트 모델 | `gemini-3.1-flash-lite` |
| 이미지 모델 | `gemini-2.5-flash-image` |
| 배포 | GitHub Pages(프론트), AWS EC2(백엔드), DuckDNS(HTTPS 도메인) |
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