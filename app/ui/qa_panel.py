"""
RAG質疑応答パネルUI
検証バッチの実行結果をベクターDBに保存して、質問に応じてRAGで関連バッチを読み出し→AIが回答を生成→ダッシュボードで表示
"""
import streamlit as st
import logging
from typing import List, Dict, Any, Optional, Callable
import json
from datetime import datetime, timedelta

from app.services.llm_service import get_llm_service
from app.services.vector_store import get_vector_store
from app.services.batch_storage import load_realistic_batches

logger = logging.getLogger(__name__)

def render_qa_panel():
    """RAG質疑応答パネルを表示"""
    st.markdown("## AI質疑応答")
    st.markdown("検証バッチの実行結果に関する質問にAIが回答します（RAG技術使用）")
    
    # 表示設定
    st.markdown("**表示設定**")
    col_s1, col_s2, col_spacer = st.columns([2, 2, 6])
    with col_s1:
        use_streaming = st.checkbox("ストリーミング表示", value=True, help="回答をリアルタイムで表示")
    with col_s2:
        show_thinking = st.checkbox("思考過程表示", value=False, help="AIの思考過程を表示")
    
    st.divider()
    
    # LLMプロバイダー選択（サイドバーから取得）
    selected_provider = st.session_state.get('selected_provider', 'ollama')
    
    # 質問応答インターフェース
    render_qa_interface(selected_provider, use_streaming, show_thinking)

def render_qa_interface(llm_provider: str, use_streaming: bool = True, show_thinking: bool = False):
    """質問応答インターフェースを表示"""
    st.markdown("### 検証結果について質問する")
    st.markdown("過去の検証バッチの結果や統計情報について質問できます")
    
    # サンプル質問
    st.write("**サンプル質問:**")
    sample_questions = [
        "最近失敗した検証項目はありますか？",
        "基地局スリープ機能の検証結果を教えてください",
        "高輪ゲートウェイシティ_Ericsson設備で問題が発生した検証はありますか？",
        "成功率が低い検証項目を特定してください",
        "今日実行された検証の結果はどうでしたか？",
        "特定の設備タイプで頻繁に失敗する検証項目はありますか？"
    ]
    
    selected_question = st.selectbox(
        "サンプル質問を選択（または下に独自の質問を入力）",
        ["質問を選択..."] + sample_questions
    )
    
    # 質問入力
    if selected_question != "質問を選択...":
        question = st.text_input("質問内容:", value=selected_question)
    else:
        question = st.text_input("質問内容:")
    
    # AI質問ボタン
    ask_button = st.button("AIに質問する", type="primary", use_container_width=True)
    
    if ask_button:
        if question:
            try:
                # LLMサービスを初期化
                llm_service = get_llm_service(llm_provider)
                
                    # RAGシステムの動作可視化
                with st.spinner("🔍 関連検証データを検索中..."):
                    # リアルなバッチデータを取得
                    realistic_batches = load_realistic_batches()
                    
                    # 検証結果専用ベクター検索の実行
                    from app.services.validation_result_vector_store import get_validation_result_vector_store
                    result_vector_store = get_validation_result_vector_store()
                    vector_search_results = result_vector_store.search_similar_documents(question, top_k=5)
                    
                    # 直接バッチデータから関連するものを検索（補完用）
                    batch_results = _search_batches_directly(question, realistic_batches, top_k=3)
                    
                    # 結果を統合（ベクター検索をメインに使用）
                    search_results = {
                        'vector_results': vector_search_results,
                        'batch_results': batch_results
                    }
                    
                    # ベクター検索結果を統一スタイルで表示
                    if vector_search_results:
                        st.info(f"✅ {len(vector_search_results)}件の関連検証結果が見つかりました")
                    else:
                        st.info("関連する検証結果が見つかりませんでした")
                        
                        # 検索結果の表示（詳細表示オプション）
                        if show_thinking and vector_search_results:
                            with st.expander("🔍 検索された検証結果", expanded=False):
                                for i, result in enumerate(vector_search_results):
                                    metadata = result.get('metadata', {})
                                    st.write(f"**{i+1}. 類似度: {result.get('similarity', 0):.3f}**")
                                    st.write(f"- バッチ: {metadata.get('batch_name', 'Unknown')}")
                                    st.write(f"- 設備: {metadata.get('equipment_type', 'Unknown')}")
                                    st.write(f"- 結果: {metadata.get('result', 'Unknown')}")
                                    st.write(f"- 内容プレビュー: {result.get('content', '')[:100]}...")
                                    st.write("---")
                
                # 思考過程表示
                if show_thinking:
                    with st.spinner("🧠 AIが検証結果を分析中..."):
                        import time
                        time.sleep(1)  # 思考過程の演出
                
                # AI回答生成と表示
                response_placeholder = st.empty()
                
                with st.spinner("AIが回答生成中..."):
                    response = _generate_qa_response(llm_service, question, search_results)
                
                # 元のシンプルなinfo表示
                with response_placeholder.container():
                    st.info(response)
                
                # 完了メッセージ
                st.success("✅ RAGシステムによる回答が完了しました")
                    
            except Exception as e:
                st.error(f"AI回答生成中にエラーが発生しました: {str(e)}")
                logger.error(f"QA error: {e}")
        else:
            st.warning("質問を入力してください")

def render_bedrock_streaming_response(llm_service, question: str, search_results: List[Dict], show_thinking: bool):
    """AWS Bedrockストリーミング応答を表示"""
    progress_bar = st.progress(0)
    spinner_placeholder = st.empty()
    thinking_container = st.empty()
    answer_container = st.empty()
    
    # 累積応答テキスト
    accumulated_answer = ""
    
    def bedrock_progress_callback(progress: float, message: str):
        nonlocal accumulated_answer
        
        # プログレス値の範囲チェック
        if progress > 1.0:
            progress = 1.0
        elif progress < 0.0:
            progress = 0.0
        
        # プログレスバー更新
        progress_bar.progress(progress)
        
        # スピナー表示（実行中... xx%済み）
        with spinner_placeholder:
            with st.spinner(f"実行中... {progress*100:.1f}%済み"):
                # 途中思考を累積表示
                if isinstance(message, str) and len(message.strip()) > 0:
                    accumulated_answer += message
                    
                    if show_thinking:
                        thinking_container.info(f"💭 AIエージェント思考: {accumulated_answer}")
                    
                    # 回答を表示
                    answer_container.markdown(f"**回答:**\n\n{accumulated_answer}")
    
    try:
        # RAGコンテキストを準備
        context = _prepare_rag_context(search_results)
        
        # ストリーミング応答を生成
        if hasattr(llm_service, '_generate_bedrock_streaming'):
            system_prompt = """あなたは通信設備の検証エキスパートです。
検証バッチの実行結果に関する質問に、提供されたコンテキスト情報を基に回答してください。

回答は以下の形式で行ってください：
1. 質問に対する直接的な回答
2. 関連する検証結果の詳細
3. 推奨事項や注意点（必要に応じて）

コンテキスト情報にない内容については、「提供された情報では確認できません」と明記してください。"""
            
            full_prompt = f"""
コンテキスト情報:
{context}

質問: {question}

上記のコンテキスト情報を基に、質問に回答してください。"""
            
            response = llm_service._generate_bedrock_streaming(
                full_prompt, 
                system_prompt, 
                bedrock_progress_callback
            )
        else:
            # フォールバック
            response = _generate_qa_response(llm_service, question, search_results)
            answer_container.markdown(f"**回答:**\n\n{response}")
        
        # 完了表示
        progress_bar.progress(1.0)
        spinner_placeholder.empty()
        st.success("✅ 回答完了")
        
    except Exception as e:
        st.error(f"ストリーミング応答生成中にエラーが発生しました: {str(e)}")
        logger.error(f"Bedrock streaming error: {e}")

def render_ollama_step_response(llm_service, question: str, search_results: List[Dict], show_thinking: bool):
    """Ollamaステップ表示応答を表示"""
    progress_bar = st.progress(0)
    spinner_placeholder = st.empty()
    step_container = st.empty()
    answer_container = st.empty()
    
    def ollama_progress_callback(progress: float, message: str):
        # プログレス値の範囲チェック
        if progress > 1.0:
            progress = 1.0
        elif progress < 0.0:
            progress = 0.0
        
        # プログレスバー更新
        progress_bar.progress(progress)
        
        # ステップ表示
        step_messages = {
            0.0: "コンテキスト情報を分析中...",
            0.3: "関連する検証結果を整理中...",
            0.6: "回答を生成中...",
            0.9: "回答を最終調整中..."
        }
        
        current_step = "回答を生成中..."
        for threshold, step_msg in step_messages.items():
            if progress >= threshold:
                current_step = step_msg
        
        # スピナーで進捗表示
        with spinner_placeholder:
            with st.spinner(f"実行中... {progress*100:.1f}%済み"):
                if show_thinking:
                    step_container.info(f"🔄 {current_step}")
    
    try:
        # 段階的に進捗を更新しながら回答生成
        ollama_progress_callback(0.1, "開始")
        
        # RAGコンテキストを準備
        context = _prepare_rag_context(search_results)
        ollama_progress_callback(0.3, "コンテキスト準備完了")
        
        # 回答生成
        response = _generate_qa_response(llm_service, question, search_results)
        ollama_progress_callback(0.9, "回答生成完了")
        
        # 回答表示
        answer_container.markdown(f"**回答:**\n\n{response}")
        
        # 完了表示
        progress_bar.progress(1.0)
        spinner_placeholder.empty()
        st.success("✅ 回答完了")
        
    except Exception as e:
        st.error(f"ステップ応答生成中にエラーが発生しました: {str(e)}")
        logger.error(f"Ollama step error: {e}")

def render_normal_response(llm_service, question: str, search_results: List[Dict]):
    """通常の応答を表示"""
    with st.spinner("AI回答を生成中..."):
        try:
            response = _generate_qa_response(llm_service, question, search_results)
            st.markdown(f"**回答:**\n\n{response}")
            st.success("✅ 回答完了")
        except Exception as e:
            st.error(f"回答生成中にエラーが発生しました: {str(e)}")
            logger.error(f"Normal response error: {e}")

def _search_batches_directly(question: str, batches: List[Dict], top_k: int = 5) -> List[Dict]:
    """バッチデータから直接関連するものを検索"""
    question_lower = question.lower()
    scored_batches = []
    
    for batch in batches:
        score = 0
        
        # 名前での一致
        if any(word in batch.get('name', '').lower() for word in question_lower.split()):
            score += 3
        
        # 試験ブロックでの一致
        if any(word in batch.get('test_block', '').lower() for word in question_lower.split()):
            score += 2
        
        # ステータスでの一致
        if '失敗' in question_lower and batch.get('status') == 'failed':
            score += 5
        if '成功' in question_lower and batch.get('status') == 'completed':
            score += 3
        if '実行中' in question_lower and batch.get('status') == 'running':
            score += 5
        
        # 今日の検証
        if '今日' in question_lower or '本日' in question_lower:
            created_at = batch.get('created_at', '')
            if '2025-09-07' in created_at:  # 今日の日付
                score += 4
        
        # 設備タイプでの一致
        if 'ericsson' in question_lower or 'nokia' in question_lower or 'samsung' in question_lower:
            # 結果から設備タイプを確認
            results = batch.get('results', [])
            for result in results:
                equipment_type = result.get('equipment_type', '')
                if any(vendor in equipment_type for vendor in ['Ericsson', 'Nokia', 'Samsung']):
                    score += 2
                    break
        
        if score > 0:
            batch_copy = batch.copy()
            batch_copy['search_score'] = score
            scored_batches.append(batch_copy)
    
    # スコアでソート
    scored_batches.sort(key=lambda x: x['search_score'], reverse=True)
    
    return scored_batches[:top_k]

def _prepare_rag_context(search_results) -> str:
    """RAGコンテキストを準備（ベクター検索とバッチ検索の統合）"""
    context_parts = []
    
    # 新しい構造（辞書形式）の場合
    if isinstance(search_results, dict):
        # ベクター検索結果を処理
        vector_results = search_results.get('vector_results', [])
        if vector_results:
            context_parts.append("【ベクター検索による関連検証結果】")
            for i, result in enumerate(vector_results[:3]):  # 上位3件
                context_parts.append(f"""
検証結果 {i+1} (類似度: {result.get('similarity', 0):.2f}):
{result.get('content', 'Unknown')}
""")
        
        # バッチ検索結果を処理
        batch_results = search_results.get('batch_results', [])
        if batch_results:
            context_parts.append("\n【バッチ検索による関連検証バッチ】")
            for i, result in enumerate(batch_results):
                context_parts.append(f"""
検証バッチ {i+1}:
- 名前: {result.get('name', 'Unknown')}
- 実行日: {result.get('created_at', 'Unknown')}
- ステータス: {result.get('status', 'Unknown')}
- 試験ブロック: {result.get('test_block', 'Unknown')}""")
                
                # 結果の詳細
                if result.get('results'):
                    results = result['results']
                    success_count = len([r for r in results if r.get('result') == 'PASS'])
                    fail_count = len([r for r in results if r.get('result') == 'FAIL'])
                    total_count = len(results)
                    
                    context_parts.append(f"""- 検証結果: 成功 {success_count}件、失敗 {fail_count}件、合計 {total_count}件
- 成功率: {success_count/total_count*100:.1f}%""")
    
    # 従来の構造（リスト形式）の場合
    elif isinstance(search_results, list):
        if not search_results:
            return "関連する検証バッチが見つかりませんでした。"
        
        context_parts.append("【検索による関連検証バッチ】")
        for i, result in enumerate(search_results):
            context_parts.append(f"""
検証バッチ {i+1}:
- 名前: {result.get('name', 'Unknown')}
- 実行日: {result.get('created_at', 'Unknown')}
- ステータス: {result.get('status', 'Unknown')}
- 試験ブロック: {result.get('test_block', 'Unknown')}""")
        
        # 結果の詳細
        if result.get('results'):
            results = result['results']
            success_count = len([r for r in results if r.get('result') == 'PASS'])
            fail_count = len([r for r in results if r.get('result') == 'FAIL'])
            total_count = len(results)
            
            context_parts.append(f"""- 検証結果: 成功 {success_count}件、失敗 {fail_count}件、合計 {total_count}件
- 成功率: {success_count/total_count*100:.1f}%""")
            
            # 失敗した項目の詳細
            failed_items = [r for r in results if r.get('result') == 'FAIL']
            if failed_items:
                context_parts.append("- 失敗した検証項目:")
                for item in failed_items[:3]:  # 最大3件まで
                    condition = item.get('condition_text', item.get('test_condition', 'Unknown'))
                    equipment = item.get('equipment_type', 'Unknown')
                    reason = item.get('failure_reason', item.get('analysis', '詳細不明'))
                    context_parts.append(f"  * 条件: {condition}")
                    context_parts.append(f"    設備: {equipment}")
                    context_parts.append(f"    失敗理由: {reason}")
            
            # 成功した項目の例
            success_items = [r for r in results if r.get('result') == 'PASS']
            if success_items and len(success_items) <= 3:
                context_parts.append("- 成功した検証項目:")
                for item in success_items[:2]:  # 最大2件まで
                    condition = item.get('condition_text', item.get('test_condition', 'Unknown'))
                    equipment = item.get('equipment_type', 'Unknown')
                    context_parts.append(f"  * 条件: {condition} (設備: {equipment})")
        
        # テスト項目の詳細
        if result.get('test_items'):
            test_items = result['test_items']
            context_parts.append(f"- テスト項目数: {len(test_items)}件")
            for item in test_items[:2]:  # 最大2件まで
                context_parts.append(f"  * {item.get('condition_text', 'Unknown')}")
    
    # どちらの構造でもない場合
    if not context_parts:
        return "関連する検証データが見つかりませんでした。"
    
    return "\n".join(context_parts)

def _generate_qa_response(llm_service, question: str, search_results: List[Dict]) -> str:
    """QA応答を生成"""
    context = _prepare_rag_context(search_results)
    
    system_prompt = """あなたはネットワーク設備検証のエキスパートです。RAGシステムによって検索された関連検証バッチを基に、質問に対して正確で実用的な回答を提供してください。

【回答指針】
- 検索された検証バッチの内容を最優先に活用してください
- 検証結果に記載されていない内容は推測せず、「検証結果に記載なし」と明記してください
- ネットワーク設備の専門用語を正確に使用してください
- 回答は簡潔で読みやすい形式で提供してください

【回答形式】
以下の形式で回答してください（記号は使用せず、シンプルなテキストで）：

回答: [質問への直接的な回答]

根拠: [回答の根拠となる具体的な検証バッチ情報（バッチ名と結果を明記）]

追加情報: [検索された検証バッチから得られる関連する重要な補足情報]

推奨対応: [必要に応じた具体的な推奨対応策]

ネットワーク設備検証の専門知識とRAGシステムで検索された最新情報を組み合わせ、実用的で具体的な回答を提供してください。"""
    
    prompt = f"""
質問: {question}

検索された関連検証バッチ:
{context}

上記の検証バッチ情報を基に、指定された形式で回答してください。"""
    
    return llm_service.generate_response(prompt, system_prompt)
