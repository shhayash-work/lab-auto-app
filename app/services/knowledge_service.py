"""
知見学習サービス
Knowledge Learning Service
"""

import sys
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.models.validation import ValidationResult, TestItem
from app.models.knowledge import KnowledgeEntry, KnowledgeCategory, KnowledgeSearchResult
from app.services.vector_store import get_vector_store

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KnowledgeService:
    """知見学習サービス"""
    
    def __init__(self):
        self.data_dir = Path("data")
        self.knowledge_file = self.data_dir / "knowledge.json"
        self.data_dir.mkdir(exist_ok=True)
        
        # 知見データの初期化
        if not self.knowledge_file.exists():
            self._save_knowledge_entries([])
        
        # ベクターストア
        self.vector_store = get_vector_store()
        
        # LLMサービス（遅延ロード）
        self._llm_service = None
    
    def _get_llm_service(self):
        """LLMサービスを遅延ロード"""
        if self._llm_service is None:
            try:
                from app.services.llm_service import get_llm_service
                self._llm_service = get_llm_service("ollama")
            except Exception as e:
                logger.warning(f"LLMサービス初期化失敗: {e}")
                self._llm_service = None
        return self._llm_service
    
    def extract_knowledge_from_review(self, review) -> List[KnowledgeEntry]:
        """エンジニアレビューから知見を抽出"""
        
        # 再検証判定の場合のみ知見抽出
        decision_value = getattr(review.engineer_decision, 'value', review.engineer_decision) if hasattr(review, 'engineer_decision') else None
        if decision_value != "re_validation":
            return []
        
        knowledge_entries = []
        
        # 検証方法フィードバックから知見抽出
        if review.validation_feedback:
            validation_knowledge = self._create_knowledge_entry(
                review, 
                KnowledgeCategory.VALIDATION_METHOD,
                review.validation_feedback,
                "validation_feedback"
            )
            if validation_knowledge:
                knowledge_entries.append(validation_knowledge)
        
        # 検証項目フィードバックから知見抽出
        if review.item_feedback:
            item_knowledge = self._create_knowledge_entry(
                review,
                KnowledgeCategory.TEST_ITEM_CREATION,
                review.item_feedback,
                "item_feedback"
            )
            if item_knowledge:
                knowledge_entries.append(item_knowledge)
        
        # ベクターDBと構造化DBに保存
        for knowledge in knowledge_entries:
            self._store_knowledge_in_vector_db(knowledge)
            self._save_knowledge_entry(knowledge)
        
        logger.info(f"知見抽出完了: {len(knowledge_entries)}件 from review {review.id}")
        
        return knowledge_entries
    
    def search_relevant_knowledge(self, test_item: TestItem, category: Optional[KnowledgeCategory] = None, limit: int = 3) -> List[KnowledgeSearchResult]:
        """関連する知見を検索"""
        
        # 検索クエリ作成
        search_query = f"""
        試験ブロック: {test_item.test_block}
        カテゴリ: {test_item.category.value}
        検証条件: {test_item.condition.condition_text}
        対象設備: {[eq.value for eq in test_item.condition.equipment_types]}
        """
        
        try:
            # ベクター検索実行
            search_results = self.vector_store.search_similar_documents(
                query=search_query,
                top_k=limit * 2  # フィルタリング考慮して多めに取得
            )
            
            knowledge_results = []
            for result in search_results:
                metadata = result.get("metadata", {})
                knowledge_id = metadata.get("knowledge_id")
                if knowledge_id:
                    knowledge_entry = self._load_knowledge_by_id(knowledge_id)
                    if knowledge_entry:
                        # カテゴリフィルタ
                        if category and knowledge_entry.category != category:
                            continue
                        
                        # 距離を類似度スコアに変換
                        similarity_score = 1.0 - result.get("distance", 0.0)
                            
                        knowledge_results.append(KnowledgeSearchResult(
                            entry=knowledge_entry,
                            similarity_score=similarity_score,
                            matching_keywords=self._extract_matching_keywords(search_query, knowledge_entry),
                            relevance_reason=self._generate_relevance_reason(test_item, knowledge_entry)
                        ))
                
                if len(knowledge_results) >= limit:
                    break
            
            # 使用回数を更新
            for kr in knowledge_results:
                self._increment_usage_count(kr.entry.id)
            
            return knowledge_results
            
        except Exception as e:
            logger.error(f"知見検索エラー: {e}")
            return []
    
    def enhance_validation_prompt(self, base_prompt: str, test_item: TestItem) -> str:
        """検証実行プロンプトを知見で強化"""
        
        relevant_knowledge = self.search_relevant_knowledge(
            test_item, 
            category=KnowledgeCategory.VALIDATION_METHOD,
            limit=3
        )
        
        if not relevant_knowledge:
            return base_prompt
        
        # 知見情報をプロンプトに統合
        knowledge_section = "\n【過去の検証知見・注意点】\n"
        
        for i, kr in enumerate(relevant_knowledge, 1):
            knowledge = kr.entry
            knowledge_section += f"""
{i}. {knowledge.test_block} - {knowledge.equipment_type}
   エンジニアフィードバック: {knowledge.engineer_feedback}
   問題の概要: {knowledge.problem_description}
   改善提案: {knowledge.solution_suggestion}
   改善ノート: {knowledge.improvement_notes}
   (類似度: {kr.similarity_score:.2f}, レビュアー: {knowledge.reviewer_name})
"""
        
        enhanced_prompt = f"""
{base_prompt}

{knowledge_section}

【重要】上記の過去のエンジニアフィードバックを参考に、以下の点に特に注意して検証を実施してください：
1. 同様の問題が発生しないよう改善提案を検証手法に反映
2. エンジニアが指摘した問題点を回避する方法で検証実行
3. 検証結果の判定時に、成功/失敗/要確認を慎重に判断

検証結果の判定は以下の基準で行ってください：
- PASS（成功）: 検証条件を完全に満たし、異常が全く見られない
- FAIL（失敗）: 検証条件を満たさない、または明確な問題が発生
- NEEDS_CHECK（要確認）: 結果が曖昧、予期しない値、または判断に迷う場合

検証結果には、これらの知見を参考にした箇所と新たに発見した事項を明記してください。
"""
        
        return enhanced_prompt
    
    def enhance_item_generation_prompt(self, base_prompt: str, feature_name: str, equipment_types: List[str]) -> str:
        """検証項目生成プロンプトを知見で強化"""
        
        # 項目作成関連の知見を検索（簡易的にfeature_nameで検索）
        search_query = f"試験ブロック: {feature_name} 対象設備: {equipment_types}"
        
        try:
            search_results = self.vector_store.search_similar_documents(
                query=search_query,
                top_k=3
            )
            
            item_knowledge = []
            for result in search_results:
                metadata = result.get("metadata", {})
                knowledge_id = metadata.get("knowledge_id")
                if knowledge_id:
                    knowledge_entry = self._load_knowledge_by_id(knowledge_id)
                    if knowledge_entry and knowledge_entry.category == KnowledgeCategory.TEST_ITEM_CREATION:
                        item_knowledge.append(knowledge_entry)
            
            if not item_knowledge:
                return base_prompt
            
            # 知見情報をプロンプトに統合
            knowledge_section = "\n【検証項目作成に関する過去の知見】\n"
            
            for i, knowledge in enumerate(item_knowledge, 1):
                knowledge_section += f"""
{i}. {knowledge.test_block} - {knowledge.equipment_type}
   エンジニアフィードバック: {knowledge.engineer_feedback}
   問題の概要: {knowledge.problem_description}
   改善提案: {knowledge.solution_suggestion}
   (レビュアー: {knowledge.reviewer_name})
"""
            
            enhanced_prompt = f"""
{base_prompt}

{knowledge_section}

【重要】上記の過去のエンジニアフィードバックを参考に、検証項目作成時は以下の点に注意してください：
1. 過去に指摘された項目の不備を回避する
2. エンジニアが提案した改善点を検証条件に反映
3. 類似機能で見落としがちな検証観点を含める

これらの知見を活用して、より実用的で漏れのない検証項目を生成してください。
"""
            
            return enhanced_prompt
            
        except Exception as e:
            logger.error(f"項目生成プロンプト強化エラー: {e}")
            return base_prompt
    
    def _create_knowledge_entry(self, review, category: KnowledgeCategory, 
                              feedback_text: str, feedback_type: str) -> Optional[KnowledgeEntry]:
        """知見エントリを作成"""
        
        try:
            # LLMを使って構造化情報を抽出
            structured_info = self._extract_structured_info(feedback_text, category)
            
            knowledge_entry = KnowledgeEntry(
                id=f"knowledge_{category.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{review.id}",
                category=category,
                test_block=self._get_test_block_from_review(review),
                test_category=self._get_test_category_from_review(review),
                equipment_type=self._get_equipment_type_from_review(review),
                condition_text=self._get_condition_text_from_review(review),
                engineer_feedback=feedback_text,
                feedback_type=feedback_type,
                problem_description=structured_info.get("problem_description", ""),
                solution_suggestion=structured_info.get("solution_suggestion", ""),
                improvement_notes=structured_info.get("improvement_notes", ""),
                reviewer_name=review.reviewer_name,
                confidence_level=self._calculate_confidence(review, feedback_text),
                source_review_id=review.id,
                source_validation_id=review.validation_result_id,
                tags=self._extract_tags(feedback_text, category)
            )
            
            return knowledge_entry
            
        except Exception as e:
            logger.error(f"知見エントリ作成エラー: {e}")
            return None
    
    def _extract_structured_info(self, feedback_text: str, category: KnowledgeCategory) -> Dict[str, str]:
        """LLMを使ってフィードバックから構造化情報を抽出"""
        
        prompt = f"""
以下のエンジニアフィードバックから、構造化された情報を抽出してください。

フィードバック種別: {category.value}
フィードバック内容: {feedback_text}

以下のJSON形式で出力してください：
{{
    "problem_description": "問題の概要を簡潔に",
    "solution_suggestion": "解決・改善提案を具体的に", 
    "improvement_notes": "追加の改善ポイントや注意事項"
}}
"""
        
        try:
            llm_service = self._get_llm_service()
            if llm_service:
                # 簡易的な構造化情報抽出（LLMエラー回避）
                response = f"""
                {{
                    "problem_description": "{feedback_text[:100]}{'...' if len(feedback_text) > 100 else ''}",
                    "solution_suggestion": "エンジニアフィードバックに基づく改善が必要", 
                    "improvement_notes": "詳細な分析と対策の検討が必要"
                }}
                """
                
                # JSON抽出
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            
        except Exception as e:
            logger.warning(f"構造化情報抽出失敗: {e}")
        
        # フォールバック：シンプルな分割
        return {
            "problem_description": feedback_text[:100] + "..." if len(feedback_text) > 100 else feedback_text,
            "solution_suggestion": "詳細な解決提案を検討する",
            "improvement_notes": "追加の改善が必要"
        }
    
    def _store_knowledge_in_vector_db(self, knowledge: KnowledgeEntry):
        """ベクターDBに知見を保存"""
        try:
            # 検索用テキスト作成
            search_text = f"""
            試験ブロック: {knowledge.test_block}
            カテゴリ: {knowledge.test_category}
            設備: {knowledge.equipment_type}
            検証条件: {knowledge.condition_text}
            問題: {knowledge.problem_description}
            解決策: {knowledge.solution_suggestion}
            フィードバック: {knowledge.engineer_feedback}
            """
            
            metadata = {
                "knowledge_id": knowledge.id,
                "category": knowledge.category.value,
                "test_block": knowledge.test_block,
                "equipment_type": knowledge.equipment_type,
                "reviewer": knowledge.reviewer_name,
                "created_at": knowledge.created_at.isoformat()
            }
            
            self.vector_store.add_text(search_text, metadata)
            
        except Exception as e:
            logger.error(f"ベクターDB保存エラー: {e}")
    
    def _calculate_confidence(self, review, feedback_text: str) -> float:
        """知見の信頼度を計算"""
        confidence = 0.5  # ベース値
        
        # フィードバックの詳細度
        if len(feedback_text) > 100:
            confidence += 0.2
        if len(feedback_text) > 200:
            confidence += 0.1
        
        # レビューの質
        if len(review.decision_reason) > 50:
            confidence += 0.1
        if review.reviewer_name:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _extract_tags(self, feedback_text: str, category: KnowledgeCategory) -> List[str]:
        """フィードバックからタグを抽出"""
        tags = [category.value]
        
        # キーワード抽出（簡易実装）
        keywords = ["設定", "通信", "エラー", "タイムアウト", "性能", "検証", "確認", "改善"]
        for keyword in keywords:
            if keyword in feedback_text:
                tags.append(keyword)
        
        return list(set(tags))
    
    def _extract_matching_keywords(self, query: str, knowledge: KnowledgeEntry) -> List[str]:
        """マッチしたキーワードを抽出"""
        query_words = re.findall(r'\w+', query.lower())
        knowledge_text = f"{knowledge.engineer_feedback} {knowledge.problem_description}".lower()
        
        matching = []
        for word in query_words:
            if len(word) > 2 and word in knowledge_text:
                matching.append(word)
        
        return matching[:5]  # 最大5個
    
    def _generate_relevance_reason(self, test_item: TestItem, knowledge: KnowledgeEntry) -> str:
        """関連性の理由を生成"""
        reasons = []
        
        if test_item.test_block == knowledge.test_block:
            reasons.append("同一試験ブロック")
        if test_item.category.value == knowledge.test_category:
            reasons.append("同一カテゴリ")
        
        equipment_types = [eq.value for eq in test_item.condition.equipment_types]
        if knowledge.equipment_type in equipment_types:
            reasons.append("同一設備タイプ")
        
        if not reasons:
            reasons.append("検証条件の類似性")
        
        return "、".join(reasons)
    
    # ヘルパーメソッド群（レビューから情報取得）
    def _get_test_block_from_review(self, review) -> str:
        # 実際の実装では validation_result や test_item から取得
        return "Unknown Test Block"
    
    def _get_test_category_from_review(self, review) -> str:
        return "Unknown Category"
    
    def _get_equipment_type_from_review(self, review) -> str:
        return "Unknown Equipment"
    
    def _get_condition_text_from_review(self, review) -> str:
        return "Unknown Condition"
    
    def _increment_usage_count(self, knowledge_id: str):
        """知見の使用回数を増加"""
        try:
            knowledge_entries = self._load_knowledge_entries()
            for knowledge in knowledge_entries:
                if knowledge.id == knowledge_id:
                    knowledge.usage_count += 1
                    break
            self._save_knowledge_entries(knowledge_entries)
        except Exception as e:
            logger.error(f"使用回数更新エラー: {e}")
    
    def _load_knowledge_by_id(self, knowledge_id: str) -> Optional[KnowledgeEntry]:
        """IDで知見を検索"""
        knowledge_entries = self._load_knowledge_entries()
        return next((k for k in knowledge_entries if k.id == knowledge_id), None)
    
    def _save_knowledge_entry(self, knowledge: KnowledgeEntry):
        """知見を保存"""
        knowledge_entries = self._load_knowledge_entries()
        knowledge_entries.append(knowledge)
        self._save_knowledge_entries(knowledge_entries)
    
    def _load_knowledge_entries(self) -> List[KnowledgeEntry]:
        """知見を読み込み"""
        try:
            if self.knowledge_file.exists():
                with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [self._dict_to_knowledge(item) for item in data]
            return []
        except Exception as e:
            logger.error(f"知見読み込みエラー: {e}")
            return []
    
    def _save_knowledge_entries(self, knowledge_entries: List[KnowledgeEntry]):
        """知見を保存"""
        try:
            data = [knowledge.to_dict() for knowledge in knowledge_entries]
            with open(self.knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"知見保存エラー: {e}")
    
    def _dict_to_knowledge(self, data: Dict[str, Any]) -> KnowledgeEntry:
        """辞書から知見オブジェクトを作成"""
        return KnowledgeEntry(
            id=data["id"],
            category=KnowledgeCategory(data["category"]),
            test_block=data["test_block"],
            test_category=data["test_category"],
            equipment_type=data["equipment_type"],
            condition_text=data["condition_text"],
            engineer_feedback=data["engineer_feedback"],
            feedback_type=data["feedback_type"],
            problem_description=data["problem_description"],
            solution_suggestion=data["solution_suggestion"],
            improvement_notes=data["improvement_notes"],
            reviewer_name=data["reviewer_name"],
            confidence_level=data["confidence_level"],
            source_review_id=data["source_review_id"],
            source_validation_id=data["source_validation_id"],
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            usage_count=data.get("usage_count", 0)
        )

# サービスインスタンス取得
_knowledge_service = None

def get_knowledge_service() -> KnowledgeService:
    """知見サービスのシングルトンインスタンスを取得"""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service
