#!/usr/bin/env python3
"""
Re-import split documents to Meilisearch
"""

import json
from meilisearch import Client

MEILI_HOST = "http://localhost:7700"
MEILI_MASTER_KEY = "masterKey"
INDEX_NAME = "legal_cn"

def main():
    client = Client(MEILI_HOST, MEILI_MASTER_KEY)
    index = client.index(INDEX_NAME)
    
    documents_file = "documents_split.jsonl"
    
    documents = []
    with open(documents_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                documents.append(json.loads(line))
    
    print(f"Importing {len(documents)} split English documents...")
    
    # Delete existing english documents first
    print("Deleting old English documents...")
    # We can't delete by filter easily, just add new ones - they have different IDs anyway
    
    response = index.add_documents(documents, primary_key="id")
    print(f"Import response: {response}")
    
    print("Done!")

if __name__ == "__main__":
    main()
