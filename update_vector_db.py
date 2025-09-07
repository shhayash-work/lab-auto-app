#!/usr/bin/env python3
"""リアルな検証データをベクターDBに登録"""

import json
from app.services.vector_store import get_vector_store

def update_vector_db_with_realistic_data():
    """リアルな検証データをベクターDBに登録"""
    
    print("🔄 ベクターDBにリアルな検証データを登録中...")
    
    # リアルなデータを読み込み
    try:
        with open('data/realistic/realistic_batches.json', 'r', encoding='utf-8') as f:
            batches = json.load(f)
    except Exception as e:
        print(f"❌ データ読み込みエラー: {e}")
        return
    
    # ベクターストアを取得
    vector_store = get_vector_store()
    
    # 各バッチの検証項目をベクターDBに追加
    added_count = 0
    for batch in batches:
        batch_name = batch.get('name', '')
        test_items = batch.get('test_items', [])
        
        for item in test_items:
            # ドキュメント作成
            content = f"""
試験ブロック: {item.get('test_block', '')}
カテゴリ: {item.get('category', '')}
検証条件: {item.get('condition', {}).get('condition_text', '')}
期待件数: {item.get('condition', {}).get('expected_count', 0)}
対象設備: {', '.join(item.get('condition', {}).get('equipment_types', []))}
バッチ名: {batch_name}
"""
            
            # ドキュメントIDを生成
            doc_id = f"realistic_{batch.get('id', '')}_{item.get('id', '')}"
            
            # ベクターDBに追加
            try:
                vector_store.add_document(doc_id, content, {
                    'batch_name': batch_name,
                    'test_block': item.get('test_block', ''),
                    'category': item.get('category', ''),
                    'source': 'realistic_data'
                })
                added_count += 1
            except Exception as e:
                print(f"⚠️  ドキュメント追加エラー: {e}")
    
    print(f"✅ ベクターDB登録完了: {added_count}件の検証項目を追加しました")

if __name__ == "__main__":
    update_vector_db_with_realistic_data()
