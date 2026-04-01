#!/usr/bin/env python3
"""
Split English laws into paragraph-level documents for Meilisearch
"""

import json
import os
import re

INDEX_FILE = "index_clean.json"
OUTPUT_FILE = "documents_split.jsonl"

def split_law(law_info):
    """Split a law into paragraph-level documents"""
    filename = law_info["filename"]
    
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    content = data["content"]
    paragraphs = data.get("paragraphs", [])
    
    # Filter out empty paragraphs
    paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 10]
    
    documents = []
    law_title_en = law_info["title"]
    
    # Article/Chapter pattern matching
    # Common patterns: "Article 1", "Chapter I", "Section 1", etc.
    article_pattern = re.compile(r'^(Article|Article\s+\d+|Chapter|Section)\s+', re.IGNORECASE)
    
    current_article = ""
    current_content = []
    para_index = 0
    
    for i, para in enumerate(paragraphs):
        if article_pattern.match(para) or para.startswith("(") and ")" in para and len(para) < 30:
            # New article/section started
            if current_article and current_content:
                # Save previous article
                combined = "\n\n".join(current_content)
                doc_id = f"english-{law_title_en.lower().replace(' ', '-')[:60]}-para-{para_index}"
                doc_id = "".join([c for c in doc_id if c.isalnum() or c in '-_'])
                documents.append({
                    "id": doc_id,
                    "law_title_en": law_title_en,
                    "law_title": "",
                    "article_no": f"para-{para_index}",
                    "article_title": current_article.split('\n')[0] if current_article else "",
                    "content_en": combined,
                    "content": "",
                    "category": "law",
                    "language": "en",
                    "effective_date": "",
                    "url": law_info["url"],
                    "source": "npc-english-official"
                })
                para_index += 1
            
            current_article = para
            current_content = [para]
        else:
            current_content.append(para)
    
    # Save the last article
    if current_article and current_content:
        combined = "\n\n".join(current_content)
        doc_id = f"english-{law_title_en.lower().replace(' ', '-')[:60]}-para-{para_index}"
        doc_id = "".join([c for c in doc_id if c.isalnum() or c in '-_'])
        documents.append({
            "id": doc_id,
            "law_title_en": law_title_en,
            "law_title": "",
            "article_no": f"para-{para_index}",
            "article_title": current_article.split('\n')[0] if current_article else "",
            "content_en": combined,
            "content": "",
            "category": "law",
            "language": "en",
            "effective_date": "",
            "url": law_info["url"],
            "source": "npc-english-official"
        })
    
    print(f"  {law_title_en}: {len(documents)} paragraphs")
    return documents

def main():
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)
    
    laws = index["laws"]
    print(f"Splitting {len(laws)} laws...")
    
    all_documents = []
    total_paragraphs = 0
    
    for law in laws:
        docs = split_law(law)
        all_documents.extend(docs)
        total_paragraphs += len(docs)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for doc in all_documents:
            json.dump(doc, f, ensure_ascii=False)
            f.write("\n")
    
    print(f"\nDone!")
    print(f"  Total laws: {len(laws)}")
    print(f"  Total paragraph documents: {total_paragraphs}")

if __name__ == "__main__":
    main()
