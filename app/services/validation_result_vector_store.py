"""
検証結果専用ベクターストアサービス
Validation Result Vector Store Service

検証結果データ専用のRAGベクターデータベース管理
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
import sys
sys.path.insert(0, str(project_root))

from app.config.settings import OLLAMA_BASE_URL, EMBEDDING_MODEL
from app.services.batch_storage import load_realistic_batches

logger = logging.getLogger(__name__)

class ValidationResultVectorStore:
    """検証結果専用ベクターストア"""
    
    def __init__(self, collection_name: str = "validation_results"):
        """
        検証結果ベクターストアを初期化
        
        Args:
            collection_name: コレクション名
        """
        self.collection_name = collection_name
        self.documents = []  # インメモリストレージ
        self._initialize_data()
    
    def _initialize_data(self):
        """検証結果データを初期化"""
        try:
            # 検証結果データを追加
            self._add_validation_results_from_batches()
            logger.info(f"Validation result vector store '{self.collection_name}' initialized with {len(self.documents)} results")
                
        except Exception as e:
            logger.error(f"Failed to initialize validation result vector store: {e}")
            self.documents = []  # フォールバック
    
    def _add_validation_results_from_batches(self):
        """バッチデータから検証結果をベクターDBに追加"""
        try:
            # リアルなバッチデータを読み込み
            batches = load_realistic_batches()
            
            for batch in batches:
                batch_id = batch.get('id', 'unknown')
                batch_name = batch.get('name', 'Unknown Batch')
                batch_created_at = batch.get('created_at', '')
                
                # 各検証結果をベクターDBに追加
                for result in batch.get('results', []):
                    # 検証結果をテキスト化
                    result_text = self._format_validation_result_for_embedding(
                        result, batch_name, batch_created_at
                    )
                    
                    # メタデータ作成
                    metadata = {
                        "type": "validation_result",
                        "batch_id": batch_id,
                        "batch_name": batch_name,
                        "result_id": result.get('id', ''),
                        "test_item_id": result.get('test_item_id', ''),
                        "equipment_type": result.get('equipment_type', ''),
                        "result": result.get('result', ''),
                        "created_at": result.get('created_at', ''),
                        "batch_created_at": batch_created_at,
                        "condition_text": result.get('condition_text', '')
                    }
                    
                    # ベクターDBに追加
                    self.add_document(result_text, metadata)
                    
        except Exception as e:
            logger.error(f"Failed to add validation results to vector store: {e}")
    
    def _format_validation_result_for_embedding(self, result: Dict[str, Any], batch_name: str, batch_created_at: str) -> str:
        """検証結果をベクター検索用テキストにフォーマット"""
        
        # 基本情報
        equipment_type = result.get('equipment_type', '')
        test_result = result.get('result', '')
        details = result.get('details', '')
        condition_text = result.get('condition_text', '')
        confidence = result.get('confidence', 0.0)
        execution_time = result.get('execution_time', 0.0)
        created_at = result.get('created_at', '')
        
        # 結果を日本語に変換
        result_map = {
            "PASS": "成功",
            "FAIL": "失敗", 
            "NEEDS_CHECK": "要確認"
        }
        result_jp = result_map.get(test_result, test_result)
        
        # 日付をフォーマット
        try:
            if created_at:
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                date_str = created_date.strftime('%Y年%m月%d日')
            else:
                date_str = "日付不明"
        except:
            date_str = "日付不明"
        
        # ラボ名と設備ベンダーを分離
        lab_name = "不明なラボ"
        vendor = "不明なベンダー"
        if '_' in equipment_type:
            parts = equipment_type.split('_')
            if len(parts) >= 2:
                lab_name = parts[0]
                vendor = parts[1]
        
        # テキスト形式に整形
        formatted_text = f"""
検証結果: {result_jp}
実行日: {date_str}
バッチ: {batch_name}
ラボ設備: {lab_name}
設備ベンダー: {vendor}
検証条件: {condition_text}
判定根拠: {details}
信頼度: {confidence:.2f}
実行時間: {execution_time:.1f}秒
検証設備詳細: {equipment_type}
""".strip()
        
        return formatted_text
    
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
                data = response.json()
                return data.get("embedding", [])
            else:
                logger.error(f"Embedding request failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            return []
    
    def add_document(self, content: str, metadata: Dict[str, Any]) -> bool:
        """ドキュメントをベクターストアに追加"""
        try:
            # 埋め込みを取得
            embedding = self._get_embedding(content)
            if not embedding:
                logger.warning(f"Failed to generate embedding for document")
                return False
            
            # ドキュメントを追加
            doc = {
                "content": content,
                "metadata": metadata,
                "embedding": embedding
            }
            self.documents.append(doc)
            return True
            
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            return False
    
    def search_similar_documents(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """類似ドキュメントを検索"""
        try:
            if not self.documents:
                logger.warning("No documents in vector store")
                return []
            
            # クエリの埋め込みを取得
            query_embedding = self._get_embedding(query)
            if not query_embedding:
                logger.warning("Failed to generate query embedding")
                return []
            
            # 類似度計算
            similar_docs = []
            for doc in self.documents:
                if doc["embedding"]:
                    similarity = self._cosine_similarity(query_embedding, doc["embedding"])
                    similar_docs.append({
                        "content": doc["content"],
                        "metadata": doc["metadata"],
                        "similarity": similarity,
                        "distance": 1.0 - similarity  # 距離に変換
                    })
            
            # 類似度でソート
            similar_docs.sort(key=lambda x: x["similarity"], reverse=True)
            
            # 上位top_k個を返す
            result_docs = similar_docs[:top_k]
            
            # テキスト検索で補完（ベクター検索で結果が少ない場合）
            if len(result_docs) < top_k:
                text_matches = []
                query_lower = query.lower()
                
                for doc in self.documents:
                    if any(word in doc["content"].lower() for word in query_lower.split()):
                        # 既に追加されていない場合のみ追加
                        if not any(d["content"] == doc["content"] for d in result_docs):
                            text_matches.append({
                                "content": doc["content"],
                                "metadata": doc["metadata"],
                                "similarity": 0.5,  # テキストマッチの類似度
                                "distance": 0.5
                            })
                
                # 不足分を補完
                needed = top_k - len(result_docs)
                result_docs.extend(text_matches[:needed])
            
            logger.info(f"Found {len(result_docs)} similar validation results for query: {query}")
            return result_docs
            
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
    
    def get_document_count(self) -> int:
        """保存されている検証結果数を取得"""
        return len(self.documents)
    
    def get_stats(self) -> Dict[str, Any]:
        """ベクターストアの統計情報を取得"""
        if not self.documents:
            return {"total_results": 0, "by_result": {}, "by_equipment": {}}
        
        stats = {
            "total_results": len(self.documents),
            "by_result": {},
            "by_equipment": {},
            "by_lab": {}
        }
        
        for doc in self.documents:
            metadata = doc.get("metadata", {})
            
            # 結果別統計
            result = metadata.get("result", "unknown")
            stats["by_result"][result] = stats["by_result"].get(result, 0) + 1
            
            # 設備別統計
            equipment = metadata.get("equipment_type", "unknown")
            stats["by_equipment"][equipment] = stats["by_equipment"].get(equipment, 0) + 1
            
            # ラボ別統計
            if '_' in equipment:
                lab = equipment.split('_')[0]
                stats["by_lab"][lab] = stats["by_lab"].get(lab, 0) + 1
        
        return stats

# グローバルインスタンス管理
_validation_result_vector_store = None

def get_validation_result_vector_store() -> ValidationResultVectorStore:
    """検証結果ベクターストアのグローバルインスタンスを取得"""
    global _validation_result_vector_store
    if _validation_result_vector_store is None:
        _validation_result_vector_store = ValidationResultVectorStore()
    return _validation_result_vector_store

def reinitialize_validation_result_vector_store():
    """検証結果ベクターストアを再初期化"""
    global _validation_result_vector_store
    _validation_result_vector_store = None
    return get_validation_result_vector_store()
