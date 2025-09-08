"""
簡易化されたモック設備シミュレータ
Simplified Mock Equipment Simulator

統一的なデータ通信機能で、90%成功・10%失敗のランダム応答を提供
どんな検証項目でも対応可能な汎用的な設計
"""
import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

class ResponseType(Enum):
    """応答タイプ"""
    SUCCESS = "success"
    FAILURE = "failure"

class FailureReason(Enum):
    """失敗理由"""
    COMMUNICATION_TIMEOUT = "通信タイムアウト"
    FUNCTION_NOT_SUPPORTED = "機能未対応"
    CONFIGURATION_ERROR = "設定不備"
    HARDWARE_ERROR = "ハードウェア異常"
    AUTHENTICATION_FAILED = "認証失敗"
    RESOURCE_UNAVAILABLE = "リソース不足"

class SimplifiedEquipmentSimulator:
    """簡易化された設備シミュレータ"""
    
    def __init__(self, equipment_id: str):
        self.equipment_id = equipment_id
        self.vendor = self._get_vendor_from_id(equipment_id)
        self.model = self._get_model_from_id(equipment_id)
        self.success_rate = 0.9  # 90%成功率
        
    def _get_vendor_from_id(self, equipment_id: str) -> str:
        """設備IDからベンダーを判定"""
        if "Ericsson" in equipment_id:
            return "Ericsson"
        elif "Samsung" in equipment_id:
            return "Samsung"
        else:
            return "Unknown"
    
    def _get_model_from_id(self, equipment_id: str) -> str:
        """設備IDからモデルを判定"""
        if "MMU" in equipment_id:
            return "MMU"
        elif "RRU" in equipment_id:
            return "RRU"
        elif "AUv1" in equipment_id:
            return "AU v1"
        elif "AUv2" in equipment_id:
            return "AU v2"
        else:
            return "Unknown"
    
    def execute_command(self, command: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        統一的なコマンド実行
        どんなコマンドでも同じデータ形式で応答
        """
        # 実行時間をシミュレート
        execution_time = random.uniform(0.5, 3.0)
        time.sleep(0.1)  # 軽微な遅延
        
        # 90%の確率で成功、10%の確率で失敗
        is_success = random.random() < self.success_rate
        
        if is_success:
            return self._generate_success_response(command, execution_time)
        else:
            return self._generate_failure_response(command, execution_time)
    
    def _generate_success_response(self, command: str, execution_time: float) -> Dict[str, Any]:
        """成功応答を生成"""
        base_response = {
            "status": "success",
            "equipment_id": self.equipment_id,
            "vendor": self.vendor,
            "model": self.model,
            "timestamp": datetime.now().isoformat(),
            "execution_time": execution_time,
            "command": command
        }
        
        # 汎用的なデータを追加
        base_response.update({
            "data": {
                "cell_id": f"CELL_{random.randint(1000, 9999)}",
                "frequency_mhz": random.choice([700, 850, 1800, 2100, 2600, 3500]),
                "bandwidth_mhz": random.choice([5, 10, 15, 20]),
                "signal_strength_dbm": round(random.uniform(-120, -60), 1),
                "active_users": random.randint(0, 200),
                "throughput_mbps": round(random.uniform(50, 1000), 1),
                "error_rate_percent": round(random.uniform(0, 5), 3),
                "temperature_celsius": round(random.uniform(20, 45), 1),
                "power_consumption_watts": round(random.uniform(100, 500), 1)
            },
            "configuration": {
                "enabled": True,
                "mode": random.choice(["normal", "power_save", "high_performance"]),
                "priority": random.randint(1, 10),
                "max_users": random.randint(100, 500)
            },
            "performance_metrics": {
                "cpu_usage_percent": round(random.uniform(10, 80), 1),
                "memory_usage_percent": round(random.uniform(20, 70), 1),
                "uptime_hours": random.randint(1, 8760),
                "packet_loss_percent": round(random.uniform(0, 2), 3)
            }
        })
        
        # ベンダー固有の追加データ
        if self.vendor == "Ericsson":
            base_response["ericsson_specific"] = {
                "rbs_id": f"RBS_{random.randint(100, 999)}",
                "carrier_aggregation": random.choice([True, False]),
                "mimo_layers": random.choice([2, 4, 8])
            }
        elif self.vendor == "Samsung":
            base_response["samsung_specific"] = {
                "au_id": f"AU_{random.randint(100, 999)}",
                "beamforming_enabled": random.choice([True, False]),
                "advanced_features": {
                    "adaptive_sleep": random.choice([True, False]),
                    "traffic_prediction": random.choice([True, False])
                }
            }
        
        return base_response
    
    def _generate_failure_response(self, command: str, execution_time: float) -> Dict[str, Any]:
        """失敗応答を生成"""
        failure_reason = random.choice(list(FailureReason))
        
        return {
            "status": "error",
            "equipment_id": self.equipment_id,
            "vendor": self.vendor,
            "model": self.model,
            "timestamp": datetime.now().isoformat(),
            "execution_time": execution_time,
            "command": command,
            "error_code": f"ERR_{random.randint(1000, 9999)}",
            "error_message": failure_reason.value,
            "error_details": self._get_failure_details(failure_reason),
            "retry_possible": random.choice([True, False]),
            "estimated_recovery_time": random.randint(1, 60)  # 分
        }
    
    def _get_failure_details(self, failure_reason: FailureReason) -> str:
        """失敗理由の詳細を取得"""
        details_map = {
            FailureReason.COMMUNICATION_TIMEOUT: "ネットワーク接続がタイムアウトしました。設備との通信を確認してください。",
            FailureReason.FUNCTION_NOT_SUPPORTED: "要求された機能はこの設備でサポートされていません。",
            FailureReason.CONFIGURATION_ERROR: "設備の設定に問題があります。設定値を確認してください。",
            FailureReason.HARDWARE_ERROR: "ハードウェアに異常が検出されました。保守が必要です。",
            FailureReason.AUTHENTICATION_FAILED: "認証に失敗しました。アクセス権限を確認してください。",
            FailureReason.RESOURCE_UNAVAILABLE: "必要なリソースが不足しています。システム負荷を確認してください。"
        }
        return details_map.get(failure_reason, "不明なエラーが発生しました。")

class SimplifiedMockEquipmentManager:
    """簡易化されたモック設備管理クラス"""
    
    def __init__(self):
        self.simulators = {}
        self._initialize_simulators()
    
    def _initialize_simulators(self):
        """シミュレータを初期化"""
        equipment_list = [
            "Ericsson-MMU-001",
            "Ericsson-RRU-001", 
            "Samsung-AUv1-001",
            "Samsung-AUv2-001"
        ]
        
        for equipment_id in equipment_list:
            self.simulators[equipment_id] = SimplifiedEquipmentSimulator(equipment_id)
    
    def execute_command(self, equipment_type: str, command: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        統一的なコマンド実行インターフェース
        設備タイプに関係なく同じ形式で応答
        """
        # 設備タイプから実際の設備IDを決定
        equipment_id = self._get_equipment_id(equipment_type)
        
        if equipment_id not in self.simulators:
            return {
                "status": "error",
                "equipment_id": equipment_id,
                "timestamp": datetime.now().isoformat(),
                "error_code": "EQUIPMENT_NOT_FOUND",
                "error_message": f"設備が見つかりません: {equipment_type}",
                "command": command
            }
        
        simulator = self.simulators[equipment_id]
        return simulator.execute_command(command, parameters)
    
    def _get_equipment_id(self, equipment_type: str) -> str:
        """設備タイプから設備IDを取得"""
        type_mapping = {
            "Ericsson-MMU": "Ericsson-MMU-001",
            "Ericsson-RRU": "Ericsson-RRU-001",
            "Samsung-AUv1": "Samsung-AUv1-001", 
            "Samsung-AUv2": "Samsung-AUv2-001"
        }
        return type_mapping.get(equipment_type, equipment_type)
    
    def get_available_equipment(self) -> List[str]:
        """利用可能な設備一覧を取得"""
        return list(self.simulators.keys())
    
    def get_equipment_status(self, equipment_id: str) -> Dict[str, Any]:
        """設備ステータスを取得"""
        if equipment_id in self.simulators:
            simulator = self.simulators[equipment_id]
            return {
                "equipment_id": equipment_id,
                "vendor": simulator.vendor,
                "model": simulator.model,
                "status": "active",
                "success_rate": simulator.success_rate,
                "last_update": datetime.now().isoformat()
            }
        else:
            return {
                "equipment_id": equipment_id,
                "status": "not_found",
                "error": "Equipment not found"
            }

# グローバルインスタンス
simplified_mock_equipment_manager = SimplifiedMockEquipmentManager()

def get_simplified_mock_equipment_manager():
    """簡易化されたモック設備管理インスタンスを取得"""
    return simplified_mock_equipment_manager

