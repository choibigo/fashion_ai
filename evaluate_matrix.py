"""
evaluate_matrix.py

여러 지역 간의 생성 이미지 vs 인스타그램 정답 이미지 교차 유사도 벤치마킹 자동화 스크립트
기존 similarity.py의 고성능 피처 추출 엔진을 그대로 래핑하여 사용합니다.

터미널에 python evaluate_matrix.py Seongsu Itaewon Cheongdam을 실행하면
각 지역 간의 스타일 정렬 분별력을 입증할 수 있는 3 by 3 종합 성능 매트릭스 결과 표 출력

사용법
------
python evaluate_matrix.py Seongsu Itaewon Cheongdam
python evaluate_matrix.py Seongsu Itaewon Cheongdam --model dino
"""

import argparse
import glob
import os
from pathlib import Path
import numpy as np
from PIL import Image

# 기존 similarity.py에서 검증된 Extractor 엔진과 유사도 함수를 그대로 가져와 재사용합니다.
from similarity import CLIPExtractor, DINOv2Extractor, cosine_similarity


def run_cross_evaluation(regions: list[str], model_type: str = "clip"):
    # 1. 백본 모델 지정 로드
    extractor = CLIPExtractor() if model_type == "clip" else DINOv2Extractor()
    
    def load_img(path) -> Image.Image:
        return Image.open(path).convert("RGB")

    # 임베딩 캐시 사전 (동일 이미지의 중복 추출 연산 방지)
    model_features = {}
    insta_features_group = {}

    print("\n[1/2] 모든 지역의 패션 이미지 임베딩 추출 시작...")
    
    for r in regions:
        # 생성형 모델 이미지 경로 매핑 및 임베딩
        model_path = f"images/{r}_model/seoul-mouse-codi.png"
        if os.path.exists(model_path):
            model_features[r] = extractor.extract(load_img(model_path))
            print(f"  ✓ [{r}] 생성형 이미지 임베딩 완료")
        else:
            print(f"  ❌ 경고: [{r}] 생성 이미지 파일을 찾을 수 없습니다. ({model_path})")

        # 인스타그램 정답 이미지 패턴 매핑 및 일괄 임베딩
        insta_pattern = f"images/{r}_instagram/*.png"
        insta_files = glob.glob(insta_pattern)
        
        if insta_files:
            feats = []
            for f in insta_files:
                feats.append(extractor.extract(load_img(f)))
            insta_features_group[r] = feats
            print(f"  ✓ [{r}] 인스타 정답 이미지 {len(insta_files)}장 임베딩 완료")
        else:
            print(f"  ❌ 경고: [{r}] 인스타 정답 폴더가 비어있거나 없습니다. ({insta_pattern})")

    # 유효한 지역 필터링 (데이터가 정상 로드된 지역만 선별)
    valid_regions = [r for r in regions if r in model_features and r in insta_features_group]
    
    if not valid_regions:
        print("❌ 에러: 교차 비교를 수행할 수 있는 유효한 지역 데이터가 존재하지 않습니다.")
        return

    # 2. 크로스 도메인 유사도 행렬 계산
    # Matrix 구조: 행(Row) = 생성 모델 지역, 열(Col) = 인스타그램 정답 지역
    matrix = np.zeros((len(valid_regions), len(valid_regions)))

    print("\n[2/2] 크로스 도메인 코사인 유사도 연산 진행 중...")
    for i, r_gen in enumerate(valid_regions):
        gen_vector = model_features[r_gen]
        for j, r_insta in enumerate(valid_regions):
            insta_vectors = insta_features_group[r_insta]
            
            # 특정 생성 이미지 1장 vs 타깃 지역 인스타 이미지들 간의 유사도 평균 계산
            sims = [cosine_similarity(gen_vector, inst_vec) for inst_vec in insta_vectors]
            matrix[i, j] = np.mean(sims) * 100  # 백분율 환산

    # 3. 최종 매트릭스 대시보드 리포팅 출력
    print("\n" + "=" * 75)
    print(f" [교차 지역 패션 유사도 검증 매트릭스]  (모델 백본: {model_type.upper()})")
    print("=" * 75)
    
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
    print("=" * 75 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="패션 AI 교차 지역 자동화 벤치마크 엔진")
    parser.add_argument("regions", nargs="+", help="실험을 연동할 지역 이름 목록 (공백 분리)")
    parser.add_argument("--model", choices=["clip", "dino"], default="clip", help="특징 추출 모델 백본")
    args = parser.parse_args()

    run_cross_evaluation(args.regions, args.model)