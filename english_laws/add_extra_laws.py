#!/usr/bin/env python3
"""
Add Labor Law and Labor Contract Law to documents
"""

import json
import os
import re

OUTPUT_FILE = "documents_split.jsonl"

def split_into_paragraphs(content, law_title):
    """Split full text into paragraph documents"""
    documents = []
    
    # Split by article
    # Article pattern: "Article XXXX" or "Article \d+"
    article_pattern = re.compile(r'(Article \d+[^\n]*)\n')
    
    paragraphs = article_pattern.split(content)
    
    # The first part is preamble/table of contents
    if paragraphs:
        current_article = "Preamble"
        current_content = paragraphs[0]
        for i in range(1, len(paragraphs), 2):
            article_title = paragraphs[i].strip()
            if i+1 < len(paragraphs):
                article_content = paragraphs[i+1]
                # Combine
                full_content = article_title + "\n\n" + article_content.strip()
                doc_id = f"english-{law_title.lower().replace(' ', '-')[:60]}-article-{i}"
                doc_id = "".join([c for c in doc_id if c.isalnum() or c in '-_'])
                documents.append({
                    "id": doc_id,
                    "law_title_en": law_title,
                    "law_title": "",
                    "article_no": article_title.split()[1] if " " in article_title else article_title,
                    "article_title": article_title,
                    "content_en": full_content,
                    "content": "",
                    "category": "law",
                    "language": "en",
                    "effective_date": "",
                    "source": "npc-english-official"
                })
    
    return documents

def main():
    # Add Labor Law
    from bs4 import BeautifulSoup
    import requests
    
    print("Processing Labor Law...")
    labor_url = "http://www.npc.gov.cn/zgrdw/englishnpc/Law/2007-12/12/content_1383754.htm"
    response = requests.get(labor_url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Extract content
    content = ""
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text and not text.startswith("Printer-Friendly") and not text.startswith("[E-Mail"):
            content += text + "\n\n"
    
    labor_docs = split_into_paragraphs(content, "Labor Law of the People's Republic of China")
    print(f"  Labor Law: {len(labor_docs)} articles")
    
    # Add Labor Contract Law
    print("\nProcessing Labor Contract Law...")
    contract_url = "http://www.npc.gov.cn/zgrdw/englishnpc/Law/2009-02/20/content_1471106.htm"
    response = requests.get(contract_url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    content = ""
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text and not text.startswith("Printer-Friendly") and not text.startswith("[E-Mail"):
            content += text + "\n\n"
    
    contract_docs = split_into_paragraphs(content, "Labor Contract Law of the People's Republic of China")
    print(f"  Labor Contract Law: {len(contract_docs)} articles")
    
    # Append to existing documents
    all_docs = []
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    all_docs.append(json.loads(line))
    
    all_docs.extend(labor_docs)
    all_docs.extend(contract_docs)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for doc in all_docs:
            json.dump(doc, f, ensure_ascii=False)
            f.write("\n")
    
    print(f"\nTotal documents now: {len(all_docs)}")
    print(f"Added {len(labor_docs) + len(contract_docs)} new articles from Labor Law & Labor Contract Law")

if __name__ == "__main__":
    main()
