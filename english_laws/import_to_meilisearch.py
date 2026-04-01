#!/usr/bin/env python3
"""
Import English laws to Meilisearch index
"""

import json
import sys
import os
from meilisearch import Client

MEILI_HOST = "http://localhost:7700"
MEILI_MASTER_KEY = "masterKey"
INDEX_NAME = "legal_cn"

def main():
    client = Client(MEILI_HOST, MEILI_MASTER_KEY)
    index = client.index(INDEX_NAME)
    
    documents_file = "documents.jsonl"
    
    documents = []
    with open(documents_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                documents.append(json.loads(line))
    
    print(f"Importing {len(documents)} English documents to Meilisearch...")
    
    response = index.add_documents(documents, primary_key="id")
    print(f"Import response: {response}")
    
    print("Done! Check Meilisearch for update.")

if __name__ == "__main__":
    main()
