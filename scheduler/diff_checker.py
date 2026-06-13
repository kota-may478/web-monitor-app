"""差分検出ユーティリティ"""

import hashlib


def compute_item_hash(text: str) -> str:
    """テキストのSHA256ハッシュ先頭16文字を返す（同一性判定用）"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def detect_new_items(
    current_items: list[dict],
    previous_items: list[dict],
) -> list[dict]:
    """
    current_items の中で previous_items に存在しないものを返す。
    text フィールドのハッシュで同一性を判定する。
    """
    previous_hashes = {compute_item_hash(item.get("text", "")) for item in previous_items}
    new_items: list[dict] = []
    for item in current_items:
        item_hash = compute_item_hash(item.get("text", ""))
        if item_hash not in previous_hashes:
            new_items.append(item)
    return new_items


def merge_items(
    current_items: list[dict],
    previous_items: list[dict],
    max_items: int = 50,
) -> list[dict]:
    """
    current_items と previous_items をマージし、重複を排除して返す。
    max_items を超える場合は新しいものを優先して切り詰める。
    """
    seen_hashes: set[str] = set()
    merged: list[dict] = []

    for item in current_items + previous_items:
        item_hash = compute_item_hash(item.get("text", ""))
        if item_hash in seen_hashes:
            continue
        seen_hashes.add(item_hash)
        merged.append(item)
        if len(merged) >= max_items:
            break

    return merged
