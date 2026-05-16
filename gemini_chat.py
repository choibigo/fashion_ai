"""
gemini_chat.py
텍스트: gemini-2.5-flash-lite
이미지 생성: gemini-2.5-flash-image
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

TEXT_MODEL = "gemini-2.5-flash-lite"  # 싼 모델
# TEXT_MODEL  = "gemini-3-flash-preview"    # 비싼 모델
IMAGE_MODEL = "gemini-2.5-flash-image"  # 싼 모델
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

    # ── 내부 ──────────────────────────────────────

    def _system_text(self) -> str:
        hint = GENDER_HINTS["female" if self._is_female else "male"]
        return SYSTEM_INSTRUCTION.strip() + f"\n\n[성별 힌트]\n{hint}"

    def _translate_to_image_prompt(self, korean_style: str) -> str:
        """한국어 코디 설명 → CoT 기반 영문 이미지 생성 프롬프트 변환"""
        gender = "young Korean woman" if self._is_female else "young Korean man"
        request = f"""You are a fashion image prompt engineer. Convert a Korean fashion recommendation into a detailed English image generation prompt using the following Chain-of-Thought steps.

Korean fashion recommendation:
\"\"\"{korean_style}\"\"\"

Think step by step:

Step 1 - Extract clothing items: Identify each specific clothing item mentioned (tops, bottoms, outerwear, shoes, accessories).

Step 2 - Map to 2025 trends: For each item, map it to the closest current 2025 fashion trend keyword (e.g., quiet luxury, streetcore, Y2K revival, Seoul street style, soft tailoring, oversized silhouette, techwear, etc.).

Step 3 - Add visual details: For each item, add specific visual descriptors (fabric texture, fit, color palette, layering, proportions) that make the outfit look modern and editorial.

Step 4 - Compose final prompt: Write a single English image prompt describing the full outfit in detail. The subject is a {gender}.

Output ONLY the final English prompt from Step 4. No explanations, no Korean, no step labels.
Format: "wearing [detailed outfit description with trend-accurate styling]"
"""
        response = self._client.models.generate_content(
            model=self._text_model,
            contents=request,
            config=types.GenerateContentConfig(
                max_output_tokens=256,
                temperature=0.4,
            ),
        )
        return response.text.strip()

    # def _build_image_prompt(self, english_style: str) -> str:
    #     gender = "young Korean woman" if self._is_female else "young Korean man"
    #     return (
    #         f"A full-body fashion editorial photo of a {gender} {english_style}. "
    #         "Seoul street background, natural daylight, shot on film camera, "
    #         "high quality, photorealistic, fashion magazine style. "
    #         "No text, no letters, no watermark, no captions, no overlays."
    #     )
    
    def _build_image_prompt(self, english_style: str) -> str:
        gender = "young Korean woman" if self._is_female else "young Korean man"
        
        # 매 호출마다 달라지는 고유 ID 생성 (동일 프롬프트로 인한 고착화 방지)
        variation_id = str(uuid.uuid4())[:8]

        return (
            # 강력하고 구체적인 다양성 지시 (이전 제안보다 훨씬 강력해짐!)
            "THIS IS A NEW, DISTINCT GENERATION. DO NOT CREATE ANYTHING SIMILAR TO PREVIOUS VERSIONS. "
            f"Generate a completely unique and original interpretation of this outfit for a {gender} [Variation ID: {variation_id}]. "
            "Ensure ALL garment details, fabrics, textures, colors, and designs are distinctly different from ANY previous interpretations of this exact prompt. "
            "Change the silhouette, lapel design, button style, pocket placements, fabric weave, and color nuances of all clothing items. "
            "If specific items are mentioned (e.g., 'black blazer'), do not produce the same black blazer; create a completely new one with different characteristics. "
            
            # 코디 설명
            f"{english_style}. "
            
            # 배경 및 스타일
            "Seoul street background, natural daylight, shot on film camera, "
            "high quality, photorealistic, fashion magazine style. "
            
            # 불필요한 요소 제거
            "No text, no letters, no watermark, no captions, no overlays."
        )

    # ── 공개 메서드 ───────────────────────────────

    def set_gender(self, is_female: bool):
        self._is_female = is_female

    def reset_history(self):
        self._history = []
        self._last_style = ""
        print("[GeminiChat] 히스토리 초기화")

    def ask(self, user_text: str, is_female=None) -> str:
        """텍스트 답변 반환"""
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
        # 한국어 답변을 영문 이미지 프롬프트로 변환해서 저장
        self._last_style = self._translate_to_image_prompt(reply)
        print(f"[GeminiChat] image prompt: {self._last_style}")
        return reply

    def generate_image(self, style_description: str = "") -> bytes:
        """
        코디 이미지 생성 → PNG bytes 반환

        Parameters
        ----------
        style_description : str
            비어 있으면 마지막 ask() 답변을 자동 사용
        """
        prompt = self._build_image_prompt(style_description or self._last_style)

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
            print(
                f"[DEBUG] part[{i}] inline_data={part.inline_data is not None}, text={repr(part.text)[:80] if part.text else None}")
            if part.inline_data is not None:
                return part.inline_data.data  # bytes (PNG)

        raise RuntimeError(f"이미지 데이터를 받지 못했습니다. parts={parts}")

    def generate_image_b64(self, style_description: str = "") -> str:
        """이미지를 base64 문자열로 반환 (HTML <img src> 에 바로 사용 가능)"""
        raw = self.generate_image(style_description)
        return base64.b64encode(raw).decode("utf-8")

    @property
    def model_name(self) -> str:
        return self._text_model
