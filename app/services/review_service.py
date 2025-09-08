"""
エンジニアレビューサービス
Engineer Review Service
"""

import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.models.validation import (
    ValidationResult, EngineerReview, ReviewStatus, EngineerDecision, TestResult
)

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReviewService:
    """レビューサービス"""
    
    def __init__(self):
        self.data_dir = Path("data")
        self.reviews_file = self.data_dir / "reviews.json"
        self.data_dir.mkdir(exist_ok=True)
        
        # レビューデータの初期化
        if not self.reviews_file.exists():
            self._save_reviews([])
    
    def create_review_from_result(self, validation_result: ValidationResult) -> Optional[EngineerReview]:
        """検証結果からレビュー項目を作成"""
        
        # レビューが必要かチェック
        if not self._needs_review(validation_result):
            return None
        
        review = EngineerReview(
            id=f"review_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{validation_result.id}",
            validation_result_id=validation_result.id,
            batch_id=getattr(validation_result, 'batch_id', ''),
            test_item_id=validation_result.test_item_id,
            review_status=ReviewStatus.NEEDS_REVIEW
        )
        
        # 元の検証結果にレビュー情報を紐付け
        validation_result.needs_review = True
        validation_result.review_reason = self._generate_review_reason(validation_result)
        validation_result.engineer_review = review
        
        # レビューを保存
        self._save_review(review)
        
        logger.info(f"レビュー項目作成: {review.id} for result {validation_result.id}")
        
        return review
    
    def get_pending_reviews(self, filter_type: str = "all") -> List[EngineerReview]:
        """レビュー待ち項目を取得"""
        all_reviews = self._load_reviews()
        
        # レビュー待ちのみフィルタ
        pending_reviews = [r for r in all_reviews if r.review_status == ReviewStatus.NEEDS_REVIEW]
        
        if filter_type == "all":
            return pending_reviews
        elif filter_type == "failed":
            # 失敗関連のレビューを取得（validation_resultから判定）
            return [r for r in pending_reviews if self._is_failure_review(r)]
        elif filter_type == "needs_check":
            # 要確認関連のレビューを取得
            return [r for r in pending_reviews if self._is_check_review(r)]
        elif filter_type == "completed_today":
            # 本日完了したレビューを取得
            today = datetime.now().strftime('%Y-%m-%d')
            completed_reviews = [r for r in all_reviews if r.review_status != ReviewStatus.NEEDS_REVIEW]
            return [r for r in completed_reviews if r.completed_at and r.completed_at.strftime('%Y-%m-%d') == today]
        
        return pending_reviews
    
    def submit_engineer_review(self, review_id: str, review_data: Dict[str, Any]) -> bool:
        """エンジニアレビューを提出"""
        try:
            reviews = self._load_reviews()
            review = next((r for r in reviews if r.id == review_id), None)
            
            if not review:
                logger.error(f"Review not found: {review_id}")
                return False
            
            # レビューデータ更新
            review.reviewer_name = review_data.get("reviewer_name", "")
            review.review_comments = review_data.get("review_comments", "")
            review.decision_reason = review_data.get("decision_reason", "")
            
            # エンジニア判定に基づく処理
            decision = review_data.get("engineer_decision")
            if decision == "success_approval":
                review.engineer_decision = EngineerDecision.SUCCESS_APPROVAL
                review.review_status = ReviewStatus.SUCCESS_APPROVED
                
            elif decision == "failure_approval":
                review.engineer_decision = EngineerDecision.FAILURE_APPROVAL
                review.review_status = ReviewStatus.FAILURE_APPROVED
                
            elif decision == "re_validation":
                review.engineer_decision = EngineerDecision.RE_VALIDATION
                review.review_status = ReviewStatus.RE_VALIDATION
                review.validation_feedback = review_data.get("validation_feedback", "")
                review.item_feedback = review_data.get("item_feedback", "")
            
            review.reviewed_at = datetime.now()
            
            # 完了時刻設定（再検証以外）
            if decision in ["success_approval", "failure_approval"]:
                review.completed_at = datetime.now()
            
            # データベース更新
            self._update_review(review, reviews)
            
            logger.info(f"レビュー更新完了: {review.id}")
            return True
            
        except Exception as e:
            logger.error(f"レビュー提出エラー: {e}")
            return False
    
    def get_review_by_id(self, review_id: str) -> Optional[EngineerReview]:
        """レビューIDで検索"""
        reviews = self._load_reviews()
        return next((r for r in reviews if r.id == review_id), None)
    
    def get_reviews_by_validation_result(self, validation_result_id: str) -> List[EngineerReview]:
        """検証結果IDでレビューを検索"""
        reviews = self._load_reviews()
        return [r for r in reviews if r.validation_result_id == validation_result_id]
    
    def _needs_review(self, validation_result: ValidationResult) -> bool:
        """レビューが必要か判定"""
        # 失敗または要確認の場合のみレビュー必要
        return validation_result.result in [TestResult.FAIL, TestResult.NEEDS_CHECK]
    
    def _generate_review_reason(self, result: ValidationResult) -> str:
        """レビュー理由を自動生成"""
        if result.result == TestResult.FAIL:
            return f"検証失敗: {result.details or 'エンジニア確認が必要'}"
        elif result.result == TestResult.NEEDS_CHECK:
            return f"要確認: {result.details or '詳細確認が必要'}"
        else:
            return "その他の理由でレビューが必要"
    
    def _is_failure_review(self, review: EngineerReview) -> bool:
        """失敗関連のレビューか判定"""
        # 実際のデータで判定するために、comment内容を確認
        return "失敗" in review.review_comments or "FAIL" in review.review_comments
    
    def _is_check_review(self, review: EngineerReview) -> bool:
        """要確認関連のレビューか判定"""
        # 実際のデータで判定するために、comment内容を確認
        return "要確認" in review.review_comments or "NEEDS_CHECK" in review.review_comments
    
    def _save_review(self, review: EngineerReview):
        """レビューを保存"""
        reviews = self._load_reviews()
        reviews.append(review)
        self._save_reviews(reviews)
    
    def _update_review(self, updated_review: EngineerReview, reviews: List[EngineerReview]):
        """レビューを更新"""
        for i, review in enumerate(reviews):
            if review.id == updated_review.id:
                reviews[i] = updated_review
                break
        self._save_reviews(reviews)
    
    def _load_reviews(self) -> List[EngineerReview]:
        """レビューを読み込み"""
        try:
            if self.reviews_file.exists():
                with open(self.reviews_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [self._dict_to_review(item) for item in data]
            return []
        except Exception as e:
            logger.error(f"レビュー読み込みエラー: {e}")
            return []
    
    def _save_reviews(self, reviews: List[EngineerReview]):
        """レビューを保存"""
        try:
            data = [review.to_dict() for review in reviews]
            with open(self.reviews_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"レビュー保存エラー: {e}")
    
    def _dict_to_review(self, data: Dict[str, Any]) -> EngineerReview:
        """辞書からレビューオブジェクトを作成"""
        return EngineerReview(
            id=data["id"],
            validation_result_id=data["validation_result_id"],
            batch_id=data["batch_id"],
            test_item_id=data["test_item_id"],
            review_status=ReviewStatus(data["review_status"]),
            reviewer_name=data.get("reviewer_name", ""),
            review_comments=data.get("review_comments", ""),
            engineer_decision=EngineerDecision(data["engineer_decision"]) if data.get("engineer_decision") else None,
            decision_reason=data.get("decision_reason", ""),
            validation_feedback=data.get("validation_feedback", ""),
            item_feedback=data.get("item_feedback", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            reviewed_at=datetime.fromisoformat(data["reviewed_at"]) if data.get("reviewed_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        )

# サービスインスタンス取得
_review_service = None

def get_review_service() -> ReviewService:
    """レビューサービスのシングルトンインスタンスを取得"""
    global _review_service
    if _review_service is None:
        _review_service = ReviewService()
    return _review_service
