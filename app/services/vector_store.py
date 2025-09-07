"""
ベクターストアサービス - RAG用のベクターデータベース管理
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
# ChromaDBの代わりにシンプルなベクターストアを実装
# import chromadb
# from chromadb.config import Settings
import requests
import json

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
import sys
sys.path.insert(0, str(project_root))

from app.config.settings import OLLAMA_BASE_URL, EMBEDDING_MODEL

logger = logging.getLogger(__name__)

class VectorStore:
    """シンプルなベクターストア（Ollama埋め込み + インメモリ検索）"""
    
    def __init__(self, collection_name: str = "test_items"):
        """
        ベクターストアを初期化
        
        Args:
            collection_name: コレクション名
        """
        self.collection_name = collection_name
        self.documents = []  # インメモリストレージ
        self._initialize_data()
    
    def _initialize_data(self):
        """初期データを初期化"""
        try:
            # 初期データを追加
            self._add_initial_test_items()
            logger.info(f"Simple vector store '{self.collection_name}' initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    def _get_embedding(self, text: str) -> List[float]:
        """Ollamaの埋め込みモデルを使用してテキストの埋め込みを取得"""
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={
                    "model": EMBEDDING_MODEL,
                    "prompt": text
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("embedding", [])
            else:
                logger.error(f"Embedding API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            return []
    
    def add_document(self, doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """ドキュメントをベクターストアに追加"""
        try:
            # 埋め込みを取得
            embedding = self._get_embedding(content)
            
            if not embedding:
                logger.warning(f"Failed to get embedding for document: {doc_id}, using text similarity")
                embedding = []
            
            # メタデータを準備
            if metadata is None:
                metadata = {}
            
            # ドキュメントを追加
            doc = {
                "id": doc_id,
                "content": content,
                "metadata": metadata,
                "embedding": embedding
            }
            self.documents.append(doc)
            
            logger.info(f"Document added: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """検索メソッド（エイリアス）"""
        return self.search_similar_documents(query, top_k)
    
    def search_similar_documents(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """類似ドキュメントを検索（テキスト類似度ベース）"""
        try:
            # クエリの埋め込みを取得
            query_embedding = self._get_embedding(query)
            
            similar_docs = []
            
            if query_embedding:
                # ベクター類似度検索
                similarities = []
                for doc in self.documents:
                    if doc["embedding"]:
                        similarity = self._cosine_similarity(query_embedding, doc["embedding"])
                        similarities.append((similarity, doc))
                
                # 類似度でソート
                similarities.sort(key=lambda x: x[0], reverse=True)
                
                # 上位k件を取得
                for similarity, doc in similarities[:top_k]:
                    similar_docs.append({
                        "content": doc["content"],
                        "metadata": doc["metadata"],
                        "distance": 1.0 - similarity  # 距離に変換
                    })
            
            # ベクター検索で結果が少ない場合、テキスト検索で補完
            if len(similar_docs) < top_k:
                text_matches = []
                query_lower = query.lower()
                
                for doc in self.documents:
                    if any(word in doc["content"].lower() for word in query_lower.split()):
                        # 既に追加されていない場合のみ追加
                        if not any(d["content"] == doc["content"] for d in similar_docs):
                            text_matches.append({
                                "content": doc["content"],
                                "metadata": doc["metadata"],
                                "distance": 0.5  # テキストマッチの距離
                            })
                
                # 不足分を補完
                needed = top_k - len(similar_docs)
                similar_docs.extend(text_matches[:needed])
            
            logger.info(f"Found {len(similar_docs)} similar documents for query: {query}")
            return similar_docs
            
        except Exception as e:
            logger.error(f"Failed to search similar documents: {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """コサイン類似度を計算"""
        try:
            import math
            
            if len(vec1) != len(vec2):
                return 0.0
            
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(a * a for a in vec2))
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
        except Exception:
            return 0.0
    
    def _add_initial_test_items(self):
        """初期の検証項目データを追加"""
        initial_test_items = [
            {
                "id": "base_station_sleep_001",
                "content": "基地局スリープ機能 - ESG選定: 対象基地局の選定条件を確認し、スリープ対象となる基地局を正しく抽出できることを検証",
                "metadata": {
                    "category": "ESG選定",
                    "feature": "基地局スリープ機能",
                    "equipment_type": "ERICSSON_MMU"
                }
            },
            {
                "id": "base_station_sleep_002", 
                "content": "基地局スリープ機能 - CMデータの取得: 基地局のCMデータを正常に取得し、必要な情報が含まれていることを確認",
                "metadata": {
                    "category": "CMデータの取得",
                    "feature": "基地局スリープ機能",
                    "equipment_type": "ERICSSON_MMU"
                }
            },
            {
                "id": "base_station_sleep_003",
                "content": "基地局スリープ機能 - インドア対策局のフィルタ: インドア対策局を正しく識別し、フィルタリング処理が適切に動作することを検証",
                "metadata": {
                    "category": "インドア対策局のフィルタ",
                    "feature": "基地局スリープ機能",
                    "equipment_type": "ERICSSON_MMU"
                }
            },
            {
                "id": "base_station_sleep_004",
                "content": "基地局スリープ機能 - 対策バンドによるフィルタ: 指定された対策バンドに基づいて基地局をフィルタリングし、適切な基地局のみが選択されることを確認",
                "metadata": {
                    "category": "対策バンドによるフィルタ",
                    "feature": "基地局スリープ機能",
                    "equipment_type": "ERICSSON_MMU"
                }
            },
            {
                "id": "base_station_sleep_005",
                "content": "基地局スリープ機能 - ESG作成: フィルタリング結果に基づいてESG（Energy Saving Group）を作成し、適切なグループ構成になることを検証",
                "metadata": {
                    "category": "ESG作成",
                    "feature": "基地局スリープ機能",
                    "equipment_type": "ERICSSON_MMU"
                }
            },
            {
                "id": "base_station_sleep_006",
                "content": "基地局スリープ機能 - ホワイトリスト局のフィルタ: ホワイトリストに登録された基地局を正しく識別し、スリープ対象から除外することを確認",
                "metadata": {
                    "category": "ホワイトリスト局のフィルタ",
                    "feature": "基地局スリープ機能",
                    "equipment_type": "ERICSSON_MMU"
                }
            },
            {
                "id": "base_station_sleep_007",
                "content": "基地局スリープ機能 - ブラックリスト局のフィルタ: ブラックリストに登録された基地局を正しく識別し、スリープ対象から除外することを確認",
                "metadata": {
                    "category": "ブラックリスト局のフィルタ",
                    "feature": "基地局スリープ機能",
                    "equipment_type": "ERICSSON_MMU"
                }
            },
            {
                "id": "base_station_sleep_008",
                "content": "基地局スリープ機能 - 作業データのフィルタ: 保守作業中の基地局を正しく識別し、スリープ対象から除外することを確認",
                "metadata": {
                    "category": "作業データのフィルタ",
                    "feature": "基地局スリープ機能",
                    "equipment_type": "ERICSSON_MMU"
                }
            }
        ]
        
        logger.info("Adding initial test items to vector store...")
        
        for item in initial_test_items:
            self.add_document(
                doc_id=item["id"],
                content=item["content"],
                metadata=item["metadata"]
            )
        
        logger.info(f"Added {len(initial_test_items)} initial test items")

# グローバルインスタンス
_vector_store = None

def get_vector_store() -> VectorStore:
    """ベクターストアのシングルトンインスタンスを取得"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
