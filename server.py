"""
server.py - CORS 직접 처리 버전 (날씨 정보 연동 파라미터 확장)
"""

import os
import argparse
from flask import Flask, request, jsonify, make_response
from gemini_chat import GeminiChat

app = Flask(__name__)

# ── bot 초기화 (gunicorn도 여기서 실행됨) ─────────────────────
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("❌ GEMINI_API_KEY 환경변수를 설정하세요.")
bot = GeminiChat(api_key=api_key)
print(f"✅ 서울쥐 봇 초기화 완료 (모델: {bot.model_name})")


# ── CORS 헤더를 모든 응답에 직접 추가 ────────────────────────
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


# OPTIONS preflight 요청 처리
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        res = make_response()
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        res.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return res, 200


# ── /chat ─────────────────────────────────────────────────────
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_text = data.get("message", "").strip()
    is_female = bool(data.get("is_female", False))
    weather_info = data.get("weather_info", "").strip()
    location = data.get("location", "").strip()

    if not user_text:
        return jsonify({"error": "message 필드가 비어 있습니다."}), 400

    try:
        reply = bot.ask(user_text, is_female=is_female, weather_info=weather_info, location=location)
        return jsonify({"reply": reply})
    except Exception as e:
        import traceback;
        traceback.print_exc()
        err = str(e)
        if "429" in err or "quota" in err.lower():
            return jsonify({"error": "API 요청 한도 초과! 잠깐 뒤에 다시 물어봐줘 찍찍! 🐭⏳"}), 429
        if "503" in err or "service unavailable" in err.lower() or "overloaded" in err.lower():
            return jsonify({"error": "지금 AI 서버가 너무 바빠서 잠깐만 기다렸다가 다시 물어봐주세요! 🔄"}), 503
        return jsonify({"error": err}), 500


# ── /image ────────────────────────────────────────────────────
@app.route("/image", methods=["POST"])
def image():
    data = request.get_json(silent=True) or {}
    style = data.get("style", "").strip()
    weather_info = data.get("weather_info", "").strip()  # 날씨 정보 파싱 추가
    regenerate = bool(data.get("regenerate", False))

    try:
        b64 = bot.generate_image_b64(style, weather_info=weather_info, regenerate=regenerate)
        return jsonify({"image_b64": b64})
    except Exception as e:
        import traceback;
        traceback.print_exc()
        err = str(e)
        if "429" in err or "quota" in err.lower():
            return jsonify({"error": "이미지 생성 한도 초과! 잠깐 뒤에 다시 눌러봐 찍찍! 🐭⏳"}), 429
        if "503" in err or "service unavailable" in err.lower() or "overloaded" in err.lower():
            return jsonify({"error": "지금 AI 서버가 너무 바빠서 이미지를 못 만들었어! 잠깐만 기다렸다가 다시 눌러봐 찍찍! 🐭🔄"}), 503
        return jsonify({"error": err}), 500


# ── /reset ────────────────────────────────────────────────────
@app.route("/reset", methods=["POST"])
def reset():
    bot.reset_history()
    return jsonify({"status": "ok"})


# ── /health ───────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": bot.model_name})


# ── 로컬 실행용 (python server.py) ───────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()
    print(f"✅ 서울쥐 서버 시작! http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)
