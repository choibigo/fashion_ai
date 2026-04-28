"""
server.py - CORS 직접 처리 버전
"""

import os
import argparse
from flask import Flask, request, jsonify, make_response
from gemini_chat import GeminiChat

app = Flask(__name__)
bot: GeminiChat = None


# ── CORS 헤더를 모든 응답에 직접 추가 ────────────────────────
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

# OPTIONS preflight 요청 처리
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        res = make_response()
        res.headers["Access-Control-Allow-Origin"]  = "*"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        res.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return res, 200


# ── /chat ─────────────────────────────────────────────────────
@app.route("/chat", methods=["POST"])
def chat():
    data      = request.get_json(silent=True) or {}
    user_text = data.get("message", "").strip()
    is_female = bool(data.get("is_female", False))

    if not user_text:
        return jsonify({"error": "message 필드가 비어 있습니다."}), 400

    try:
        reply = bot.ask(user_text, is_female=is_female)
        return jsonify({"reply": reply})
    except Exception as e:
        import traceback; traceback.print_exc()
        err = str(e)
        if "429" in err or "quota" in err.lower():
            return jsonify({"error": "API 요청 한도 초과! 잠깐 뒤에 다시 물어봐줘 찍찍! 🐭⏳"}), 429
        return jsonify({"error": err}), 500


# ── /image ────────────────────────────────────────────────────
@app.route("/image", methods=["POST"])
def image():
    data  = request.get_json(silent=True) or {}
    style = data.get("style", "").strip()

    try:
        b64 = bot.generate_image_b64(style)
        return jsonify({"image_b64": b64})
    except Exception as e:
        import traceback; traceback.print_exc()
        err = str(e)
        if "429" in err or "quota" in err.lower():
            return jsonify({"error": "이미지 생성 한도 초과! 잠깐 뒤에 다시 눌러봐 찍찍! 🐭⏳"}), 429
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--port",    type=int, default=5001)
    parser.add_argument("--host",    type=str, default="127.0.0.1")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("❌ --api-key 또는 GEMINI_API_KEY 환경변수를 설정하세요.")

    bot = GeminiChat(api_key=api_key)
    print(f"✅ 서울쥐 서버 시작! http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)