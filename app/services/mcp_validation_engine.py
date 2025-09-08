#!/usr/bin/env python3
"""
MCP Validation Engine

MCPエージェントと従来のValidation Engineを統合するクラス
プロバイダーに応じて実行方式を自動切り替え
"""

import sys
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.models.validation import ValidationBatch, ValidationResult, TestItem, EquipmentType
import uuid
from app.services.validation_engine import ValidationEngine
from app.services.real_mcp_agent import get_real_mcp_agent

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnifiedValidationEngine:
    """統合検証エンジン - MCPと従来実装を統合"""
    
    def __init__(self, llm_provider: str = "ollama"):
        self.llm_provider = llm_provider
        self.is_mcp_supported = llm_provider in ["anthropic", "openai", "bedrock"]
        
        if self.is_mcp_supported:
            logger.info(f"真のMCP対応プロバイダー '{llm_provider}' を使用")
            self.mcp_agent = get_real_mcp_agent(llm_provider)
            self.traditional_engine = None
        else:
            logger.info(f"従来実装プロバイダー '{llm_provider}' を使用")
            self.mcp_agent = None
            self.traditional_engine = ValidationEngine(llm_provider)
    
    def create_batch_from_test_items(self, test_items: List[TestItem], batch_name: str) -> ValidationBatch:
        """テスト項目からバッチを作成"""
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return ValidationBatch(
            id=batch_id,
            name=batch_name,
            test_items=test_items,
            created_at=datetime.now()
        )
    
    async def execute_batch_async(self, batch: ValidationBatch, progress_callback: Optional[Callable] = None) -> ValidationBatch:
        """バッチを非同期実行"""
        if self.is_mcp_supported:
            return await self._execute_with_mcp(batch, progress_callback)
        else:
            return await self._execute_with_traditional(batch, progress_callback)
    
    def execute_batch(self, batch: ValidationBatch, progress_callback: Optional[Callable] = None) -> ValidationBatch:
        """バッチを同期実行"""
        if self.is_mcp_supported:
            # MCPの場合は非同期実行をラップ
            return asyncio.run(self._execute_with_mcp(batch, progress_callback))
        else:
            # 従来実装の場合は同期実行
            return self._execute_with_traditional_sync(batch, progress_callback)
    
    async def _execute_with_mcp(self, batch: ValidationBatch, progress_callback: Optional[Callable] = None) -> ValidationBatch:
        """MCP エージェントで実行"""
        logger.info(f"MCP実行開始: {batch.name}")
        
        try:
            # 進捗コールバック（開始）
            if progress_callback:
                progress_callback(0.0, None)
            
            # MCPエージェントで実行
            result_batch = await self.mcp_agent.execute_validation_batch(batch, progress_callback)
            
            # 進捗コールバック（各結果）
            if progress_callback:
                total_items = len(result_batch.test_items)
                for i, result in enumerate(result_batch.results):
                    progress = (i + 1) / total_items
                    progress_callback(progress, result)
            
            logger.info(f"MCP実行完了: {len(result_batch.results)}件")
            return result_batch
            
        except Exception as e:
            logger.error(f"MCP実行エラー: {e}")
            # エラーの場合は失敗結果を作成
            batch.results = self._create_error_results(batch.test_items, str(e))
            batch.completed_at = datetime.now()
            return batch
    
    async def _execute_with_traditional(self, batch: ValidationBatch, progress_callback: Optional[Callable] = None) -> ValidationBatch:
        """従来エンジンで非同期実行"""
        # 従来エンジンを非同期でラップ
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self._execute_with_traditional_sync, 
            batch, 
            progress_callback
        )
    
    def _execute_with_traditional_sync(self, batch: ValidationBatch, progress_callback: Optional[Callable] = None) -> ValidationBatch:
        """従来エンジンで同期実行"""
        logger.info(f"従来実行開始: {batch.name}")
        
        try:
            # 進捗コールバック（開始）
            if progress_callback:
                progress_callback(0.0, None)
            
            # 従来のValidation Engineで実行
            result_batch = self.traditional_engine.execute_batch(batch, progress_callback)
            
            logger.info(f"従来実行完了: {len(result_batch.results)}件")
            return result_batch
            
        except Exception as e:
            logger.error(f"従来実行エラー: {e}")
            # エラーの場合は失敗結果を作成
            batch.results = self._create_error_results(batch.test_items, str(e))
            batch.completed_at = datetime.now()
            return batch
    
    def _create_error_results(self, test_items: List[TestItem], error_message: str) -> List[ValidationResult]:
        """エラー時の結果を作成"""
        from app.models.validation import TestResult
        
        error_results = []
        for item in test_items:
            # テストアイテムの最初の設備を使用、なければデフォルト
            equipment_type = EquipmentType.TAKANAWA_ERICSSON  # デフォルト
            if item.condition.equipment_types:
                first_equipment = item.condition.equipment_types[0]
                if hasattr(first_equipment, 'value'):
                    equipment_type = first_equipment
                else:
                    # 文字列の場合、対応するEquipmentTypeを検索
                    for et in EquipmentType:
                        if et.value == str(first_equipment):
                            equipment_type = et
                            break
            
            result = ValidationResult(
                id=str(uuid.uuid4()),
                test_item_id=item.id,
                equipment_type=equipment_type,
                result=TestResult.FAIL,
                details=f"実行エラー: {error_message}",
                confidence=0.0,
                execution_time=0.0,
                created_at=datetime.now()
            )
            error_results.append(result)
        
        return error_results
    
    def get_execution_method(self) -> str:
        """現在の実行方式を取得"""
        if self.is_mcp_supported:
            return f"MCP Agent ({self.llm_provider})"
        else:
            return f"Traditional Engine ({self.llm_provider})"
    
    def get_capabilities(self) -> Dict[str, Any]:
        """エンジンの機能情報を取得"""
        return {
            "provider": self.llm_provider,
            "execution_method": "MCP Agent" if self.is_mcp_supported else "Traditional Engine",
            "mcp_supported": self.is_mcp_supported,
            "autonomous_execution": self.is_mcp_supported,
            "features": {
                "autonomous_command_selection": self.is_mcp_supported,
                "real_time_decision_making": self.is_mcp_supported,
                "equipment_interaction": True,
                "result_analysis": True,
                "batch_processing": True
            }
        }
    
    def get_equipment_summary(self, batch: ValidationBatch) -> Dict[str, Dict[str, Any]]:
        """設備別サマリーを取得"""
        if self.traditional_engine:
            return self.traditional_engine.get_equipment_summary(batch)
        else:
            # MCP用の簡易実装
            equipment_summary = {}
            
            for result in batch.results:
                eq_type = result.equipment_type
                if eq_type not in equipment_summary:
                    equipment_summary[eq_type] = {
                        "total": 0,
                        "pass": 0,
                        "fail": 0,
                        "warning": 0,
                        "success_rate": 0.0
                    }
                
                equipment_summary[eq_type]["total"] += 1
                
                if result.result.value == "PASS":
                    equipment_summary[eq_type]["pass"] += 1
                elif result.result.value == "FAIL":
                    equipment_summary[eq_type]["fail"] += 1
                elif result.result.value == "WARNING":
                    equipment_summary[eq_type]["warning"] += 1
            
            # 成功率を計算
            for eq_type, stats in equipment_summary.items():
                if stats["total"] > 0:
                    stats["success_rate"] = stats["pass"] / stats["total"]
            
            return equipment_summary

def get_unified_validation_engine(llm_provider: str = "ollama") -> UnifiedValidationEngine:
    """統合検証エンジンのファクトリー関数"""
    return UnifiedValidationEngine(llm_provider)

# 使用例とテスト
async def main():
    """テスト用のメイン関数"""
    try:
        # 各プロバイダーでテスト
        providers = ["ollama", "anthropic", "openai"]
        
        for provider in providers:
            print(f"\n=== {provider} プロバイダーのテスト ===")
            
            try:
                engine = get_unified_validation_engine(provider)
                capabilities = engine.get_capabilities()
                
                print(f"実行方式: {capabilities['execution_method']}")
                print(f"MCP対応: {capabilities['mcp_supported']}")
                print(f"自律実行: {capabilities['autonomous_execution']}")
                
                # テスト用のバッチを作成
                from app.models.validation import TestItem, TestCondition, TestCategory, EquipmentType
                
                test_item = TestItem(
                    id=f"test_{provider}_001",
                    test_block="基地局スリープ機能",
                    category=TestCategory.NORMAL,
                    condition=TestCondition(
                        condition_text="CMデータの取得成功",
                        expected_count=1,
                        equipment_types=[EquipmentType.TAKANAWA_ERICSSON]
                    ),
                    scenarios=["正常スリープ"]
                )
                
                batch = engine.create_batch_from_test_items([test_item], f"テストバッチ_{provider}")
                
                print(f"バッチ作成完了: {batch.name}")
                
            except Exception as e:
                print(f"エラー: {e}")
        
    except Exception as e:
        logger.error(f"テスト実行エラー: {e}")

if __name__ == "__main__":
    asyncio.run(main())
