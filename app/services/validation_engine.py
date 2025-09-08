"""
検証実行エンジン
Validation Execution Engine

検証項目を実行し、結果を分析するエンジン
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from app.models.validation import (
    TestItem, ValidationResult, ValidationBatch, ValidationStatus, 
    TestResult, EquipmentType, ReviewStatus
)
from app.services.llm_service import get_llm_service
from app.services.review_service import get_review_service
from mock_equipment.simplified_equipment_simulator import get_simplified_mock_equipment_manager

logger = logging.getLogger(__name__)

class ValidationEngine:
    """検証実行エンジン"""
    
    def __init__(self, llm_provider: str = "ollama"):
        self.llm_service = get_llm_service(llm_provider)
        self.mock_equipment = get_simplified_mock_equipment_manager()
        self.review_service = get_review_service()
        self.max_workers = 3  # 並列実行数
    
    def execute_test_item(self, test_item: TestItem, equipment_type: EquipmentType) -> ValidationResult:
        """単一の検証項目を実行"""
        result_id = str(uuid.uuid4())
        start_time = time.time()
        
        logger.info(f"Executing test: {test_item.id} - {equipment_type.value}")
        
        try:
            # モック設備にコマンド送信
            command = self._determine_command(test_item.category.value)
            equipment_response = self.mock_equipment.execute_command(
                equipment_type.value, 
                command
            )
            
            # LLMで結果分析（実行時間計測はここまで含める）
            analysis = self.llm_service.analyze_validation_result(
                test_item.to_dict(),
                equipment_response
            )
            
            execution_time = time.time() - start_time
            
            # 結果判定
            test_result = TestResult(analysis.get('result', 'FAIL'))
            confidence = analysis.get('confidence', 0.5)
            
            # LLM分析の詳細を取得
            analysis_details = analysis.get('analysis', 'LLMによる分析結果')
            recommendations = analysis.get('recommendations', [])
            issues = analysis.get('issues', [])
            
            # 判定根拠を作成
            details_parts = [analysis_details]
            if issues:
                details_parts.append(f"問題点: {'; '.join(issues)}")
            if recommendations:
                details_parts.append(f"推奨事項: {'; '.join(recommendations)}")
            
            details = ' | '.join(details_parts)
            
            # エラーメッセージの処理
            error_message = None
            if equipment_response.get('status') == 'error':
                error_message = equipment_response.get('error_message', 'Unknown error')
            elif test_result == TestResult.FAIL:
                if issues:
                    error_message = '; '.join(issues)
            
            # レビューステータスを設定
            review_status = ReviewStatus.NOT_REQUIRED
            if test_result in [TestResult.FAIL, TestResult.NEEDS_CHECK]:
                review_status = ReviewStatus.NEEDS_REVIEW
            
            validation_result = ValidationResult(
                id=result_id,
                test_item_id=test_item.id,
                equipment_type=equipment_type,
                result=test_result,
                details=details,  # LLM判定根拠を追加
                response_data=equipment_response,
                execution_time=execution_time,
                error_message=error_message,
                confidence=confidence,
                review_status=review_status
            )
            
            return validation_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Test execution failed: {e}")
            
            return ValidationResult(
                id=result_id,
                test_item_id=test_item.id,
                equipment_type=equipment_type,
                result=TestResult.FAIL,
                details=f"検証実行中にエラーが発生しました: {str(e)}",
                response_data={"status": "error", "error": str(e)},
                execution_time=execution_time,
                error_message=f"実行エラー: {str(e)}",
                confidence=0.0
            )
    
    def _determine_command(self, category: str) -> str:
        """統一的なコマンドを決定（簡易化）"""
        # すべての検証項目に対して統一的なコマンドを使用
        return "execute_validation"
    
    def execute_batch(self, batch: ValidationBatch, progress_callback: Optional[callable] = None) -> ValidationBatch:
        """バッチ検証を実行"""
        logger.info(f"Starting batch execution: {batch.id}")
        
        batch.status = ValidationStatus.RUNNING
        batch.started_at = datetime.now()
        
        try:
            # 実行タスクを準備（検証項目 × 設備のみ）
            tasks = []
            for test_item in batch.test_items:
                for equipment_type in test_item.condition.equipment_types:
                    tasks.append((test_item, equipment_type))
            
            total_tasks = len(tasks)
            completed_tasks = 0
            
            # 並列実行
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # タスクを投入
                future_to_task = {
                    executor.submit(self.execute_test_item, test_item, equipment_type): (test_item, equipment_type)
                    for test_item, equipment_type in tasks
                }
                
                # 結果を収集
                for future in as_completed(future_to_task):
                    try:
                        result = future.result()
                        batch.results.append(result)
                        completed_tasks += 1
                        
                        # 進捗コールバック
                        if progress_callback:
                            progress = completed_tasks / total_tasks
                            progress_callback(progress, result)
                        
                        logger.info(f"Task completed: {completed_tasks}/{total_tasks}")
                        
                    except Exception as e:
                        logger.error(f"Task failed: {e}")
                        completed_tasks += 1
            
            batch.status = ValidationStatus.COMPLETED
            batch.completed_at = datetime.now()
            
            logger.info(f"Batch execution completed: {batch.id}")
            
        except Exception as e:
            logger.error(f"Batch execution failed: {e}")
            batch.status = ValidationStatus.FAILED
            batch.completed_at = datetime.now()
        
        return batch
    
    async def execute_batch_async(self, batch: ValidationBatch, progress_callback: Optional[callable] = None) -> ValidationBatch:
        """非同期バッチ検証を実行"""
        logger.info(f"Starting async batch execution: {batch.id}")
        
        batch.status = ValidationStatus.RUNNING
        batch.started_at = datetime.now()
        
        try:
            # 実行タスクを準備
            tasks = []
            for test_item in batch.test_items:
                for scenario in test_item.scenarios:
                    for equipment_type in test_item.condition.equipment_types:
                        tasks.append((test_item, scenario, equipment_type))
            
            total_tasks = len(tasks)
            completed_tasks = 0
            
            # 非同期実行
            semaphore = asyncio.Semaphore(self.max_workers)
            
            async def execute_with_semaphore(test_item, scenario, equipment_type):
                async with semaphore:
                    # 同期関数を非同期で実行
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        None, 
                        self.execute_test_item, 
                        test_item, scenario, equipment_type
                    )
            
            # すべてのタスクを並列実行
            async_tasks = [
                execute_with_semaphore(test_item, scenario, equipment_type)
                for test_item, scenario, equipment_type in tasks
            ]
            
            # 結果を順次収集
            for coro in asyncio.as_completed(async_tasks):
                try:
                    result = await coro
                    batch.results.append(result)
                    completed_tasks += 1
                    
                    # 進捗コールバック
                    if progress_callback:
                        progress = completed_tasks / total_tasks
                        progress_callback(progress, result)
                    
                    logger.info(f"Async task completed: {completed_tasks}/{total_tasks}")
                    
                except Exception as e:
                    logger.error(f"Async task failed: {e}")
                    completed_tasks += 1
            
            batch.status = ValidationStatus.COMPLETED
            batch.completed_at = datetime.now()
            
            logger.info(f"Async batch execution completed: {batch.id}")
            
        except Exception as e:
            logger.error(f"Async batch execution failed: {e}")
            batch.status = ValidationStatus.FAILED
            batch.completed_at = datetime.now()
        
        return batch
    
    def create_batch_from_test_items(self, test_items: List[TestItem], batch_name: str = None) -> ValidationBatch:
        """検証項目からバッチを作成"""
        batch_id = str(uuid.uuid4())
        if not batch_name:
            batch_name = f"検証バッチ_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return ValidationBatch(
            id=batch_id,
            name=batch_name,
            test_items=test_items
        )
    
    def get_batch_summary(self, batch: ValidationBatch) -> Dict[str, Any]:
        """バッチサマリーを取得"""
        if not batch.results:
            return {
                "total_tests": 0,
                "completed_tests": 0,
                "pass_count": 0,
                "fail_count": 0,
                "warning_count": 0,
                "success_rate": 0.0,
                "average_execution_time": 0.0,
                "status": batch.status.value
            }
        
        total_tests = len(batch.results)
        pass_count = sum(1 for r in batch.results if r.result == TestResult.PASS)
        fail_count = sum(1 for r in batch.results if r.result == TestResult.FAIL)
        warning_count = sum(1 for r in batch.results if r.result == TestResult.WARNING)
        
        success_rate = pass_count / total_tests if total_tests > 0 else 0.0
        avg_execution_time = sum(r.execution_time for r in batch.results) / total_tests
        
        return {
            "total_tests": total_tests,
            "completed_tests": total_tests,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "warning_count": warning_count,
            "success_rate": success_rate,
            "average_execution_time": avg_execution_time,
            "status": batch.status.value,
            "started_at": batch.started_at.isoformat() if batch.started_at else None,
            "completed_at": batch.completed_at.isoformat() if batch.completed_at else None
        }
    
    def get_equipment_summary(self, batch: ValidationBatch) -> Dict[str, Any]:
        """設備別サマリーを取得"""
        equipment_stats = {}
        
        for result in batch.results:
            eq_type = result.equipment_type.value if hasattr(result.equipment_type, 'value') else str(result.equipment_type)
            if eq_type not in equipment_stats:
                equipment_stats[eq_type] = {
                    "total": 0,
                    "pass": 0,
                    "fail": 0,
                    "warning": 0,
                    "avg_execution_time": 0.0,
                    "avg_confidence": 0.0
                }
            
            stats = equipment_stats[eq_type]
            stats["total"] += 1
            
            if result.result == TestResult.PASS:
                stats["pass"] += 1
            elif result.result == TestResult.FAIL:
                stats["fail"] += 1
            elif result.result == TestResult.WARNING:
                stats["warning"] += 1
            
            stats["avg_execution_time"] += result.execution_time
            stats["avg_confidence"] += result.confidence
        
        # 平均値を計算
        for eq_type, stats in equipment_stats.items():
            if stats["total"] > 0:
                stats["avg_execution_time"] /= stats["total"]
                stats["avg_confidence"] /= stats["total"]
                stats["success_rate"] = stats["pass"] / stats["total"]
        
        return equipment_stats

# グローバルエンジンインスタンス
def get_validation_engine(llm_provider: str = "ollama") -> ValidationEngine:
    """検証エンジンインスタンスを取得"""
    return ValidationEngine(llm_provider=llm_provider)
