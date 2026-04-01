#!/usr/bin/env python3
"""
Convert scraped English laws to document format for Meilisearch
"""

import json
import os
from typing import Dict, List

INDEX_FILE = "index_clean.json"
OUTPUT_FILE = "documents.jsonl"

def process_law(law_info: Dict) -> List[Dict]:
    """Convert a scraped law to documents (split by article/section)"""
    
    if law_info["type"] == "pdf":
        # PDF, we don't process text now, just note it
        return [{
            "id": f"english-{law_info['title'].replace(' ', '-').lower()[:80]}",
            "law_title_en": law_info["title"],
            "law_title": "",  # will add later if we have Chinese name
            "content_en": f"PDF available: {law_info['filename']}",
            "category": "law",
            "language": "en",
            "url": law_info["url"],
            "source": "npc-english-official"
        }]
    
    # Load the JSON
    filename = law_info["filename"]
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    content = data["content"]
    paragraphs = data.get("paragraphs", [])
    
    # Split into documents - we'll make the entire law one document for now
    # can split later if needed
    # Remove invalid characters from ID
    safe_title = law_info['title'].lower().replace(' ', '-')
    # Keep only alphanumeric, hyphen, underscore
    safe_title = ''.join([c for c in safe_title if c.isalnum() or c in '-_'])
    doc_id = f"english-{safe_title[:80]}"
    
    return [{
        "id": doc_id,
        "law_title_en": law_info["title"],
        "law_title": "",  # keep empty for now, can match with Chinese later
        "content_en": content,
        "content": "",  # no Chinese here
        "category": "law",
        "language": "en",
        "article_no": "",
        "article_title": "",
        "effective_date": "",
        "url": law_info["url"],
        "source": "npc-english-official"
    }]

def main():
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)
    
    laws = index["laws"]
    print(f"Processing {len(laws)} laws...")
    
    documents = []
    skipped = 0
    for law in laws:
        # Skip short navigation links
        if len(law["title"].strip()) < 3:
            skipped += 1
            print(f"Skipping short title: {law['title']}")
            continue
        docs = process_law(law)
        documents.extend(docs)
    
    print(f"Generated {len(documents)} documents (skipped {skipped})")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for doc in documents:
            json.dump(doc, f, ensure_ascii=False)
            f.write("\n")
    
    print(f"Saved to {OUTPUT_FILE}")
    print(f"\nSummary:")
    print(f"  Total laws: {len(laws)}")
    print(f"  Skipped: {skipped}")
    print(f"  Total documents: {len(documents)}")

if __name__ == "__main__":
    main()
