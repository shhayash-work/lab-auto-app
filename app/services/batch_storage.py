"""
検証バッチ永続化システム
Validation Batch Storage System

検証バッチとその結果の永続化、RAG用ベクターDB連携
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.models.validation import ValidationBatch, ValidationResult, TestItem
from app.services.vector_store import get_vector_store

# データ保存ディレクトリ
STORAGE_DIR = Path(__file__).parent.parent.parent / "data" / "batches"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

USER_BATCHES_FILE = STORAGE_DIR / "user_batches.json"
BATCH_RESULTS_FILE = STORAGE_DIR / "batch_results.json"

class BatchStorageManager:
    """検証バッチ永続化マネージャー"""
    
    def __init__(self):
        self.vector_store = get_vector_store()
        self.user_batches = self._load_user_batches()
        self.batch_results = self._load_batch_results()
    
    def _load_user_batches(self) -> List[Dict[str, Any]]:
        """ユーザー作成バッチを読み込み"""
        if USER_BATCHES_FILE.exists():
            with open(USER_BATCHES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _load_batch_results(self) -> Dict[str, List[Dict[str, Any]]]:
        """バッチ結果を読み込み"""
        if BATCH_RESULTS_FILE.exists():
            with open(BATCH_RESULTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_user_batches(self):
        """ユーザー作成バッチを保存"""
        with open(USER_BATCHES_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.user_batches, f, ensure_ascii=False, indent=2, default=str)
    
    def _save_batch_results(self):
        """バッチ結果を保存"""
        with open(BATCH_RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.batch_results, f, ensure_ascii=False, indent=2, default=str)
    
    def save_batch(self, batch: ValidationBatch) -> str:
        """検証バッチを保存"""
        batch_data = {
            'id': batch.id,
            'name': batch.name,
            'created_at': batch.created_at.strftime('%Y/%m/%d %H:%M:%S'),
            'completed_at': batch.completed_at.strftime('%Y/%m/%d %H:%M:%S') if batch.completed_at else None,
            'status': batch.status.value,
            'test_items': [item.to_dict() for item in batch.test_items],
            'test_count': len(batch.test_items)
        }
        
        # 既存バッチの更新または新規追加
        existing_index = None
        for i, existing_batch in enumerate(self.user_batches):
            if existing_batch['id'] == batch.id:
                existing_index = i
                break
        
        if existing_index is not None:
            self.user_batches[existing_index] = batch_data
        else:
            self.user_batches.append(batch_data)
        
        self._save_user_batches()
        
        # RAG用ベクターDBに保存
        self._save_to_vector_db(batch)
        
        return batch.id
    
    def save_batch_results(self, batch_id: str, results: List[ValidationResult]):
        """バッチ結果を保存"""
        results_data = [result.to_dict() for result in results]
        self.batch_results[batch_id] = results_data
        self._save_batch_results()
    
    def _save_to_vector_db(self, batch: ValidationBatch):
        """検証バッチをベクターDBに保存（RAG用）"""
        try:
            # 検証項目をテキスト化
            batch_text = f"""
検証バッチ: {batch.name}
作成日時: {batch.created_at.strftime('%Y/%m/%d %H:%M:%S')}

検証項目:
"""
            for item in batch.test_items:
                batch_text += f"""
- 試験ブロック: {item.test_block}
- カテゴリ: {item.category.value}
- 検証条件: {item.condition.condition_text}
- 期待件数: {item.condition.expected_count}
- 対象設備: {', '.join([eq.value for eq in item.condition.equipment_types])}
"""
            
            # ベクターDBに保存
            self.vector_store.add_document(
                doc_id=batch.id,
                content=batch_text,
                metadata={
                    'type': 'validation_batch',
                    'batch_name': batch.name,
                    'created_at': batch.created_at.isoformat(),
                    'test_count': len(batch.test_items)
                }
            )
            
        except Exception as e:
            print(f"ベクターDB保存エラー: {e}")
    
    def get_all_batches(self, include_dummy: bool = True) -> List[Dict[str, Any]]:
        """全バッチを取得（ダミーデータ含む）"""
        batches = self.user_batches.copy()
        
        if include_dummy:
            from app.config.dummy_data import load_dummy_batches
            dummy_batches = load_dummy_batches()
            batches.extend(dummy_batches)
        
        # 作成日時でソート
        batches.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return batches
    
    def get_batch_results(self, batch_id: str) -> List[Dict[str, Any]]:
        """バッチ結果を取得"""
        return self.batch_results.get(batch_id, [])
    
    def delete_user_data(self):
        """ユーザー作成データを削除（ダミーデータは保持）"""
        self.user_batches = []
        self.batch_results = {}
        self._save_user_batches()
        self._save_batch_results()
        
        # ベクターDBからもユーザーデータを削除
        try:
            # ユーザー作成バッチのみ削除（ダミーデータは保持）
            user_doc_ids = [batch['id'] for batch in self.user_batches]
            for doc_id in user_doc_ids:
                self.vector_store.delete_document(doc_id)
        except Exception as e:
            print(f"ベクターDB削除エラー: {e}")
    
    def get_dashboard_metrics(self) -> Dict[str, int]:
        """ダッシュボード用メトリクスを取得"""
        all_batches = self.get_all_batches(include_dummy=True)
        today = datetime.now().strftime('%Y/%m/%d')
        
        today_batches = len([b for b in all_batches if b.get('completed_at', '').startswith(today)])
        success_batches = len([b for b in all_batches if b.get('status') == 'COMPLETED'])
        fail_batches = len([b for b in all_batches if b.get('status') == 'FAILED'])
        running_batches = len([b for b in all_batches if b.get('status') == 'RUNNING'])
        
        return {
            'today_batches': today_batches,
            'success_batches': success_batches,
            'fail_batches': fail_batches,
            'running_batches': running_batches
        }

# グローバルインスタンス
_batch_storage = None

def get_batch_storage() -> BatchStorageManager:
    """バッチストレージマネージャーを取得"""
    global _batch_storage
    if _batch_storage is None:
        _batch_storage = BatchStorageManager()
    return _batch_storage
