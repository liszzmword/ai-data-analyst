"""
임베딩 및 벡터 데이터베이스
"""
import os
import pickle
import numpy as np
from typing import List, Tuple
from sentence_transformers import SentenceTransformer
import faiss

from config import EMBEDDING_MODEL_NAME, VECTOR_STORE_DIR
from data_loader import Document


class VectorStore:
    """벡터 스토어 클래스 (FAISS 기반)"""

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME):
        self.model_name = model_name
        self.model = None
        self.index = None
        self.documents = []
        self.dimension = None

        # 캐시 파일 경로
        self.index_path = VECTOR_STORE_DIR / "faiss_index.bin"
        self.docs_path = VECTOR_STORE_DIR / "documents.pkl"
        self.config_path = VECTOR_STORE_DIR / "config.pkl"

        # 벡터 스토어 디렉토리 생성
        VECTOR_STORE_DIR.mkdir(exist_ok=True, parents=True)

    def _load_model(self):
        """임베딩 모델을 로드합니다."""
        if self.model is None:
            print(f"\n🤖 임베딩 모델 로딩 중: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            print(f"✓ 모델 로드 완료 (차원: {self.dimension})")

    def build_index(self, documents: List[Document], force_rebuild: bool = False):
        """
        문서 리스트로부터 벡터 인덱스를 생성합니다.

        Args:
            documents: 문서 리스트
            force_rebuild: 강제로 재생성 여부
        """
        # 캐시된 인덱스 확인
        if not force_rebuild and self._load_from_cache():
            print("✓ 캐시된 벡터 인덱스 로드 완료")
            return

        print(f"\n🔨 벡터 인덱스 생성 중... (문서 수: {len(documents)})")

        # 모델 로드
        self._load_model()

        # 문서 저장
        self.documents = documents

        # 텍스트 추출
        texts = [doc.text for doc in documents]

        # 임베딩 생성
        print("  임베딩 생성 중...")
        embeddings = self.model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # 코사인 유사도를 위해 정규화
        )

        # FAISS 인덱스 생성
        print("  FAISS 인덱스 구축 중...")
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner Product (정규화된 벡터라면 코사인 유사도)
        self.index.add(embeddings.astype('float32'))

        print(f"✓ 인덱스 생성 완료 (총 {self.index.ntotal} 벡터)")

        # 캐시 저장
        self._save_to_cache()

    def search(self, query: str, top_k: int = 5, dataset_filter: str = "전체") -> List[Tuple[Document, float]]:
        """
        쿼리에 대해 유사한 문서를 검색합니다.

        Args:
            query: 검색 쿼리
            top_k: 반환할 문서 수
            dataset_filter: 데이터셋 필터 ("전체", "거래처", "매출", "영업일지")

        Returns:
            [(Document, score), ...] 리스트
        """
        if self.index is None or self.model is None:
            print("✗ 벡터 인덱스가 초기화되지 않았습니다.")
            return []

        # 쿼리 임베딩 생성
        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        ).astype('float32')

        # 검색 (더 많이 가져온 후 필터링)
        search_k = min(top_k * 10, self.index.ntotal)
        distances, indices = self.index.search(query_embedding, search_k)

        # 결과 필터링 및 정리
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= len(self.documents):
                continue

            doc = self.documents[idx]

            # 데이터셋 필터 적용
            if dataset_filter != "전체":
                if doc.metadata.get("dataset") != dataset_filter:
                    continue

            score = float(dist)
            results.append((doc, score))

            if len(results) >= top_k:
                break

        return results

    def _save_to_cache(self):
        """벡터 인덱스를 디스크에 저장합니다."""
        print(f"\n💾 벡터 인덱스 캐싱 중...")

        try:
            # FAISS 인덱스 저장
            faiss.write_index(self.index, str(self.index_path))

            # 문서 저장
            with open(self.docs_path, 'wb') as f:
                pickle.dump(self.documents, f)

            # 설정 저장
            config = {
                'model_name': self.model_name,
                'dimension': self.dimension,
                'num_documents': len(self.documents)
            }
            with open(self.config_path, 'wb') as f:
                pickle.dump(config, f)

            print(f"✓ 캐시 저장 완료: {VECTOR_STORE_DIR}")

        except Exception as e:
            print(f"✗ 캐시 저장 실패: {e}")

    def _load_from_cache(self) -> bool:
        """
        디스크에서 벡터 인덱스를 로드합니다.

        Returns:
            성공 여부
        """
        if not (self.index_path.exists() and self.docs_path.exists() and self.config_path.exists()):
            return False

        try:
            print(f"\n📂 캐시된 인덱스 로딩 중...")

            # 설정 로드
            with open(self.config_path, 'rb') as f:
                config = pickle.load(f)

            # 모델 일치 확인
            if config['model_name'] != self.model_name:
                print(f"⚠ 모델 불일치: {config['model_name']} != {self.model_name}")
                return False

            # 모델 로드
            self._load_model()

            # FAISS 인덱스 로드
            self.index = faiss.read_index(str(self.index_path))

            # 문서 로드
            with open(self.docs_path, 'rb') as f:
                self.documents = pickle.load(f)

            self.dimension = config['dimension']

            print(f"✓ 캐시 로드 완료: {len(self.documents)} 문서, {self.index.ntotal} 벡터")
            return True

        except Exception as e:
            print(f"✗ 캐시 로드 실패: {e}")
            return False

    def clear_cache(self):
        """캐시를 삭제합니다."""
        for path in [self.index_path, self.docs_path, self.config_path]:
            if path.exists():
                path.unlink()
        print("✓ 캐시 삭제 완료")


if __name__ == "__main__":
    # 테스트
    from data_loader import DataLoader

    print("=== 벡터 스토어 테스트 ===")

    # 데이터 로드
    data_loader = DataLoader()
    documents = data_loader.load_all_data()

    # 벡터 스토어 생성
    vector_store = VectorStore()
    vector_store.build_index(documents, force_rebuild=True)

    # 검색 테스트
    test_queries = [
        "한국케미칼상사",
        "최근 매출",
        "거래처 정보"
    ]

    for query in test_queries:
        print(f"\n검색어: {query}")
        results = vector_store.search(query, top_k=3)

        for i, (doc, score) in enumerate(results, 1):
            print(f"\n  {i}. [score={score:.4f}] {doc.metadata['source']}")
            print(f"     {doc.text[:200]}...")
