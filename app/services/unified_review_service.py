"""
統合レビューサービス
Unified Review Service - ValidationResult統合アプローチ
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.validation import ValidationResult, ReviewStatus, EngineerDecision, TestResult

logger = logging.getLogger(__name__)

class UnifiedReviewService:
    """ValidationResult統合ベースのレビューサービス"""
    
    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
    
    def get_pending_reviews(self, filter_type: str = "all") -> List[ValidationResult]:
        """レビュー待ちの検証結果を取得"""
        all_results = self._load_all_validation_results()
        
        # レビュー待ちの結果をフィルタ
        pending_results = [r for r in all_results if r.review_status == ReviewStatus.NEEDS_REVIEW]
        
        if filter_type == "all":
            return pending_results
        elif filter_type == "failed":
            return [r for r in pending_results if r.result == TestResult.FAIL]
        elif filter_type == "needs_check":
            return [r for r in pending_results if r.result == TestResult.NEEDS_CHECK]
        elif filter_type == "completed_today":
            today = datetime.now().strftime('%Y-%m-%d')
            completed_results = [r for r in all_results if r.review_status != ReviewStatus.NEEDS_REVIEW]
            return [r for r in completed_results if r.reviewed_at and r.reviewed_at.strftime('%Y-%m-%d') == today]
        
        return pending_results
    
    def submit_review(self, result_id: str, review_data: Dict[str, Any]) -> bool:
        """レビューを提出"""
        try:
            all_results = self._load_all_validation_results()
            result = next((r for r in all_results if r.id == result_id), None)
            
            if not result:
                logger.error(f"検証結果が見つかりません: {result_id}")
                return False
            
            # レビューデータ更新
            result.reviewer_name = review_data.get("reviewer_name", "")
            result.review_comments = review_data.get("review_comments", "")
            result.decision_reason = review_data.get("decision_reason", "")
            
            # エンジニア判定に基づく処理
            decision = review_data.get("engineer_decision")
            if decision == "success_approval":
                result.engineer_decision = EngineerDecision.SUCCESS_APPROVAL
                result.review_status = ReviewStatus.SUCCESS_APPROVED
                
            elif decision == "failure_approval":
                result.engineer_decision = EngineerDecision.FAILURE_APPROVAL
                result.review_status = ReviewStatus.FAILURE_APPROVED
                
            elif decision == "re_validation":
                result.engineer_decision = EngineerDecision.RE_VALIDATION
                result.review_status = ReviewStatus.RE_VALIDATION
                result.validation_feedback = review_data.get("validation_feedback", "")
                result.item_feedback = review_data.get("item_feedback", "")
            
            result.reviewed_at = datetime.now()
            
            # データ保存
            self._save_all_validation_results(all_results)
            
            logger.info(f"レビュー更新完了: {result.id}")
            return True
            
        except Exception as e:
            logger.error(f"レビュー提出エラー: {e}")
            return False
    
    def get_review_statistics(self) -> Dict[str, int]:
        """レビュー統計を取得"""
        all_results = self._load_all_validation_results()
        
        stats = {
            "pending_total": 0,
            "failed_items": 0,
            "needs_check_items": 0,
            "completed_today": 0
        }
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        for result in all_results:
            if result.review_status == ReviewStatus.NEEDS_REVIEW:
                stats["pending_total"] += 1
                if result.result == TestResult.FAIL:
                    stats["failed_items"] += 1
                elif result.result == TestResult.NEEDS_CHECK:
                    stats["needs_check_items"] += 1
            elif result.reviewed_at and result.reviewed_at.strftime('%Y-%m-%d') == today:
                stats["completed_today"] += 1
        
        return stats
    
    def _load_all_validation_results(self) -> List[ValidationResult]:
        """全ての検証結果を読み込み"""
        results = []
        
        # リアルなバッチデータから読み込み
        realistic_batches_file = self.data_dir / "realistic" / "realistic_batches.json"
        if realistic_batches_file.exists():
            with open(realistic_batches_file, 'r', encoding='utf-8') as f:
                batches = json.load(f)
                
            for batch in batches:
                for result_data in batch.get('results', []):
                    try:
                        result = self._dict_to_validation_result(result_data)
                        results.append(result)
                    except Exception as e:
                        logger.warning(f"検証結果の読み込みに失敗: {e}")
        
        return results
    
    def _save_all_validation_results(self, results: List[ValidationResult]):
        """全ての検証結果を保存（簡易実装）"""
        # デモ環境では保存しない（指示通り）
        logger.info("デモ環境のため検証結果は保存されません")
        pass
    
    def _dict_to_validation_result(self, data: Dict[str, Any]) -> ValidationResult:
        """辞書からValidationResultオブジェクトを作成"""
        from app.models.validation import EquipmentType
        
        # レビューステータスの決定
        review_status = ReviewStatus.NOT_REQUIRED
        result_value = data.get('result', 'PASS')
        if result_value in ['FAIL', 'NEEDS_CHECK']:
            review_status = ReviewStatus.NEEDS_REVIEW
        
        result = ValidationResult(
            id=data.get('id', ''),
            test_item_id=data.get('test_item_id', ''),
            equipment_type=EquipmentType(data.get('equipment_type', 'UNKNOWN')),
            result=TestResult(result_value),
            details=data.get('details', ''),
            response_data=data.get('response_data', {}),
            execution_time=data.get('execution_time', 0.0),
            error_message=data.get('error_message'),
            confidence=data.get('confidence', 1.0),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            review_status=review_status,
            reviewer_name=data.get('reviewer_name', ''),
            review_comments=data.get('review_comments', ''),
            engineer_decision=EngineerDecision(data['engineer_decision']) if data.get('engineer_decision') else None,
            reviewed_at=datetime.fromisoformat(data['reviewed_at']) if data.get('reviewed_at') else None,
            decision_reason=data.get('decision_reason', ''),
            validation_feedback=data.get('validation_feedback', ''),
            item_feedback=data.get('item_feedback', '')
        )
        
        # 追加属性を設定（batch_name と test_id）
        result.batch_name = data.get('batch_name', '不明なバッチ')
        result.test_id = data.get('test_id', result.test_item_id)
        
        return result

# サービスインスタンス取得
_unified_review_service = None

def get_unified_review_service() -> UnifiedReviewService:
    """統合レビューサービスインスタンスを取得"""
    global _unified_review_service
    if _unified_review_service is None:
        _unified_review_service = UnifiedReviewService()
    return _unified_review_service
