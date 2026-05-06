"""
similarity.py

생성 이미지 1장 vs 인스타그램 이미지 N장 패션 유사도 비교
  - 배경 제거는 외부에서 처리 후 입력
  - CLIP 또는 DINOv2 feature cosine similarity

사용법
------
python similarity.py generated.png insta1.png insta2.png insta3.png insta4.png insta5.png
python similarity.py generated.png insta*.png --model dino
"""

import argparse
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image


# ── Feature 추출 ───────────────────────────────────────────────────────────────

class CLIPExtractor:
    MODEL_ID = "openai/clip-vit-base-patch32"

    def __init__(self):
        from transformers import CLIPProcessor, CLIPModel
        print(f"[모델 로딩] {self.MODEL_ID}")
        self.processor = CLIPProcessor.from_pretrained(self.MODEL_ID)
        self.model = CLIPModel.from_pretrained(self.MODEL_ID).eval()

    @torch.no_grad()
    def extract(self, img: Image.Image) -> np.ndarray:
        pixel_values = self.processor(images=img, return_tensors="pt")["pixel_values"]
        vision_out = self.model.vision_model(pixel_values=pixel_values)
        feats = self.model.visual_projection(vision_out.pooler_output)
        feats = F.normalize(feats, dim=-1)
        return feats.squeeze().cpu().numpy()


class DINOv2Extractor:
    MODEL_ID = "facebook/dinov2-base"

    def __init__(self):
        from transformers import AutoImageProcessor, AutoModel
        print(f"[모델 로딩] {self.MODEL_ID}")
        self.processor = AutoImageProcessor.from_pretrained(self.MODEL_ID)
        self.model = AutoModel.from_pretrained(self.MODEL_ID).eval()

    @torch.no_grad()
    def extract(self, img: Image.Image) -> np.ndarray:
        inputs = self.processor(images=img, return_tensors="pt")
        feats = self.model(**inputs).last_hidden_state[:, 0, :]  # CLS 토큰
        feats = F.normalize(feats, dim=-1)
        return feats.squeeze().cpu().numpy()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# ── 비교 ───────────────────────────────────────────────────────────────────────

def compare(
        generated_path: str,
        instagram_paths: list[str],
        model: str = "clip",
) -> list[dict]:
    extractor = CLIPExtractor() if model == "clip" else DINOv2Extractor()

    def load(path: str) -> Image.Image:
        return Image.open(path).convert("RGB")

    print("\n[1/2] Feature 추출")
    gen_feat = extractor.extract(load(generated_path))
    print(f"  생성이미지: {Path(generated_path).name}")

    results = []
    for i, path in enumerate(instagram_paths):
        feat = extractor.extract(load(path))
        sim = cosine_similarity(gen_feat, feat)
        results.append({"path": path, "similarity": sim, "similarity_pct": sim * 100})
        print(f"  인스타[{i + 1}]: {Path(path).name}  →  {sim:.4f}")

    return results


def print_results(results: list[dict], model: str):
    print("\n" + "=" * 60)
    print(f"패션 유사도  (모델: {model.upper()}, cosine similarity)")
    print("=" * 60)
    print(f"{'순위':>4}  {'파일명':<30}  {'유사도':>8}  {'그래프'}")
    print("-" * 60)

    for rank, r in enumerate(sorted(results, key=lambda x: x["similarity"], reverse=True), 1):
        name = Path(r["path"]).name
        pct = r["similarity_pct"]
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"  {rank:>2}.  {name:<30}  {pct:6.2f}%  {bar}")

    print("-" * 60)
    print(f"  평균: {np.mean([r['similarity_pct'] for r in results]):.2f}%")
    print("=" * 60)


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="패션 이미지 유사도 비교")
    parser.add_argument("generated", help="생성된 이미지 경로")
    parser.add_argument("instagram", nargs="+", help="인스타그램 이미지 경로들")
    parser.add_argument("--model", choices=["clip", "dino"], default="clip")
    args = parser.parse_args()

    results = compare(args.generated, args.instagram, args.model)
    print_results(results, args.model)
