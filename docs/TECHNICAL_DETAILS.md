# 🔧 技術詳細説明書

**Technical Details Documentation**

ラボ検証自動化システムの技術的な詳細について、初級者にも分かりやすく説明します。

## 📋 目次

1. [システム全体像](#システム全体像)
2. [アーキテクチャ詳細](#アーキテクチャ詳細)
3. [データフロー](#データフロー)
4. [各コンポーネント詳細](#各コンポーネント詳細)
5. [実装ロジック](#実装ロジック)
6. [データベース設計](#データベース設計)
7. [API仕様](#api仕様)
8. [セキュリティ](#セキュリティ)

## 🏗️ システム全体像

### 概要
本システムは、通信事業者のラボ検証作業を自動化するためのWebアプリケーションです。以下の技術スタックで構築されています：

- **フロントエンド**: Streamlit (Python Webフレームワーク)
- **バックエンド**: Python 3.12
- **データベース**: SQLite (軽量リレーショナルDB)
- **AI/LLM**: Ollama + llama3.3:latest
- **モック設備**: カスタム実装のシミュレーター

### システム構成図

```mermaid
graph TB
    subgraph "ユーザーインターフェース層"
        A[Streamlit Dashboard]
        B[Web Browser]
    end
    
    subgraph "アプリケーション層"
        C[Main Application]
        D[LLM Service]
        E[Validation Engine]
        F[Excel Parser]
        G[Star Chart Generator]
    end
    
    subgraph "データ層"
        H[SQLite Database]
        I[Vector Store]
        J[File Storage]
    end
    
    subgraph "外部システム"
        K[Ollama LLM]
        L[Mock Equipment]
    end
    
    B --> A
    A --> C
    C --> D
    C --> E
    C --> F
    C --> G
    D --> K
    E --> L
    C --> H
    D --> I
    C --> J
```

## 🔄 データフロー

### 1. 検証項目作成フロー

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant UI as Streamlit UI
    participant LLM as LLM Service
    participant DB as Database
    
    User->>UI: 新機能名入力
    UI->>LLM: 検証項目生成要求
    LLM->>LLM: RAG検索 + 生成
    LLM->>UI: 生成された検証項目
    UI->>DB: 検証項目保存
    DB->>UI: 保存完了
    UI->>User: 結果表示
```

### 2. 検証実行フロー

```mermaid
sequenceDiagram
    participant UI as Streamlit UI
    participant Engine as Validation Engine
    participant Mock as Mock Equipment
    participant LLM as LLM Service
    participant DB as Database
    
    UI->>Engine: 検証バッチ実行
    Engine->>Mock: 設備コマンド送信
    Mock->>Engine: 設備応答データ
    Engine->>LLM: 結果分析要求
    LLM->>Engine: 判定結果
    Engine->>DB: 結果保存
    Engine->>UI: 進捗通知
    UI->>UI: リアルタイム表示更新
```

## 🧩 各コンポーネント詳細

### 1. Streamlit UI (`app/main.py`)

**役割**: ユーザーインターフェースの提供

**主要機能**:
- ダッシュボード表示
- 検証項目管理
- 検証実行制御
- 結果表示・分析

**実装のポイント**:
```python
# セッション状態管理
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.test_items = []

# リアルタイム更新
def progress_callback(progress: float, result: ValidationResult):
    progress_bar.progress(progress)
    status_text.text(f"実行中... {progress:.1%} 完了")
```

### 2. LLM Service (`app/services/llm_service.py`)

**役割**: 大規模言語モデルとの連携

**対応プロバイダー**:
- Ollama (ローカル)
- OpenAI GPT-4o
- Anthropic Claude
- AWS Bedrock

**主要メソッド**:

#### `analyze_validation_result()`
```python
def analyze_validation_result(self, test_item: Dict, equipment_response: Dict) -> Dict:
    """
    検証結果をLLMで分析
    
    処理フロー:
    1. システムプロンプト設定
    2. 検証項目と設備応答を組み合わせ
    3. LLMに分析要求
    4. JSON形式の判定結果を取得
    5. フォールバック処理（エラー時）
    """
```

#### `generate_test_items()`
```python
def generate_test_items(self, feature_name: str, equipment_types: List[str]) -> List[Dict]:
    """
    新機能の検証項目をAI生成
    
    処理フロー:
    1. 機能名と設備タイプを入力
    2. 過去の検証パターンを参照（RAG）
    3. 新規検証項目を生成
    4. 星取表形式で出力
    """
```

### 3. Validation Engine (`app/services/validation_engine.py`)

**役割**: 検証の実行制御とオーケストレーション

**主要クラス**: `ValidationEngine`

**実行フロー**:

#### 単一検証実行
```python
def execute_test_item(self, test_item: TestItem, scenario: str, equipment_type: EquipmentType):
    """
    1. 開始時刻記録
    2. コマンド決定（カテゴリベース）
    3. モック設備にコマンド送信
    4. 設備応答受信
    5. LLMで結果分析
    6. ValidationResultオブジェクト作成
    7. 実行時間計算
    """
```

#### バッチ実行
```python
def execute_batch(self, batch: ValidationBatch, progress_callback):
    """
    1. バッチステータス更新（RUNNING）
    2. 実行タスクリスト作成
    3. ThreadPoolExecutorで並列実行
    4. 進捗コールバック呼び出し
    5. 結果収集・集計
    6. バッチステータス更新（COMPLETED）
    """
```

### 4. Mock Equipment System (`mock_equipment/equipment_simulator.py`)

**役割**: 実際のネットワーク設備を模擬

**設備シミュレーター階層**:
```
BaseEquipmentSimulator (基底クラス)
├── EricssonMMUSimulator
├── EricssonRRUSimulator  
├── SamsungAUv1Simulator
└── SamsungAUv2Simulator
```

**応答データ生成ロジック**:

#### Ericsson MMU例
```python
def get_cm_data(self) -> Dict[str, Any]:
    """
    1. 実行時間シミュレート（1-3秒）
    2. 成功/失敗をランダム決定（90%成功率）
    3. SNMP MIBオブジェクト生成
    4. 解析済みデータ生成
    5. JSON形式で応答返却
    """
    
    # SNMP MIB形式（実際の基地局に準拠）
    snmp_data = {
        "1.3.6.1.4.1.193.183.4.1.3.4.1.1": "Cell_12345",  # cellId
        "1.3.6.1.4.1.193.183.4.1.4.1.1": -75.2,           # RSRP
    }
    
    # 人間が読みやすい形式
    parsed_data = {
        "cell_id": "Cell_12345",
        "signal_strength_dbm": -75.2,
        "throughput_mbps": 150.5
    }
```

**参考にしたデータ形式**:
- **SNMP MIB**: [RFC 1213](https://tools.ietf.org/html/rfc1213)
- **Ericsson基地局**: 1.3.6.1.4.1.193.183.*
- **Samsung基地局**: 1.3.6.1.4.1.20858.*

### 5. Database Models (`app/models/database.py`)

**役割**: データの永続化とORM

**使用技術**: SQLAlchemy + SQLite

**主要テーブル**:

#### TestItemDB
```python
class TestItemDB(Base):
    __tablename__ = "test_items"
    
    id = Column(String, primary_key=True)
    test_block = Column(String, nullable=False)
    category = Column(String, nullable=False)
    condition_text = Column(Text, nullable=False)
    expected_count = Column(Integer, default=0)
    threshold_values = Column(Text)  # JSON文字列
    equipment_types = Column(Text)   # JSON文字列
    scenarios = Column(Text)         # JSON文字列
```

**JSON列の処理**:
```python
def set_threshold_values(self, values: Dict[str, float]):
    """辞書をJSON文字列として保存"""
    self.threshold_values = json.dumps(values)

def get_threshold_values(self) -> Dict[str, float]:
    """JSON文字列を辞書として取得"""
    if self.threshold_values:
        return json.loads(self.threshold_values)
    return {}
```

### 6. Excel Parser (`app/utils/excel_parser.py`)

**役割**: Excelファイルからの検証項目抽出

**処理フロー**:
```python
def parse_excel_test_items(uploaded_file) -> List[TestItem]:
    """
    1. pandasでExcel読み込み
    2. 列名とデータ構造を分析
    3. 各行を検証項目に変換
    4. 設備タイプとシナリオを抽出
    5. TestItemオブジェクト生成
    6. エラーハンドリング
    """
```

**列名マッピング例**:
```python
# Excelの列名から設備タイプを特定
if 'Ericsson-MMU' in col_str:
    equipment_type = EquipmentType.ERICSSON_MMU
elif 'Samsung-AUv1' in col_str:
    equipment_type = EquipmentType.SAMSUNG_AUV1
```

### 7. Star Chart Generator (`app/utils/star_chart.py`)

**役割**: 検証結果の星取表生成

**変換ロジック**:
```python
def convert_result_to_symbol(result: TestResult) -> str:
    """テスト結果を記号に変換"""
    symbol_mapping = {
        TestResult.PASS: "●",        # 合格
        TestResult.FAIL: "×",        # 不合格  
        TestResult.WARNING: "△",     # 警告
        TestResult.NOT_EXECUTED: "-" # 未実行
    }
    return symbol_mapping.get(result, "-")
```

**DataFrame生成**:
```python
def create_star_chart_dataframe(results: List[ValidationResult]) -> pd.DataFrame:
    """
    1. シナリオと設備タイプを抽出
    2. 結果マトリックス作成
    3. 記号変換適用
    4. pandas DataFrameとして返却
    """
```

## 💾 データベース設計

### ER図

```mermaid
erDiagram
    TEST_ITEMS {
        string id PK
        string test_block
        string category
        text condition_text
        integer expected_count
        text threshold_values
        text equipment_types
        text scenarios
        datetime created_at
        datetime updated_at
    }
    
    VALIDATION_BATCHES {
        string id PK
        string name
        string status
        datetime started_at
        datetime completed_at
        datetime created_at
    }
    
    VALIDATION_RESULTS {
        string id PK
        string test_item_id FK
        string batch_id FK
        string equipment_type
        string scenario
        string result
        text response_data
        float execution_time
        text error_message
        float confidence
        datetime created_at
    }
    
    LAB_LOCATIONS {
        string id PK
        string name
        string address
        text equipment_types
        integer capacity
        datetime created_at
    }
    
    KNOWLEDGE_ENTRIES {
        string id PK
        string test_item_id FK
        text failure_pattern
        text analysis
        text improvement_suggestion
        string created_by
        datetime created_at
    }
    
    TEST_ITEMS ||--o{ VALIDATION_RESULTS : "has"
    VALIDATION_BATCHES ||--o{ VALIDATION_RESULTS : "contains"
    TEST_ITEMS ||--o{ KNOWLEDGE_ENTRIES : "generates"
```

### インデックス設計

```sql
-- 検索パフォーマンス向上のためのインデックス
CREATE INDEX idx_validation_results_batch_id ON validation_results(batch_id);
CREATE INDEX idx_validation_results_test_item_id ON validation_results(test_item_id);
CREATE INDEX idx_validation_results_created_at ON validation_results(created_at);
CREATE INDEX idx_test_items_category ON test_items(category);
```

## 🔄 実装ロジック詳細

### 1. 並列処理実装

**ThreadPoolExecutor使用**:
```python
with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
    # タスクを投入
    future_to_task = {
        executor.submit(self.execute_test_item, test_item, scenario, equipment_type): 
        (test_item, scenario, equipment_type)
        for test_item, scenario, equipment_type in tasks
    }
    
    # 結果を収集
    for future in as_completed(future_to_task):
        result = future.result()
        batch.results.append(result)
```

**非同期処理対応**:
```python
async def execute_batch_async(self, batch: ValidationBatch):
    """
    asyncio.Semaphoreで同時実行数制御
    asyncio.as_completedで順次結果収集
    """
    semaphore = asyncio.Semaphore(self.max_workers)
    
    async def execute_with_semaphore(test_item, scenario, equipment_type):
        async with semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self.execute_test_item, test_item, scenario, equipment_type
            )
```

### 2. エラーハンドリング戦略

**階層的エラー処理**:
```python
try:
    # メイン処理
    result = self.execute_main_logic()
except SpecificException as e:
    # 特定エラーの処理
    logger.warning(f"Specific error: {e}")
    result = self.handle_specific_error(e)
except Exception as e:
    # 汎用エラーの処理
    logger.error(f"Unexpected error: {e}")
    result = self.create_error_result(e)
finally:
    # クリーンアップ処理
    self.cleanup_resources()
```

**フォールバック機能**:
```python
def analyze_validation_result(self, test_item, equipment_response):
    """
    1. LLMで分析試行
    2. JSONパース試行
    3. 失敗時はルールベース分析にフォールバック
    4. 最終的にデフォルト値を返却
    """
    try:
        llm_result = self.llm_service.analyze(...)
        return json.loads(llm_result)
    except (json.JSONDecodeError, LLMException):
        logger.warning("LLM analysis failed, using fallback")
        return self._fallback_analysis(equipment_response)
```

### 3. キャッシュ戦略

**Streamlitセッション状態**:
```python
# 重い処理の結果をキャッシュ
@st.cache_data
def load_test_items():
    """検証項目の読み込み結果をキャッシュ"""
    return database_manager.get_all_test_items()

# セッション間でのデータ保持
if 'validation_results' not in st.session_state:
    st.session_state.validation_results = []
```

**LLM接続キャッシュ**:
```python
def _test_ollama_connection(self):
    """接続テスト結果をセッションキャッシュ"""
    cache_key = f"ollama_tested_{OLLAMA_BASE_URL}_{OLLAMA_MODEL}"
    
    if not self.force_test and cache_key in st.session_state:
        cached_result = st.session_state[cache_key]
        logger.info("⚡ Using cached Ollama connection")
        return cached_result
```

### 4. データ変換パイプライン

**モデル間変換**:
```python
# Domain Model → Database Model
def to_db_model(test_item: TestItem) -> TestItemDB:
    db_item = TestItemDB(
        id=test_item.id,
        test_block=test_item.test_block,
        category=test_item.category.value
    )
    db_item.set_equipment_types([eq.value for eq in test_item.condition.equipment_types])
    return db_item

# Database Model → Domain Model  
def from_db_model(db_item: TestItemDB) -> TestItem:
    equipment_types = [EquipmentType(eq) for eq in db_item.get_equipment_types()]
    condition = TestCondition(
        condition_text=db_item.condition_text,
        equipment_types=equipment_types
    )
    return TestItem(
        id=db_item.id,
        test_block=db_item.test_block,
        category=TestCategory(db_item.category),
        condition=condition
    )
```

## 🔒 セキュリティ実装

### 1. 入力検証

**SQLインジェクション対策**:
```python
# SQLAlchemy ORMを使用（自動エスケープ）
session.query(TestItemDB).filter(TestItemDB.id == user_input).first()

# 直接SQL実行時はパラメータ化クエリ
session.execute(
    text("SELECT * FROM test_items WHERE id = :id"),
    {"id": user_input}
)
```

**ファイルアップロード検証**:
```python
def validate_uploaded_file(uploaded_file):
    """
    1. ファイル拡張子チェック
    2. ファイルサイズ制限
    3. MIMEタイプ検証
    4. ウイルススキャン（本番環境）
    """
    allowed_extensions = ['.xlsx', '.xls']
    max_size = 10 * 1024 * 1024  # 10MB
    
    if not any(uploaded_file.name.endswith(ext) for ext in allowed_extensions):
        raise ValueError("Invalid file type")
    
    if uploaded_file.size > max_size:
        raise ValueError("File too large")
```

### 2. 認証・認可

**環境変数による設定**:
```python
# APIキーの安全な管理
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.warning("OpenAI API key not configured")

# デバッグモードの制御
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
if DEBUG:
    logging.basicConfig(level=logging.DEBUG)
```

### 3. ログ管理

**センシティブ情報の除外**:
```python
def safe_log_response(response_data: Dict) -> Dict:
    """ログ出力用にセンシティブ情報を除外"""
    safe_data = response_data.copy()
    
    # APIキーやトークンを除外
    sensitive_keys = ['api_key', 'token', 'password']
    for key in sensitive_keys:
        if key in safe_data:
            safe_data[key] = "***REDACTED***"
    
    return safe_data

logger.info(f"Equipment response: {safe_log_response(response)}")
```

## 📊 パフォーマンス最適化

### 1. データベース最適化

**接続プール**:
```python
# SQLAlchemy接続プール設定
engine = create_engine(
    DATABASE_URL,
    pool_size=10,           # 接続プールサイズ
    max_overflow=20,        # 最大オーバーフロー
    pool_timeout=30,        # タイムアウト
    pool_recycle=3600       # 接続リサイクル
)
```

**バッチ処理**:
```python
def bulk_insert_results(results: List[ValidationResult]):
    """バッチでの結果挿入"""
    session = db_manager.get_session()
    try:
        db_results = [result.to_db_model() for result in results]
        session.bulk_save_objects(db_results)
        session.commit()
    finally:
        session.close()
```

### 2. メモリ管理

**ジェネレーター使用**:
```python
def process_large_dataset():
    """大量データを逐次処理"""
    for batch in get_data_batches():
        yield process_batch(batch)
        # メモリ解放
        del batch
```

**オブジェクトプール**:
```python
class ValidationEnginePool:
    """検証エンジンのオブジェクトプール"""
    def __init__(self, pool_size=5):
        self.pool = Queue(maxsize=pool_size)
        for _ in range(pool_size):
            self.pool.put(ValidationEngine())
    
    def get_engine(self):
        return self.pool.get()
    
    def return_engine(self, engine):
        self.pool.put(engine)
```

## 🧪 テスト戦略

### 1. 単体テスト

**pytest使用例**:
```python
def test_validation_engine():
    """検証エンジンのテスト"""
    engine = ValidationEngine()
    
    # テストデータ作成
    test_item = create_test_item()
    
    # 実行
    result = engine.execute_test_item(
        test_item, "正常スリープ", EquipmentType.ERICSSON_MMU
    )
    
    # 検証
    assert result.test_item_id == test_item.id
    assert result.result in [TestResult.PASS, TestResult.FAIL, TestResult.WARNING]
    assert result.execution_time > 0
```

### 2. 統合テスト

**モックオブジェクト使用**:
```python
@patch('app.services.llm_service.ollama.Client')
def test_llm_service_integration(mock_ollama):
    """LLMサービスの統合テスト"""
    # モック設定
    mock_ollama.return_value.chat.return_value = {
        'message': {'content': '{"result": "PASS", "confidence": 0.9}'}
    }
    
    # テスト実行
    llm_service = LLMService()
    result = llm_service.analyze_validation_result(test_item, response)
    
    # 検証
    assert result['result'] == 'PASS'
    assert result['confidence'] == 0.9
```

### 3. パフォーマンステスト

**実行時間測定**:
```python
def test_validation_performance():
    """検証実行のパフォーマンステスト"""
    engine = ValidationEngine()
    test_items = create_large_test_batch(100)
    
    start_time = time.time()
    batch = engine.execute_batch(test_items)
    execution_time = time.time() - start_time
    
    # パフォーマンス要件チェック
    assert execution_time < 300  # 5分以内
    assert batch.success_rate > 0.8  # 80%以上の成功率
```

## 🔧 デバッグ・トラブルシューティング

### 1. ログレベル設定

```python
# 開発時の詳細ログ
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)

# 本番時の最小ログ
logging.basicConfig(level=logging.WARNING)
```

### 2. デバッグ用ユーティリティ

```python
def debug_validation_result(result: ValidationResult):
    """検証結果のデバッグ出力"""
    print(f"=== Validation Result Debug ===")
    print(f"Test Item ID: {result.test_item_id}")
    print(f"Equipment: {result.equipment_type.value}")
    print(f"Scenario: {result.scenario}")
    print(f"Result: {result.result.value}")
    print(f"Execution Time: {result.execution_time:.2f}s")
    print(f"Confidence: {result.confidence:.2f}")
    if result.error_message:
        print(f"Error: {result.error_message}")
    print(f"Response Data: {json.dumps(result.response_data, indent=2)}")
    print("=" * 30)
```

### 3. ヘルスチェック機能

```python
def system_health_check():
    """システムの健全性チェック"""
    health_status = {
        "database": check_database_connection(),
        "ollama": check_ollama_connection(),
        "mock_equipment": check_mock_equipment(),
        "disk_space": check_disk_space(),
        "memory_usage": check_memory_usage()
    }
    
    return health_status

def check_database_connection():
    """データベース接続チェック"""
    try:
        session = db_manager.get_session()
        session.execute(text("SELECT 1"))
        session.close()
        return {"status": "healthy", "message": "Database connection OK"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}
```

## 📈 監視・メトリクス

### 1. パフォーマンスメトリクス

```python
class PerformanceMonitor:
    """パフォーマンス監視クラス"""
    
    def __init__(self):
        self.metrics = {
            "validation_count": 0,
            "total_execution_time": 0.0,
            "success_count": 0,
            "failure_count": 0
        }
    
    def record_validation(self, result: ValidationResult):
        """検証結果を記録"""
        self.metrics["validation_count"] += 1
        self.metrics["total_execution_time"] += result.execution_time
        
        if result.result == TestResult.PASS:
            self.metrics["success_count"] += 1
        else:
            self.metrics["failure_count"] += 1
    
    def get_average_execution_time(self):
        """平均実行時間を取得"""
        if self.metrics["validation_count"] > 0:
            return self.metrics["total_execution_time"] / self.metrics["validation_count"]
        return 0.0
    
    def get_success_rate(self):
        """成功率を取得"""
        total = self.metrics["validation_count"]
        if total > 0:
            return self.metrics["success_count"] / total
        return 0.0
```

### 2. アラート機能

```python
def check_system_alerts():
    """システムアラートのチェック"""
    alerts = []
    
    # 成功率が低下した場合
    if performance_monitor.get_success_rate() < 0.7:
        alerts.append({
            "level": "warning",
            "message": "Validation success rate below 70%"
        })
    
    # 実行時間が長すぎる場合
    if performance_monitor.get_average_execution_time() > 10.0:
        alerts.append({
            "level": "warning", 
            "message": "Average execution time exceeds 10 seconds"
        })
    
    # ディスク容量不足
    if get_disk_usage() > 0.9:
        alerts.append({
            "level": "critical",
            "message": "Disk usage above 90%"
        })
    
    return alerts
```

## 🚀 デプロイメント

### 1. 本番環境設定

```bash
# 本番用環境変数
export ENVIRONMENT=production
export DEBUG=false
export LOG_LEVEL=WARNING
export DATABASE_URL=postgresql://user:pass@host:5432/labvalidation

# セキュリティ設定
export SECRET_KEY=your-secret-key
export ALLOWED_HOSTS=your-domain.com
```

### 2. Docker化

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 依存関係インストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコピー
COPY . .

# 非rootユーザーで実行
RUN useradd -m appuser
USER appuser

# ポート公開
EXPOSE 8501

# 起動コマンド
CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 3. 運用監視

```python
# ヘルスチェックエンドポイント
@app.get("/health")
async def health_check():
    """ヘルスチェックAPI"""
    health_status = system_health_check()
    
    if all(status["status"] == "healthy" for status in health_status.values()):
        return {"status": "healthy", "details": health_status}
    else:
        raise HTTPException(status_code=503, detail=health_status)

# メトリクスエンドポイント
@app.get("/metrics")
async def get_metrics():
    """メトリクス取得API"""
    return {
        "validation_count": performance_monitor.metrics["validation_count"],
        "success_rate": performance_monitor.get_success_rate(),
        "average_execution_time": performance_monitor.get_average_execution_time(),
        "timestamp": datetime.now().isoformat()
    }
```

---

この技術詳細説明書により、システムの内部動作を詳細に理解し、カスタマイズや拡張を行うことができます。各コンポーネントの役割と実装方法を把握することで、効率的な開発・運用が可能になります。

