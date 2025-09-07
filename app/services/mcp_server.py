#!/usr/bin/env python3
"""
Lab Validation MCP Server

FastMCPを使用したラボ検証自動化システム用のMCPサーバー
Claude/OpenAIのAIエージェントがラボ設備の検証を自律的に実行するためのツールを提供
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    print("FastAPIがインストールされていません。pip install fastapi を実行してください。")
    sys.exit(1)

from app.models.validation import TestItem, TestCondition, ValidationResult, TestResult, EquipmentType
from app.models.database import db_manager
from mock_equipment.simplified_equipment_simulator import get_simplified_mock_equipment_manager

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPIアプリケーション（MCP API用）
app = FastAPI(title="Lab Validation MCP Server", version="1.0.0")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/mcp/get_test_items")
def get_test_items() -> Dict[str, Any]:
    """
    データベースから検証項目一覧を取得
    
    Returns:
        Dict: 検証項目のリストと詳細情報
    """
    try:
        with db_manager.get_session() as session:
            # 検証項目を取得（実際の実装では適切なクエリを使用）
            test_items = []
            
            # サンプルデータを返す（実際の実装では DB から取得）
            sample_items = [
                {
                    "id": "test_001",
                    "test_block": "基地局スリープ機能",
                    "category": "正常系",
                    "condition": "CMデータの取得成功",
                    "expected_count": 1,
                    "equipment_types": ["ERICSSON_MMU", "SAMSUNG_AUV1"],
                    "scenarios": ["正常スリープ", "スリープ復帰"]
                },
                {
                    "id": "test_002", 
                    "test_block": "基地局スリープ機能",
                    "category": "異常系",
                    "condition": "異常データでのエラー処理",
                    "expected_count": 0,
                    "equipment_types": ["ERICSSON_RRU"],
                    "scenarios": ["異常データ入力", "タイムアウト"]
                }
            ]
            
            return {
                "status": "success",
                "test_items": sample_items,
                "total_count": len(sample_items),
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"検証項目取得エラー: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/mcp/send_command_to_equipment")
def send_command_to_equipment(equipment_id: str, command: str, parameters: Optional[Dict] = None) -> Dict[str, Any]:
    """
    ラボ設備にコマンドを送信して応答を取得
    
    Args:
        equipment_id: 設備ID (例: "ERICSSON_MMU_001")
        command: 実行するコマンド (例: "get_signal_strength", "check_sleep_status")
        parameters: コマンドパラメータ (オプション)
    
    Returns:
        Dict: 設備からの応答データ
    """
    try:
        logger.info(f"設備 {equipment_id} にコマンド '{command}' を送信")
        
        # パラメータのデフォルト値設定
        if parameters is None:
            parameters = {}
            
        # 簡易化されたモック設備システムを使用してコマンド実行
        mock_equipment_manager = get_simplified_mock_equipment_manager()
        response = mock_equipment_manager.execute_command(equipment_id, command, parameters)
        
        return {
            "status": "success",
            "equipment_id": equipment_id,
            "command": command,
            "parameters": parameters,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"設備コマンド実行エラー: {e}")
        return {
            "status": "error",
            "equipment_id": equipment_id,
            "command": command,
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/mcp/analyze_test_result")
def analyze_test_result(test_item_id: str, equipment_response: Dict, expected_criteria: Dict) -> Dict[str, Any]:
    """
    検証結果を分析して合否を判定
    
    Args:
        test_item_id: 検証項目ID
        equipment_response: 設備からの応答データ
        expected_criteria: 期待される条件・基準
    
    Returns:
        Dict: 分析結果と判定
    """
    try:
        logger.info(f"検証項目 {test_item_id} の結果を分析中")
        
        # 基本的な分析ロジック
        result = TestResult.PASS
        confidence = 0.9
        details = []
        
        # 設備応答の確認
        if equipment_response.get("status") != "success":
            result = TestResult.FAIL
            confidence = 0.95
            details.append("設備からの応答でエラーが発生")
        else:
            response_data = equipment_response.get("response", {})
            parsed_data = response_data.get("parsed_data", {})
            
            # 期待基準との比較
            for criterion, expected_value in expected_criteria.items():
                actual_value = parsed_data.get(criterion)
                
                if actual_value is None:
                    result = TestResult.WARNING
                    confidence = min(confidence, 0.7)
                    details.append(f"{criterion}の値が取得できませんでした")
                elif isinstance(expected_value, dict):
                    # 範囲チェック
                    min_val = expected_value.get("min")
                    max_val = expected_value.get("max")
                    
                    if min_val is not None and actual_value < min_val:
                        result = TestResult.FAIL
                        confidence = 0.9
                        details.append(f"{criterion}: {actual_value} < {min_val} (期待最小値)")
                    elif max_val is not None and actual_value > max_val:
                        result = TestResult.FAIL
                        confidence = 0.9
                        details.append(f"{criterion}: {actual_value} > {max_val} (期待最大値)")
                    else:
                        details.append(f"{criterion}: {actual_value} (正常範囲内)")
                else:
                    # 完全一致チェック
                    if actual_value != expected_value:
                        result = TestResult.FAIL
                        confidence = 0.9
                        details.append(f"{criterion}: {actual_value} != {expected_value} (期待値)")
                    else:
                        details.append(f"{criterion}: {actual_value} (期待値と一致)")
        
        return {
            "status": "success",
            "test_item_id": test_item_id,
            "result": result.value,
            "confidence": confidence,
            "details": details,
            "analysis_summary": f"検証結果: {result.value} (信頼度: {confidence:.1%})",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"結果分析エラー: {e}")
        return {
            "status": "error",
            "test_item_id": test_item_id,
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/mcp/save_validation_result")
def save_validation_result(test_item_id: str, result_data: Dict) -> Dict[str, Any]:
    """
    検証結果をデータベースに保存
    
    Args:
        test_item_id: 検証項目ID
        result_data: 保存する結果データ
    
    Returns:
        Dict: 保存結果
    """
    try:
        logger.info(f"検証結果を保存中: {test_item_id}")
        
        # 実際の実装ではデータベースに保存
        # ここではログ出力のみ
        logger.info(f"保存データ: {json.dumps(result_data, indent=2, ensure_ascii=False)}")
        
        return {
            "status": "success",
            "test_item_id": test_item_id,
            "message": "検証結果を正常に保存しました",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"結果保存エラー: {e}")
        return {
            "status": "error",
            "test_item_id": test_item_id,
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/mcp/get_equipment_status")
def get_equipment_status() -> Dict[str, Any]:
    """
    利用可能な設備の状態を取得
    
    Returns:
        Dict: 設備状態の一覧
    """
    try:
        equipment_status = mock_equipment_manager.get_equipment_status()
        
        return {
            "status": "success",
            "equipment_status": equipment_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"設備状態取得エラー: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/mcp/create_validation_batch")
def create_validation_batch(batch_name: str, test_item_ids: List[str]) -> Dict[str, Any]:
    """
    検証バッチを作成
    
    Args:
        batch_name: バッチ名
        test_item_ids: 実行する検証項目のIDリスト
    
    Returns:
        Dict: 作成されたバッチ情報
    """
    try:
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return {
            "status": "success",
            "batch_id": batch_id,
            "batch_name": batch_name,
            "test_item_ids": test_item_ids,
            "created_at": datetime.now().isoformat(),
            "message": f"バッチ '{batch_name}' を作成しました"
        }
        
    except Exception as e:
        logger.error(f"バッチ作成エラー: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

# HTTP APIエンドポイント
@app.post("/mcp/call")
async def call_mcp_tool(request: Dict[str, Any]):
    """MCPツールを呼び出すHTTPエンドポイント"""
    try:
        tool_name = request.get("tool")
        parameters = request.get("parameters", {})
        
        logger.info(f"MCP tool call: {tool_name} with params: {parameters}")
        
        # ツール名に基づいて適切な関数を呼び出し
        if tool_name == "get_test_items":
            result = get_test_items()
        elif tool_name == "send_command_to_equipment":
            result = send_command_to_equipment(
                equipment_id=parameters.get("equipment_id"),
                command=parameters.get("command"),
                parameters=parameters.get("parameters")
            )
        elif tool_name == "analyze_test_result":
            result = analyze_test_result(
                test_item_id=parameters.get("test_item_id", ""),
                equipment_response=parameters.get("test_data", {}),
                expected_criteria={"expected_result": parameters.get("expected_result", "")}
            )
        elif tool_name == "save_validation_result":
            result = save_validation_result(
                test_item_id=parameters.get("test_item_id"),
                result_data=parameters
            )
        else:
            return {
                "status": "error",
                "message": f"Unknown tool: {tool_name}",
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"MCP tool call error: {e}")
        return {
            "status": "error", 
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "service": "Lab Validation MCP Server",
        "timestamp": datetime.now().isoformat()
    }

def main():
    """MCPサーバーを起動"""
    logger.info("Lab Validation MCP Server を起動中...")
    
    # データベース初期化
    try:
        db_manager.create_tables()
        logger.info("データベース初期化完了")
    except Exception as e:
        logger.error(f"データベース初期化エラー: {e}")
    
    # FastAPIサーバーを起動
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    main()
