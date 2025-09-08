"""
モック設備シミュレータ
Mock Equipment Simulator

実際のネットワーク設備を模擬したシミュレータ
SNMP MIB形式とJSON形式の応答データを生成

参考資料:
- SNMP MIB: https://www.seil.jp/sx4/doc/sa/snmp/snmp-mib.html
- 基地局管理: https://docs.oracle.com/cd/E23846_01/tuxedo/docs11gr1/snmpmref/1tmib.html
"""
import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

class EquipmentStatus(Enum):
    """設備ステータス"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error"

@dataclass
class SNMPResponse:
    """SNMP応答データ"""
    oid: str                    # Object Identifier
    value: Any                  # 値
    data_type: str             # データタイプ
    timestamp: datetime        # タイムスタンプ

class BaseEquipmentSimulator:
    """基地局設備シミュレータ基底クラス"""
    
    def __init__(self, equipment_id: str, vendor: str, model: str):
        self.equipment_id = equipment_id
        self.vendor = vendor
        self.model = model
        self.status = EquipmentStatus.ACTIVE
        self.last_update = datetime.now()
        
        # 基本的なSNMP MIBオブジェクト
        self.base_oids = {
            "1.3.6.1.2.1.1.1.0": f"{vendor} {model}",  # sysDescr
            "1.3.6.1.2.1.1.2.0": "1.3.6.1.4.1.193",   # sysObjectID
            "1.3.6.1.2.1.1.3.0": self._get_uptime(),   # sysUpTime
            "1.3.6.1.2.1.1.4.0": "KDDI Lab Admin",     # sysContact
            "1.3.6.1.2.1.1.5.0": equipment_id,         # sysName
            "1.3.6.1.2.1.1.6.0": "Tokyo Lab",          # sysLocation
        }
    
    def _get_uptime(self) -> int:
        """システム稼働時間を取得（1/100秒単位）"""
        uptime_seconds = random.randint(3600, 86400 * 30)  # 1時間〜30日
        return uptime_seconds * 100
    
    def _generate_signal_strength(self) -> float:
        """信号強度を生成（dBm）"""
        # 正常範囲: -40 to -100 dBm
        return round(random.uniform(-40.0, -100.0), 1)
    
    def _generate_throughput(self) -> float:
        """スループットを生成（Mbps）"""
        return round(random.uniform(50.0, 1000.0), 2)
    
    def _generate_error_rate(self) -> float:
        """エラー率を生成（%）"""
        return round(random.uniform(0.0, 5.0), 3)
    
    def get_cm_data(self) -> Dict[str, Any]:
        """CMデータを取得"""
        raise NotImplementedError("Subclasses must implement get_cm_data")
    
    def execute_sleep_mode(self) -> Dict[str, Any]:
        """スリープモード実行"""
        raise NotImplementedError("Subclasses must implement execute_sleep_mode")
    
    def get_snmp_response(self, oid: str) -> Optional[SNMPResponse]:
        """SNMP応答を取得"""
        if oid in self.base_oids:
            return SNMPResponse(
                oid=oid,
                value=self.base_oids[oid],
                data_type="string" if isinstance(self.base_oids[oid], str) else "integer",
                timestamp=datetime.now()
            )
        return None

class EricssonMMUSimulator(BaseEquipmentSimulator):
    """Ericsson MMU シミュレータ
    
    参考: Ericsson基地局のSNMP MIBオブジェクト
    - Cell Configuration: 1.3.6.1.4.1.193.183.4.1.3.4
    - Radio Performance: 1.3.6.1.4.1.193.183.4.1.4
    """
    
    def __init__(self, equipment_id: str = "高輪ゲートウェイシティ_Ericsson_001"):
        super().__init__(equipment_id, "Ericsson", "MMU")
        
        # Ericsson固有のMIBオブジェクト
        self.ericsson_oids = {
            "1.3.6.1.4.1.193.183.4.1.3.4.1.1": "Cell_001",      # cellId
            "1.3.6.1.4.1.193.183.4.1.3.4.1.2": "2100",          # frequency (MHz)
            "1.3.6.1.4.1.193.183.4.1.3.4.1.3": "20",            # bandwidth (MHz)
            "1.3.6.1.4.1.193.183.4.1.4.1.1": self._generate_signal_strength(),  # RSRP
            "1.3.6.1.4.1.193.183.4.1.4.1.2": random.randint(0, 100),  # activeUsers
        }
    
    def get_cm_data(self) -> Dict[str, Any]:
        """CMデータを取得
        
        Returns:
            SNMP MIB形式とJSON形式の複合データ
        """
        # 実行時間をシミュレート（1-3秒）
        execution_time = random.uniform(1.0, 3.0)
        time.sleep(0.1)  # デモ用の短い待機
        
        # 成功/失敗をランダムに決定（90%成功率）
        success = random.random() > 0.1
        
        if success:
            return {
                "status": "success",
                "equipment_id": self.equipment_id,
                "vendor": self.vendor,
                "model": self.model,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "snmp_data": {
                    "1.3.6.1.4.1.193.183.4.1.3.4.1.1": "Cell_12345",
                    "1.3.6.1.4.1.193.183.4.1.3.4.1.2": "2100",
                    "1.3.6.1.4.1.193.183.4.1.3.4.1.3": "20",
                    "1.3.6.1.4.1.193.183.4.1.4.1.1": self._generate_signal_strength(),
                    "1.3.6.1.4.1.193.183.4.1.4.1.2": random.randint(20, 80)
                },
                "parsed_data": {
                    "cell_id": "Cell_12345",
                    "frequency_mhz": 2100,
                    "bandwidth_mhz": 20,
                    "signal_strength_dbm": self._generate_signal_strength(),
                    "active_users": random.randint(20, 80),
                    "throughput_mbps": self._generate_throughput(),
                    "error_rate_percent": self._generate_error_rate()
                }
            }
        else:
            return {
                "status": "error",
                "equipment_id": self.equipment_id,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "error_code": "SNMP_TIMEOUT",
                "error_message": "SNMP request timeout - equipment may be unreachable"
            }
    
    def execute_sleep_mode(self) -> Dict[str, Any]:
        """スリープモード実行"""
        execution_time = random.uniform(2.0, 5.0)
        time.sleep(0.1)
        
        # スリープモード成功率85%
        success = random.random() > 0.15
        
        if success:
            power_savings = random.uniform(25.0, 35.0)
            return {
                "status": "success",
                "equipment_id": self.equipment_id,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "sleep_mode": {
                    "enabled": True,
                    "power_savings_percent": round(power_savings, 1),
                    "sleep_duration_minutes": random.randint(30, 120),
                    "wake_threshold_dbm": -90.0
                },
                "snmp_data": {
                    "1.3.6.1.4.1.193.183.4.1.5.1.1": "1",  # sleepModeEnabled
                    "1.3.6.1.4.1.193.183.4.1.5.1.2": str(round(power_savings, 1)),  # powerSavings
                }
            }
        else:
            return {
                "status": "error",
                "equipment_id": self.equipment_id,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "error_code": "SLEEP_MODE_FAILED",
                "error_message": "Failed to enable sleep mode - hardware limitation"
            }

class EricssonRRUSimulator(BaseEquipmentSimulator):
    """Ericsson RRU シミュレータ"""
    
    def __init__(self, equipment_id: str = "大岡山ラボ_Ericsson_001"):
        super().__init__(equipment_id, "Ericsson", "RRU")
    
    def get_cm_data(self) -> Dict[str, Any]:
        """CMデータを取得"""
        execution_time = random.uniform(1.5, 4.0)
        time.sleep(0.1)
        
        success = random.random() > 0.12  # 88%成功率
        
        if success:
            return {
                "status": "success",
                "equipment_id": self.equipment_id,
                "vendor": self.vendor,
                "model": self.model,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "snmp_data": {
                    "1.3.6.1.4.1.193.183.5.1.1.1": "RRU_67890",
                    "1.3.6.1.4.1.193.183.5.1.2.1": "3500",  # 5G frequency
                    "1.3.6.1.4.1.193.183.5.1.3.1": "100",   # 5G bandwidth
                },
                "parsed_data": {
                    "rru_id": "RRU_67890",
                    "frequency_mhz": 3500,
                    "bandwidth_mhz": 100,
                    "signal_strength_dbm": self._generate_signal_strength(),
                    "throughput_mbps": self._generate_throughput() * 2,  # 5Gなので高速
                    "error_rate_percent": self._generate_error_rate()
                }
            }
        else:
            return {
                "status": "error",
                "equipment_id": self.equipment_id,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "error_code": "RRU_COMMUNICATION_ERROR",
                "error_message": "RRU communication interface error"
            }
    
    def execute_sleep_mode(self) -> Dict[str, Any]:
        """スリープモード実行"""
        execution_time = random.uniform(3.0, 6.0)
        time.sleep(0.1)
        
        # RRUはスリープモード対応率が低い（70%）
        success = random.random() > 0.3
        
        if success:
            return {
                "status": "success",
                "equipment_id": self.equipment_id,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "sleep_mode": {
                    "enabled": True,
                    "power_savings_percent": round(random.uniform(15.0, 25.0), 1),
                    "sleep_duration_minutes": random.randint(15, 60)
                }
            }
        else:
            return {
                "status": "error",
                "equipment_id": self.equipment_id,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "error_code": "SLEEP_NOT_SUPPORTED",
                "error_message": "Sleep mode not supported on this RRU model"
            }

class SamsungAUv1Simulator(BaseEquipmentSimulator):
    """Samsung AU v1 シミュレータ"""
    
    def __init__(self, equipment_id: str = "高輪ゲートウェイシティ_Samsung_001"):
        super().__init__(equipment_id, "Samsung", "AU-v1")
    
    def get_cm_data(self) -> Dict[str, Any]:
        """CMデータを取得"""
        execution_time = random.uniform(1.0, 2.5)
        time.sleep(0.1)
        
        success = random.random() > 0.08  # 92%成功率
        
        if success:
            return {
                "status": "success",
                "equipment_id": self.equipment_id,
                "vendor": self.vendor,
                "model": self.model,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "snmp_data": {
                    "1.3.6.1.4.1.20858.10.1.1.1": "SAMSUNG_CELL_001",
                    "1.3.6.1.4.1.20858.10.1.2.1": "2100",
                    "1.3.6.1.4.1.20858.10.1.3.1": "20",
                },
                "parsed_data": {
                    "cell_id": "SAMSUNG_CELL_001",
                    "frequency_mhz": 2100,
                    "bandwidth_mhz": 20,
                    "signal_strength_dbm": self._generate_signal_strength(),
                    "active_users": random.randint(15, 70),
                    "throughput_mbps": self._generate_throughput(),
                    "error_rate_percent": self._generate_error_rate()
                }
            }
        else:
            return {
                "status": "error",
                "equipment_id": self.equipment_id,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "error_code": "SAMSUNG_API_ERROR",
                "error_message": "Samsung API authentication failed"
            }
    
    def execute_sleep_mode(self) -> Dict[str, Any]:
        """スリープモード実行"""
        execution_time = random.uniform(2.5, 4.5)
        time.sleep(0.1)
        
        success = random.random() > 0.2  # 80%成功率
        
        if success:
            return {
                "status": "success",
                "equipment_id": self.equipment_id,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "sleep_mode": {
                    "enabled": True,
                    "power_savings_percent": round(random.uniform(20.0, 30.0), 1),
                    "sleep_duration_minutes": random.randint(45, 90)
                }
            }
        else:
            return {
                "status": "error",
                "equipment_id": self.equipment_id,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "error_code": "SLEEP_CONFIG_ERROR",
                "error_message": "Sleep mode configuration validation failed"
            }

class SamsungAUv2Simulator(BaseEquipmentSimulator):
    """Samsung AU v2 シミュレータ"""
    
    def __init__(self, equipment_id: str = "大岡山ラボ_Samsung_001"):
        super().__init__(equipment_id, "Samsung", "AU-v2")
    
    def get_cm_data(self) -> Dict[str, Any]:
        """CMデータを取得"""
        execution_time = random.uniform(0.8, 2.0)
        time.sleep(0.1)
        
        success = random.random() > 0.05  # 95%成功率（v2は改良版）
        
        if success:
            return {
                "status": "success",
                "equipment_id": self.equipment_id,
                "vendor": self.vendor,
                "model": self.model,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "snmp_data": {
                    "1.3.6.1.4.1.20858.11.1.1.1": "SAMSUNG_CELL_V2_001",
                    "1.3.6.1.4.1.20858.11.1.2.1": "2100",
                    "1.3.6.1.4.1.20858.11.1.3.1": "20",
                },
                "parsed_data": {
                    "cell_id": "SAMSUNG_CELL_V2_001",
                    "frequency_mhz": 2100,
                    "bandwidth_mhz": 20,
                    "signal_strength_dbm": self._generate_signal_strength(),
                    "active_users": random.randint(25, 90),
                    "throughput_mbps": self._generate_throughput() * 1.2,  # v2は性能向上
                    "error_rate_percent": self._generate_error_rate() * 0.8  # エラー率改善
                }
            }
        else:
            return {
                "status": "error",
                "equipment_id": self.equipment_id,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "error_code": "NETWORK_TIMEOUT",
                "error_message": "Network communication timeout"
            }
    
    def execute_sleep_mode(self) -> Dict[str, Any]:
        """スリープモード実行"""
        execution_time = random.uniform(1.5, 3.0)
        time.sleep(0.1)
        
        success = random.random() > 0.1  # 90%成功率（v2は改良版）
        
        if success:
            return {
                "status": "success",
                "equipment_id": self.equipment_id,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "sleep_mode": {
                    "enabled": True,
                    "power_savings_percent": round(random.uniform(30.0, 40.0), 1),  # v2は省電力性能向上
                    "sleep_duration_minutes": random.randint(60, 120),
                    "advanced_features": {
                        "adaptive_sleep": True,
                        "traffic_prediction": True,
                        "energy_optimization": True
                    }
                }
            }
        else:
            return {
                "status": "error",
                "equipment_id": self.equipment_id,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "error_code": "FIRMWARE_ERROR",
                "error_message": "Firmware update required for sleep mode"
            }

class MockEquipmentManager:
    """モック設備管理クラス"""
    
    def __init__(self):
        self.simulators = {
            "Ericsson-MMU": EricssonMMUSimulator(),
            "Ericsson-RRU": EricssonRRUSimulator(),
            "Samsung-AUv1": SamsungAUv1Simulator(),
            "Samsung-AUv2": SamsungAUv2Simulator()
        }
    
    def get_simulator(self, equipment_type: str) -> Optional[BaseEquipmentSimulator]:
        """シミュレータを取得"""
        return self.simulators.get(equipment_type)
    
    def get_equipment(self, equipment_id: str) -> Optional[BaseEquipmentSimulator]:
        """設備IDから設備を取得（テスト用）"""
        # 設備IDから設備タイプを推定
        if "MMU" in equipment_id:
            return self.simulators.get("Ericsson-MMU")
        elif "RRU" in equipment_id:
            return self.simulators.get("Ericsson-RRU")
        elif "AUv1" in equipment_id:
            return self.simulators.get("Samsung-AUv1")
        elif "AUv2" in equipment_id:
            return self.simulators.get("Samsung-AUv2")
        else:
            # デフォルトはEricsson MMU
            return self.simulators.get("Ericsson-MMU")
    
    def execute_command(self, equipment_type: str, command: str) -> Dict[str, Any]:
        """コマンドを実行"""
        simulator = self.get_simulator(equipment_type)
        if not simulator:
            return {
                "status": "error",
                "error_code": "UNKNOWN_EQUIPMENT",
                "error_message": f"Unknown equipment type: {equipment_type}"
            }
        
        try:
            if command == "get_cm_data":
                return simulator.get_cm_data()
            elif command == "execute_sleep_mode":
                return simulator.execute_sleep_mode()
            else:
                return {
                    "status": "error",
                    "error_code": "UNKNOWN_COMMAND",
                    "error_message": f"Unknown command: {command}"
                }
        except Exception as e:
            return {
                "status": "error",
                "error_code": "EXECUTION_ERROR",
                "error_message": f"Command execution failed: {str(e)}"
            }
    
    def execute_command(self, equipment_id: str, command: str, parameters: Dict = None) -> Dict[str, Any]:
        """設備にコマンドを実行（MCP用）"""
        if parameters is None:
            parameters = {}
            
        # 設備IDから設備タイプを特定（柔軟なマッチング）
        equipment_type = None
        
        # 直接的なマッチング
        for eq_type, simulator in self.simulators.items():
            if simulator.equipment_id == equipment_id:
                equipment_type = eq_type
                break
        
        # 設備タイプ名での直接マッチング
        if equipment_type is None and equipment_id in self.simulators:
            equipment_type = equipment_id
        
        # パターンマッチング
        if equipment_type is None:
            if "Samsung" in equipment_id:
                if "高輪ゲートウェイシティ" in equipment_id:
                    equipment_type = "高輪ゲートウェイシティ_Samsung"
                else:
                    equipment_type = "大岡山ラボ_Samsung"
            elif "Ericsson" in equipment_id:
                if "高輪ゲートウェイシティ" in equipment_id:
                    equipment_type = "高輪ゲートウェイシティ_Ericsson"
                else:
                    equipment_type = "大岡山ラボ_Ericsson"
        
        if equipment_type is None:
            return {
                "status": "error",
                "error_code": "EQUIPMENT_NOT_FOUND",
                "error_message": f"Equipment not found: {equipment_id}"
            }
        
        # コマンド実行
        return self.send_command(equipment_type, command)
    
    def send_command(self, equipment_type: str, command: str) -> Dict[str, Any]:
        """設備にコマンドを送信"""
        simulator = self.get_simulator(equipment_type)
        if not simulator:
            return {
                "status": "error",
                "error_code": "UNKNOWN_EQUIPMENT",
                "error_message": f"Unknown equipment type: {equipment_type}"
            }
        
        # 基本的なコマンド実行
        if command == "get_status":
            return simulator.get_snmp_data()
        elif command == "get_cm_data":
            return {"cm_data": simulator.get_cm_data()}
        elif "test_command" in command:
            return {
                "status": "success",
                "equipment_type": equipment_type,
                "command": command,
                "timestamp": datetime.now().isoformat(),
                "response": "Command executed successfully"
            }
        else:
            return {
                "status": "error",
                "error_code": "UNKNOWN_COMMAND",
                "error_message": f"Unknown command: {command}"
            }
    
    def get_equipment_status(self) -> Dict[str, Any]:
        """全設備のステータスを取得"""
        status = {}
        for eq_type, simulator in self.simulators.items():
            status[eq_type] = {
                "equipment_id": simulator.equipment_id,
                "vendor": simulator.vendor,
                "model": simulator.model,
                "status": simulator.status.value,
                "last_update": simulator.last_update.isoformat()
            }
        return status

# グローバルインスタンス
mock_equipment_manager = MockEquipmentManager()

