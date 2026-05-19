"""
gemini_chat.py
텍스트: gemini-2.5-flash-lite
이미지 생성: gemini-2.5-flash-image
날씨 및 기온 정보 반영 프롬프트 엔지니어링 적용 버전
"""

import os
import base64
import uuid
from google import genai
from google.genai import types

SYSTEM_INSTRUCTION = """
당신은 "서울쥐"입니다. 서울의 힙한 동네를 손바닥 보듯 꿰고 있는 트렌디한 쥐 캐릭터예요.
시골에서 올라온 친구 "시골쥐"에게 서울 동네별 옷차림·패션 코디를 알려줍니다.

[말투 규칙]
- 항상 활기차고 친근한 반말을 사용하세요.
- "찍찍!", "찍!" 같은 쥐 의성어를 자연스럽게 섞으세요.
- 이모지를 적극 활용하세요.
- 대답은 3~5문장 내외로 간결하게.

[답변 구조]
1. 해당 동네의 분위기를 한 문장으로 설명.
2. 사용자의 성별에 맞는 구체적인 코디 아이템을 추천.
3. 자신감을 불어넣는 응원 한 마디로 마무리.

[주의]
- 서울 동네와 관련 없는 질문에는 "어디 갈지 알려줘야 코디를 추천해줄 수 있어! 찍찍! 🐭"라고 안내하세요.
- HTML 태그는 사용하지 마세요. 순수 텍스트로만 답변하세요.
"""

GENDER_HINTS = {
    "female": "사용자는 여성입니다. 여성 패션 아이템(스커트, 블라우스, 힐 등)을 중심으로 추천하세요. 답변은 여성스러운 표현으로 해주세요.",
    "male": "사용자는 남성입니다. 남성 패션 아이템(자켓, 팬츠, 스니커즈 등)을 중심으로 추천하세요. 답변은 남성적인 표현으로 해주세요.",
}

TEXT_MODEL = "gemini-2.5-flash-lite"
# TEXT_MODEL  = "gemini-3-flash-preview"    # 비싼 모델
IMAGE_MODEL = "gemini-2.5-flash-image"
# IMAGE_MODEL = "gemini-3.1-flash-image-preview"  # 비싼 모델


class GeminiChat:
    def __init__(self, api_key=None, text_model=TEXT_MODEL, image_model=IMAGE_MODEL):
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("API 키를 api_key 인자 또는 GEMINI_API_KEY 환경변수로 전달하세요.")

        self._client = genai.Client(api_key=key)
        self._text_model = text_model
        self._image_model = image_model
        self._is_female = False
        self._history = []  # list[types.Content]
        self._last_style = ""  # 마지막 코디 설명 (이미지 생성 프롬프트용)
        self._last_reply = ""  # 마지막 한국어 답변 (재생성 시 재번역용)
        self._last_weather = ""  # 마지막 대화 시점의 날씨 정보 저장

    # ── 내부 ──────────────────────────────────────

    def _system_text(self) -> str:
        hint = GENDER_HINTS["female" if self._is_female else "male"]
        return SYSTEM_INSTRUCTION.strip() + f"\n\n[성별 힌트]\n{hint}"

    def _translate_to_image_prompt(self, korean_style: str, weather_info: str = "", regenerate: bool = False) -> str:
        """한국어 코디 설명 → CoT 기반 영문 이미지 생성 프롬프트 변환 (날씨 반영 가이드 포함)"""
        gender = "young Korean woman" if self._is_female else "young Korean man"

        weather_context = f"\n[Current Weather Conditions]: {weather_info}" if weather_info else ""

        regenerate_context = (
            "\n[REGENERATION REQUEST]: The user was not satisfied with the previous image and clicked 'regenerate'. "
            "You MUST produce a completely different prompt. "
            "CRITICAL: Do NOT reuse the same clothing items or designs from the previous generation. "
            "Choose entirely different garment types, designs, and styles that still fit the occasion and weather. "
            "For example, if the previous image had a blazer, use a different type of outerwear; "
            "if it had straight-leg pants, try wide-leg, cargo, or a skirt instead. "
            "The new outfit must look like a completely different person's wardrobe choice for the same situation."
        ) if regenerate else ""

        request = f"""You are a fashion image prompt engineer. Convert a Korean fashion recommendation into a detailed English image generation prompt using the following Chain-of-Thought steps.{weather_context}{regenerate_context}

Korean fashion recommendation:
\"\"\"{korean_style}\"\"\"

Think step by step:

Step 1 - Extract clothing items: Identify each specific clothing item mentioned (tops, bottoms, outerwear, shoes, accessories).{"  Since this is a REGENERATION, treat these as inspiration only — you must select DIFFERENT garment types and designs. Do not carry over any specific items from the previous generation." if regenerate else ""}

Step 2 - Map to 2026 trends: For each item, map it to the closest current 2026 fashion trend keyword (e.g., quiet luxury, streetcore, Y2K revival, Seoul street style, soft tailoring, oversized silhouette, techwear, etc.).{"  Choose a different trend direction than what was previously used." if regenerate else ""}

Step 3 - Add visual details & Weather Adaptability: For each item, add specific visual descriptors (fabric texture, fit, color palette, layering, proportions). Ensure the fabric weight, thickness, and layering logic are highly realistic and strictly appropriate for the given weather/temperature condition ({weather_info if weather_info else 'seasonal weather'}). If it's rainy, sunny, or cold, adjust the material appearance (e.g., lightweight linen for hot weather, heavy wool for cold, waterproof sheen or holding an umbrella for rain).

Step 4 - Compose final prompt: Write a single English image prompt describing the full outfit in detail. The subject is a {gender}.{"  REGENERATION RULE: The final outfit must use different clothing items and designs from the previous version — different garment types, different silhouettes, different color story, different styling direction." if regenerate else ""}

Output ONLY the final English prompt from Step 4. No explanations, no Korean, no step labels.
Format: "wearing [detailed outfit description with trend-accurate and weather-appropriate styling]"
"""
        response = self._client.models.generate_content(
            model=self._text_model,
            contents=request,
            config=types.GenerateContentConfig(
                max_output_tokens=256,
                temperature=1.0 if regenerate else 0.4,
            ),
        )
        return response.text.strip()

    def _build_image_prompt(self, english_style: str, weather_info: str = "", regenerate: bool = False) -> str:
        gender = "young Korean woman" if self._is_female else "young Korean man"
        variation_id = str(uuid.uuid4())[:8]

        # 날씨 기온 정보에 따른 배경 환경 조건 정의
        weather_environment = "Seoul street background, natural daylight"
        if weather_info:
            weather_environment = (
                f"Seoul street background perfectly matching the weather condition '{weather_info}'. "
                f"Adjust the ambient lighting, sky texture, and ground surface (e.g., wet asphalt with puddle reflections for rain, "
                f"bright cinematic sunlight with harsh shadows for hot sunny weather, or soft overcast diffused light for cloudy days) to realistically reflect this climate."
            )

        regen_prefix = (
            "THIS IS A REGENERATION — the user rejected the previous image. "
            "You MUST NOT reproduce the same clothing items, designs, or visual style as the previous image. "
            "Use completely different garment types, cuts, colors, and fashion aesthetic. "
        ) if regenerate else (
            "THIS IS A NEW, DISTINCT GENERATION. DO NOT CREATE ANYTHING SIMILAR TO PREVIOUS VERSIONS. "
        )

        return (
            f"{regen_prefix}"
            f"Generate a completely unique and original interpretation of this outfit for a {gender} [Variation ID: {variation_id}]. "
            "Ensure ALL garment details, fabrics, textures, colors, and designs are distinctly different from ANY previous interpretations of this exact prompt. "
            "Change the silhouette, lapel design, button style, pocket placements, fabric weave, and color nuances of all clothing items. "
            "If specific items are mentioned (e.g., 'black blazer'), do not produce the same black blazer; create a completely new one with different characteristics. "

            # 코디 설명 적용
            f"{english_style}. "

            # 날씨 정보 기반 배경 및 촬영 스타일
            f"{weather_environment}, shot on film camera, high quality, photorealistic, fashion magazine style. "

            # 불필요한 요소 제거
            "No text, no letters, no watermark, no captions, no overlays."
        )

    # ── 공개 메서드 ───────────────────────────────

    def set_gender(self, is_female: bool):
        self._is_female = is_female

    def reset_history(self):
        self._history = []
        self._last_style = ""
        self._last_weather = ""
        print("[GeminiChat] 히스토리 초기화")

    def ask(self, user_text: str, is_female=None, weather_info: str = "") -> str:
        """텍스트 답변 반환 및 날씨 콘텍스트 기록"""
        if is_female is not None and is_female != self._is_female:
            gender_str = "여성" if is_female else "남성"
            self._history.append(
                types.Content(role="user", parts=[types.Part(
                    text=f"[성별 변경] 이제부터 나는 {gender_str}이야. {gender_str} 패션으로 추천해줘."
                )])
            )
            self._history.append(
                types.Content(role="model", parts=[types.Part(
                    text=f"알겠어! 이제부터 {gender_str} 코디로 추천해줄게! 찍찍! 🐭"
                )])
            )
            self.set_gender(is_female)
        elif is_female is not None:
            self.set_gender(is_female)

        self._history.append(
            types.Content(role="user", parts=[types.Part(text=user_text)])
        )

        response = self._client.models.generate_content(
            model=self._text_model,
            contents=self._history,
            config=types.GenerateContentConfig(
                system_instruction=self._system_text(),
                max_output_tokens=512,
                temperature=0.9,
            ),
        )

        reply = response.text.strip().replace("**", "")

        self._history.append(
            types.Content(role="model", parts=[types.Part(text=reply)])
        )

        # 현재 날씨 상태 저장 및 영문 이미지 프롬프트 변환 시 인자로 주입
        self._last_weather = weather_info
        self._last_reply = reply
        self._last_style = self._translate_to_image_prompt(reply, weather_info=weather_info)
        print(f"[GeminiChat] image prompt: {self._last_style}")
        return reply

    def generate_image(self, style_description: str = "", weather_info: str = "", regenerate: bool = False) -> bytes:
        """코디 이미지 생성 → PNG bytes 반환 (동적 백그라운드 반영)"""
        current_weather = weather_info or self._last_weather
        if regenerate and self._last_reply:
            english_style = self._translate_to_image_prompt(self._last_reply, weather_info=current_weather, regenerate=True)
            print(f"[GeminiChat] regenerated image prompt: {english_style}")
        else:
            english_style = style_description or self._last_style
        prompt = self._build_image_prompt(english_style, weather_info=current_weather, regenerate=regenerate)

        response = self._client.models.generate_content(
            model=self._image_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        candidates = response.candidates
        if not candidates:
            raise RuntimeError(f"candidates 없음. response: {response}")

        parts = candidates[0].content.parts
        print(f"[DEBUG] parts count: {len(parts)}")
        for i, part in enumerate(parts):
            if part.inline_data is not None:
                return part.inline_data.data

        raise RuntimeError(f"이미지 데이터를 받지 못했습니다. parts={parts}")

    def generate_image_b64(self, style_description: str = "", weather_info: str = "", regenerate: bool = False) -> str:
        raw = self.generate_image(style_description, weather_info=weather_info, regenerate=regenerate)
        return base64.b64encode(raw).decode("utf-8")

    @property
    def model_name(self) -> str:
        return self._text_model
