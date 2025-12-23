#!/usr/bin/env python3
"""生成測試用的 Deck JSON 檔案"""

import json
import sys
from pathlib import Path

from learn2cards.agent_a import generate_deck, AgentAOptions

def main():
    # 測試文字
    test_text = """專案目標是把長文轉成一疊可翻閱的卡片，方便快速掌握重點。每張卡片會包含摘要和關鍵詞。系統會自動將相似主題的段落分群。使用者可以透過翻卡片的方式快速瀏覽內容。這個功能特別適合用來整理學習筆記。"""
    
    # 設定選項
    options = AgentAOptions(
        topicThreshold=0.75,
        maxTopics=5,
        maxBulletsPerCard=5,
    )
    
    # 生成 deck
    print("正在生成卡片...", file=sys.stderr)
    deck = generate_deck(test_text, options=options, debug=True)
    
    # 輸出到檔案
    output_path = Path(__file__).parent / "test_deck.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(deck.model_dump(), f, ensure_ascii=False, indent=2, sort_keys=True)
    
    print(f"\n✓ 已成功生成測試檔案：{output_path}", file=sys.stderr)
    print(f"  - 段落數：{deck.stats.paragraphCount}", file=sys.stderr)
    print(f"  - 主題數：{deck.stats.topicCount}", file=sys.stderr)
    print(f"  - 卡片數：{deck.stats.cardCount}", file=sys.stderr)
    
    # 同時輸出到 stdout（方便查看）
    print("\n生成的 JSON 內容：")
    print(json.dumps(deck.model_dump(), ensure_ascii=False, indent=2, sort_keys=True))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

