"""差分検出ユーティリティ"""

import hashlib


def compute_item_hash(text: str) -> str:
    """テキストのSHA256ハッシュ先頭16文字を返す（同一性判定用）"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _item_key(item: dict) -> str:
    """差分検出用の安定キー。title+url があれば優先する。"""
    title = (item.get("title") or "").strip()
    url = (item.get("url") or "").strip()
    if title:
        return f"{title}|{url}"
    return compute_item_hash(item.get("text", ""))


def detect_new_items(
    current_items: list[dict],
    previous_items: list[dict],
) -> list[dict]:
    """
    current_items の中で previous_items に存在しないものを返す。
    title+url または text のハッシュで同一性を判定する。
    """
    previous_keys = {_item_key(item) for item in previous_items}
    return [item for item in current_items if _item_key(item) not in previous_keys]


def merge_items(
    current_items: list[dict],
    previous_items: list[dict],
    max_items: int = 50,
) -> list[dict]:
    """
    current_items と previous_items をマージし、重複を排除して返す。
    max_items を超える場合は新しいものを優先して切り詰める。
    """
    seen: set[str] = set()
    merged: list[dict] = []

    for item in current_items + previous_items:
        key = _item_key(item)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
        if len(merged) >= max_items:
            break

    return merged
