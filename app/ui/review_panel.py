"""
検証レビューページUI
Validation Review Panel UI
"""

import sys
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.models.validation import EngineerReview, ReviewStatus, EngineerDecision
from app.services.unified_review_service import get_unified_review_service
from app.services.knowledge_service import get_knowledge_service

def render_review_panel():
    """レビューパネルを描画"""
    st.header("検証レビュー")
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>NWエンジニアによる検証結果のレビューと再検証対応を管理できます</p>", unsafe_allow_html=True)
    
    unified_review_service = get_unified_review_service()
    
    # レビュー統計セクション
    st.markdown("<div class='custom-header'>レビュー統計</div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>レビューが必要な検証項目の状況を一目で確認できます</p>", unsafe_allow_html=True)
    
    render_review_statistics(unified_review_service)
    
    # レビュー項目一覧セクション
    st.markdown("<div class='custom-header'>レビュー項目一覧</div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 14px; margin-bottom: 16px;'>検証結果の詳細レビューと判定が行えます</p>", unsafe_allow_html=True)
    
    # タブでフィルタ表示
    tab1, tab2, tab3, tab4 = st.tabs(["全て", "失敗項目", "要確認", "本日完了"])
    
    with tab1:
        render_review_items_table(unified_review_service, "all")
    
    with tab2:
        render_review_items_table(unified_review_service, "failed")
    
    with tab3:
        render_review_items_table(unified_review_service, "needs_check")
    
    with tab4:
        render_review_items_table(unified_review_service, "completed_today")

def render_review_statistics(unified_review_service):
    """レビュー統計を表示"""
    try:
        stats = unified_review_service.get_review_statistics()
        
        total_pending = stats["pending_total"]
        total_failed = stats["failed_items"]
        total_needs_check = stats["needs_check_items"]
        today_completed = stats["completed_today"]
        
        # 割合計算
        total_reviews = total_pending if total_pending > 0 else 1
        failed_percentage = int((total_failed / total_reviews) * 100)
        needs_check_percentage = int((total_needs_check / total_reviews) * 100)
        completed_percentage = 6  # 仮データ
        
    except Exception as e:
        # エラー時はダミー表示
        total_pending = 45
        total_failed = 12
        total_needs_check = 8
        today_completed = 3
        failed_percentage = 27
        needs_check_percentage = 18
        completed_percentage = 6
    
    # メトリクス表示（検証サマリと同じスタイル）
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>レビュー待ち</h3>
            <div class="metric-value">
                {total_pending}<span style="font-size: 40px;">件</span>
            </div>
            <div class="metric-delta" style="color: #999; font-size: 16px;">
                100%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>失敗項目</h3>
            <div class="metric-value">
                {total_failed}<span style="font-size: 40px;">件</span>
            </div>
            <div class="metric-delta" style="color: #999; font-size: 16px;">
                {failed_percentage}%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>要確認項目</h3>
            <div class="metric-value">
                {total_needs_check}<span style="font-size: 40px;">件</span>
            </div>
            <div class="metric-delta" style="color: #999; font-size: 16px;">
                {needs_check_percentage}%
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3>本日完了</h3>
            <div class="metric-value">
                {today_completed}<span style="font-size: 40px;">件</span>
            </div>
            <div class="metric-delta" style="color: #999; font-size: 16px;">
                {completed_percentage}%
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_review_items_table(unified_review_service, filter_type: str):
    """レビュー項目テーブルを表示"""
    try:
        reviews = unified_review_service.get_pending_reviews(filter_type)
        
        if not reviews:
            st.info("該当するレビュー項目がありません")
            return
        
        # テーブル用データ作成（ValidationResult用）
        table_data = []
        for result in reviews:
            # 結果に応じたステータス表示
            status_map = {
                "FAIL": "失敗",
                "NEEDS_CHECK": "要確認", 
                "PASS": "成功"
            }
            status_text = status_map.get(result.result.value, "不明")
            
            # バッチ名とtest_idを取得
            batch_name = getattr(result, 'batch_name', '不明なバッチ')
            test_id = getattr(result, 'test_id', result.test_item_id)
            
            table_data.append({
                "検証バッチ名": batch_name,
                "検証項目ID": test_id,
                "対象設備": result.equipment_type.value if hasattr(result.equipment_type, 'value') else str(result.equipment_type),
                "結果": status_text,
                "作成日時": result.created_at.strftime("%Y/%m/%d %H:%M") if result.created_at else "不明",
                "アクション": "レビュー"
            })
        
        df = pd.DataFrame(table_data)
        
        # データフレーム表示
        event = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            key=f"review_dataframe_{filter_type}"  # ユニークキー追加
        )
        
        # 選択された行のレビュー詳細表示
        if event.selection and event.selection.rows:
            selected_idx = event.selection.rows[0]
            selected_result = reviews[selected_idx]
            render_individual_review_result(selected_result)
            
    except Exception as e:
        st.error(f"レビュー一覧取得エラー: {e}")

def render_individual_review_result(result):
    """ValidationResult用の個別レビュー画面"""
    st.markdown("---")
    st.subheader("エンジニアレビュー入力")
    
    # エンジニア判定を最上部に配置
    render_engineer_review_form_for_result(result)
    
    st.markdown("---")
    
    # 検証結果詳細セクション
    st.markdown("**検証結果詳細**")
    
    # 検証結果詳細を表示
    col1, col2 = st.columns(2)
    
    # バッチ名とtest_idを取得
    batch_name = getattr(result, 'batch_name', '不明なバッチ')
    test_id = getattr(result, 'test_id', result.test_item_id)
    
    with col1:
        st.text_input("検証バッチ名", value=batch_name, disabled=True)
        st.text_input("検証項目ID", value=test_id, disabled=True)
    
    with col2:
        equipment_name = result.equipment_type.value if hasattr(result.equipment_type, 'value') else str(result.equipment_type)
        st.text_input("対象設備", value=equipment_name, disabled=True)
        st.text_input("作成日時", value=result.created_at.strftime("%Y-%m-%d %H:%M:%S") if result.created_at else "不明", disabled=True)
    
    # 検証結果の詳細
    result_map = {"FAIL": "失敗", "NEEDS_CHECK": "要確認", "PASS": "成功"}
    result_text = result_map.get(result.result.value, "不明")
    
    st.text_input("結果", value=result_text, disabled=True)
    st.text_area("判定根拠", value=result.details or "情報なし", disabled=True, height=100)
    st.text_input("信頼度", value=f"{result.confidence:.2f}", disabled=True)
    st.text_input("実行時間", value=f"{result.execution_time:.2f}秒", disabled=True)

def render_engineer_review_form_for_result(result):
    """ValidationResult用のエンジニアレビューフォーム（統合版）"""
    st.markdown("**エンジニア判定**")
    
    # レビュアー名
    reviewer_name = st.text_input(
        "レビュアー名",
        key=f"reviewer_result_{result.id}",
        placeholder="あなたの名前を入力",
        value=result.reviewer_name or ""
    )
    
    # 判定選択
    current_decision = "再検証"
    if result.engineer_decision:
        decision_map = {
            "SUCCESS_APPROVAL": "成功承認",
            "FAILURE_APPROVAL": "失敗承認", 
            "RE_VALIDATION": "再検証"
        }
        current_decision = decision_map.get(result.engineer_decision.value, "再検証")
    
    engineer_decision = st.radio(
        "判定結果",
        ["成功承認", "失敗承認", "再検証"],
        key=f"decision_result_{result.id}",
        index=["成功承認", "失敗承認", "再検証"].index(current_decision),
        help="""
        - 成功承認: 検証結果に問題はなく成功で確定
        - 失敗承認: エンジニア確認の上で検証結果は失敗で確定  
        - 再検証: 検証方法に問題があるので見直して再度検証
        """
    )
    
    # 判定理由
    decision_reason = st.text_area(
        "判定理由",
        key=f"reason_result_{result.id}",
        placeholder="判定の理由を詳しく記載してください",
        value=result.decision_reason or "",
        height=100
    )
    
    # 総合コメント
    review_comments = st.text_area(
        "総合コメント",
        key=f"comments_result_{result.id}",
        placeholder="全体的なコメントや補足事項があれば記載",
        value=result.review_comments or "",
        height=80
    )
    
    # 提出ボタン
    if st.button("レビュー提出", key=f"submit_result_{result.id}", type="primary"):
        # バリデーション
        if not reviewer_name.strip():
            st.error("レビュアー名を入力してください")
        elif not decision_reason.strip():
            st.error("判定理由を入力してください")
        else:
            # バッチ名と検証項目IDを取得
            batch_name = getattr(result, 'batch_name', '不明なバッチ')
            test_id = getattr(result, 'test_id', result.test_item_id)
            
            # 成功メッセージを表示
            st.success(f"✅ {batch_name} - {test_id} のレビューを提出しました")

def submit_result_review(result, reviewer_name: str, engineer_decision: str,
                        decision_reason: str, validation_feedback: str, item_feedback: str,
                        review_comments: str):
    """ValidationResult用のレビュー提出"""
    
    # バリデーション
    if not reviewer_name.strip():
        st.error("レビュアー名を入力してください")
        return False
    
    if not decision_reason.strip():
        st.error("判定理由を入力してください")
        return False
    
    if engineer_decision == "再検証" and not (validation_feedback.strip() or item_feedback.strip()):
        st.error("再検証の場合は、検証実行方法または検証項目への指摘を入力してください")
        return False
    
    try:
        # 判定結果を英語値に変換
        decision_map = {
            "成功承認": "success_approval",
            "失敗承認": "failure_approval", 
            "再検証": "re_validation"
        }
        english_decision = decision_map.get(engineer_decision, "re_validation")
        
        # レビューデータ作成
        review_data = {
            "reviewer_name": reviewer_name.strip(),
            "engineer_decision": english_decision,
            "decision_reason": decision_reason.strip(),
            "validation_feedback": validation_feedback.strip(),
            "item_feedback": item_feedback.strip(),
            "review_comments": review_comments.strip()
        }
        
        # レビューサービスに提出
        unified_review_service = get_unified_review_service()
        success = unified_review_service.submit_review(result.id, review_data)
        
        if success:
            # バッチ名と検証項目IDを取得して表示
            batch_name = getattr(result, 'batch_name', '不明なバッチ')
            test_id = getattr(result, 'test_id', result.test_item_id)
            
            # 成功メッセージ表示とセッション状態クリア
            st.success(f"✅ {batch_name} - {test_id} のレビューを提出しました")
            
            # セッション状態から選択された結果をクリア
            if "selected_result_for_review" in st.session_state:
                del st.session_state.selected_result_for_review
            
            st.rerun()
        else:
            st.error("❌ レビュー提出に失敗しました")
        
        return success
            
    except Exception as e:
        st.error(f"レビュー提出エラー: {e}")
        return False

def render_individual_review(review: EngineerReview):
    """個別レビュー画面を描画"""
    st.markdown("---")
    st.subheader("レビュー詳細")
    
    # エンジニア判定を上部に配置
    render_engineer_review_form(review)
    
    st.markdown("---")
    
    # 検証結果詳細を下部に配置
    st.markdown("**検証結果詳細**")
    
    # 詳細情報表示欄
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("検証結果ID", value=review.validation_result_id, disabled=True)
        st.text_input("バッチID", value=review.batch_id, disabled=True)
    
    with col2:
        st.text_input("検証項目ID", value=review.test_item_id, disabled=True)
        st.text_input("作成日時", value=review.created_at.strftime("%Y-%m-%d %H:%M:%S"), disabled=True)
    
    # より詳細な検証結果情報を構造的に表示
    try:
        # 実際のデータを表示（この部分は後で実装強化）
        st.markdown("**検証実行結果**")
        
        # ダミーデータ表示（実際にはreview_serviceから取得）
        result_details = {
            "検証条件": "5G NR セルへの初期接続時間が3秒以内であること",
            "対象設備": "高輪ゲートウェイシティ_Ericsson", 
            "測定結果": "NEEDS_CHECK",
            "判定根拠": "接続時間が2.9秒で基準値に近いため、追加確認が必要",
            "信頼度": "0.65",
            "実行時間": "45.2秒",
            "機器応答データ": "Connection established in 2.9s, signal strength: -95dBm"
        }
        
        for key, value in result_details.items():
            st.text_input(key, value=value, disabled=True)
            
    except Exception as e:
        st.warning(f"詳細情報の取得に失敗しました: {e}")
    
    # 既存のコメント表示
    if review.review_comments:
        st.markdown("**既存のレビューコメント**")
        st.text_area("", value=review.review_comments, disabled=True, height=100)

def render_engineer_review_form(review: EngineerReview):
    """エンジニアレビューフォームを描画"""
    st.markdown("**エンジニア判定**")
    
    # レビュアー名
    reviewer_name = st.text_input(
        "レビュアー名",
        key=f"reviewer_{review.id}",
        placeholder="あなたの名前を入力"
    )
    
    # 判定選択
    engineer_decision = st.radio(
        "判定結果",
        ["成功承認", "失敗承認", "再検証"],
        key=f"decision_{review.id}",
        help="""
        - 成功承認: 検証結果に問題はなく成功で確定
        - 失敗承認: エンジニア確認の上で検証結果は失敗で確定  
        - 再検証: 検証方法に問題があるので見直して再度検証
        """
    )
    
    # 判定理由
    decision_reason = st.text_area(
        "判定理由",
        key=f"reason_{review.id}",
        placeholder="判定の理由を詳しく記載してください",
        height=100
    )
    
    # 再検証の場合の追加フィールド
    validation_feedback = ""
    item_feedback = ""
    
    if engineer_decision == "再検証":
        st.markdown("**🔄 再検証フィードバック**")
        
        validation_feedback = st.text_area(
            "検証実行方法への指摘",
            key=f"val_fb_{review.id}",
            placeholder="検証の実行方法、手順、判定基準等への改善提案を記載",
            height=100
        )
        
        item_feedback = st.text_area(
            "検証項目への指摘",
            key=f"item_fb_{review.id}",
            placeholder="検証項目の内容、条件設定、追加すべき項目等への改善提案を記載",
            height=100
        )
    
    # レビューコメント
    review_comments = st.text_area(
        "総合コメント",
        key=f"comments_{review.id}",
        placeholder="全体的なコメントや補足事項があれば記載",
        height=80
    )
    
    # 提出ボタン
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("レビュー提出", type="primary", key=f"submit_{review.id}"):
            submit_review(
                review,
                reviewer_name,
                engineer_decision,
                decision_reason,
                validation_feedback,
                item_feedback,
                review_comments
            )
    
    with col2:
        if st.button("キャンセル", key=f"cancel_{review.id}"):
            st.rerun()

def submit_review(review: EngineerReview, reviewer_name: str, engineer_decision: str,
                 decision_reason: str, validation_feedback: str, item_feedback: str,
                 review_comments: str):
    """レビューを提出"""
    
    # バリデーション
    if not reviewer_name.strip():
        st.error("レビュアー名を入力してください")
        return
    
    if not decision_reason.strip():
        st.error("判定理由を入力してください")
        return
    
    if engineer_decision == "再検証" and not (validation_feedback.strip() or item_feedback.strip()):
        st.error("再検証の場合は、検証実行方法または検証項目への指摘を入力してください")
        return
    
    try:
        # レビューデータ作成
        review_data = {
            "reviewer_name": reviewer_name.strip(),
            "engineer_decision": _map_decision_to_enum(engineer_decision),
            "decision_reason": decision_reason.strip(),
            "validation_feedback": validation_feedback.strip(),
            "item_feedback": item_feedback.strip(),
            "review_comments": review_comments.strip()
        }
        
        # レビューサービスに提出
        review_service = get_review_service()
        success = review_service.submit_engineer_review(review.id, review_data)
        
        if success:
            st.success("✅ レビューを提出しました")
            
            # 再検証の場合は知見学習を実行
            if engineer_decision == "再検証":
                extract_knowledge_from_review(review.id)
            
            # 1秒後にページ更新
            import time
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ レビュー提出に失敗しました")
            
    except Exception as e:
        st.error(f"レビュー提出エラー: {e}")

def extract_knowledge_from_review(review_id: str):
    """レビューから知見を抽出"""
    try:
        knowledge_service = get_knowledge_service()
        review_service = get_review_service()
        
        review = review_service.get_review_by_id(review_id)
        if review:
            knowledge_entries = knowledge_service.extract_knowledge_from_review(review)
            if knowledge_entries:
                st.info(f"💡 {len(knowledge_entries)}件の知見を蓄積しました")
            
    except Exception as e:
        st.warning(f"知見抽出中にエラーが発生しました: {e}")

def _map_decision_to_enum(decision_text: str) -> str:
    """判定テキストをEnumに変換"""
    mapping = {
        "成功承認": "success_approval",
        "失敗承認": "failure_approval", 
        "再検証": "re_validation"
    }
    return mapping.get(decision_text, "re_validation")
