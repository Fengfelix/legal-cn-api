#!/usr/bin/env python3
"""Clean index.json to remove navigation links"""

import json

with open("index.json", "r", encoding="utf-8") as f:
    data = json.load(f)

original_count = len(data["laws"])
cleaned = []

for law in data["laws"]:
    title = law["title"].strip()
    # Skip if title contains Chinese characters
    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in title)
    if has_chinese:
        print(f"Skipping Chinese title: {title}")
        continue
    # Skip short titles
    if len(title) < 10:
        print(f"Skipping short title: {title}")
        continue
    cleaned.append(law)

data["laws"] = cleaned
data["total"] = len(cleaned)

with open("index_clean.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\nCleaned: {original_count} -> {len(cleaned)}")
