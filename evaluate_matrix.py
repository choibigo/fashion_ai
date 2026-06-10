"""
evaluate_matrix.py

여러 지역 간의 생성 이미지 vs 인스타그램 정답 이미지 교차 유사도 벤치마킹 자동화 스크립트
기존 similarity.py의 고성능 피처 추출 엔진을 그대로 래핑하여 사용합니다.

[v2 변경점]
1. 성별(--gender) 필터 지원: 파일명 접미사(_f1, _m3 ...)에서 성별을 자동 인식하여
   여성/남성을 분리 평가하거나(all 이면 전체) 통합 평가할 수 있습니다.
2. 지역당 생성 이미지 N장 지원: 생성 이미지가 여러 장이어도(남 n장·여 n장)
   "모든 생성 × 모든 정답" 쌍의 평균 유사도로 종합 성능을 측정합니다.

파일명 규칙
----------
- 인스타 정답:  images/{지역}_instagram/{지역}_{성별}{번호}.png   예) Cheongdam_f1.png
- 생성 모델:    images/{지역}_model/seoul-mouse-codi_{지역}_{성별}{번호}.png
                                                       예) seoul-mouse-codi_Itaewon_m1.png

사용법
------
python evaluate_matrix.py Seongsu Itaewon Cheongdam
python evaluate_matrix.py Seongsu Itaewon Cheongdam --model dino
python evaluate_matrix.py Seongsu Itaewon Cheongdam --gender f      # 여성만 평가
python evaluate_matrix.py Seongsu Itaewon Cheongdam --gender m      # 남성만 평가
"""

import argparse
import glob
import os
import re
import numpy as np
from PIL import Image

# 기존 similarity.py에서 검증된 Extractor 엔진과 유사도 함수를 그대로 가져와 재사용합니다.
from similarity import CLIPExtractor, DINOv2Extractor, cosine_similarity


# 파일명 끝의 성별 접미사 추출: "..._f1.png" → 'f',  "..._m3.png" → 'm'
GENDER_RE = re.compile(r"_([fmFM])\d+\.png$")


def detect_gender(filename: str) -> str | None:
    """파일명에서 성별('f'/'m')을 추출. 규칙에 안 맞으면 None."""
    m = GENDER_RE.search(filename)
    return m.group(1).lower() if m else None


def gather_files(pattern: str, gender: str) -> list[str]:
    """패턴에 매칭되는 png 중 성별 조건에 맞는 파일만 정렬하여 반환.
    gender='all' 이면 성별 무관 전체 반환(접미사 없는 구버전 파일도 포함)."""
    files = sorted(glob.glob(pattern))
    if gender == "all":
        return files
    return [f for f in files if detect_gender(os.path.basename(f)) == gender]


def run_cross_evaluation(regions: list[str], model_type: str = "clip", gender: str = "all"):
    # 1. 백본 모델 지정 로드
    extractor = CLIPExtractor() if model_type == "clip" else DINOv2Extractor()

    def load_img(path) -> Image.Image:
        return Image.open(path).convert("RGB")

    # 임베딩 캐시 사전. 이제 둘 다 "벡터 리스트"로 보관 (지역당 N장 지원)
    model_features = {}        # region -> list[np.ndarray]
    insta_features_group = {}  # region -> list[np.ndarray]

    print(f"\n[1/2] 패션 이미지 임베딩 추출 시작... (성별 필터: {gender})")

    for r in regions:
        # 생성형 모델 이미지: 폴더 내 전체 png에서 성별 조건에 맞는 것 모두 임베딩
        model_pattern = f"images/{r}_model/*.png"
        model_files = gather_files(model_pattern, gender)
        if model_files:
            model_features[r] = [extractor.extract(load_img(f)) for f in model_files]
            print(f"  ✓ [{r}] 생성 이미지 {len(model_files)}장 임베딩 완료")
        else:
            print(f"  ❌ 경고: [{r}] 조건에 맞는 생성 이미지가 없습니다. ({model_pattern}, gender={gender})")

        # 인스타그램 정답 이미지: 동일하게 성별 조건 필터 후 일괄 임베딩
        insta_pattern = f"images/{r}_instagram/*.png"
        insta_files = gather_files(insta_pattern, gender)
        if insta_files:
            insta_features_group[r] = [extractor.extract(load_img(f)) for f in insta_files]
            print(f"  ✓ [{r}] 인스타 정답 이미지 {len(insta_files)}장 임베딩 완료")
        else:
            print(f"  ❌ 경고: [{r}] 조건에 맞는 인스타 정답 이미지가 없습니다. ({insta_pattern}, gender={gender})")

    # 유효한 지역 필터링 (생성·정답 데이터가 모두 정상 로드된 지역만 선별)
    valid_regions = [r for r in regions if r in model_features and r in insta_features_group]

    if not valid_regions:
        print("❌ 에러: 교차 비교를 수행할 수 있는 유효한 지역 데이터가 존재하지 않습니다.")
        print("   (성별 필터로 인해 해당 성별 이미지가 없는 지역은 제외됩니다.)")
        return

    # 2. 크로스 도메인 유사도 행렬 계산
    # Matrix 구조: 행(Row) = 생성 모델 지역, 열(Col) = 인스타그램 정답 지역
    matrix = np.zeros((len(valid_regions), len(valid_regions)))

    print("\n[2/2] 크로스 도메인 코사인 유사도 연산 진행 중...")
    for i, r_gen in enumerate(valid_regions):
        gen_vectors = model_features[r_gen]
        for j, r_insta in enumerate(valid_regions):
            insta_vectors = insta_features_group[r_insta]

            # 모든 (생성 이미지 × 정답 이미지) 쌍의 유사도 평균 → 종합 성능
            sims = [cosine_similarity(g, t) for g in gen_vectors for t in insta_vectors]
            matrix[i, j] = np.mean(sims) * 100  # 백분율 환산

    # 3. 최종 매트릭스 대시보드 리포팅 출력
    gender_label = {"all": "통합", "f": "여성", "m": "남성"}.get(gender, gender)
    print("\n" + "=" * 75)
    print(f" [교차 지역 패션 유사도 검증 매트릭스]  (백본: {model_type.upper()} / 성별: {gender_label})")
    print("=" * 75)

    # 각 지역에 사용된 이미지 장수 요약 (생성 N장 × 정답 M장)
    for r in valid_regions:
        print(f"   - {r}: 생성 {len(model_features[r])}장 × 정답 {len(insta_features_group[r])}장")
    print("-" * 75)

    # 상단 열 라벨(인스타그램 정답 군집) 출력
    header_str = f"{'생성 모델 ＼ 인스타':<18}"
    for r_insta in valid_regions:
        header_str += f"{r_insta:>14}"
    print(header_str)
    print("-" * 75)

    # 각 행(생성 모델 아웃풋)별 교차 스코어 출력
    for i, r_gen in enumerate(valid_regions):
        row_str = f"{r_gen:<16}"
        for j, r_insta in enumerate(valid_regions):
            score = matrix[i, j]
            # 자기 자신의 도메인 대조(Diagonal)일 경우 대괄호 [] 로 강조 표시
            if i == j:
                row_str += f"{f'[{score:.2f}%]':>14}"
            else:
                row_str += f"{f'{score:.2f}%':>14}"
        print(row_str)

    print("-" * 75)
    print(" 💡 각 괄호 [ ] 기호는 동일 지역 간의 매칭(Within-domain) 점수입니다.")
    print(" 💡 타 지역 스코어 대비 대각선([]) 스코어가 눈에 띄게 높은지 검증하세요.")
    print(" 💡 성별 분리 평가는 --gender f / --gender m 으로 각각 실행하세요.")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="패션 AI 교차 지역 자동화 벤치마크 엔진")
    parser.add_argument("regions", nargs="+", help="실험을 연동할 지역 이름 목록 (공백 분리)")
    parser.add_argument("--model", choices=["clip", "dino"], default="clip", help="특징 추출 모델 백본")
    parser.add_argument("--gender", choices=["all", "f", "m"], default="all",
                        help="평가 대상 성별 필터 (all=통합, f=여성, m=남성)")
    args = parser.parse_args()

    run_cross_evaluation(args.regions, args.model, args.gender)
