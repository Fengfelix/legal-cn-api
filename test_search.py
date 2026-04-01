#!/usr/bin/env python3
import sys
import traceback
import config
from meilisearch import Client
from fastapi import HTTPException

try:
    print("Testing the full search logic...")
    
    client = Client(config.MEILISEARCH_HOST, config.MEILISEARCH_MASTER_KEY)
    index = client.index("legal_cn")
    
    q = "违法解除"
    limit = 10
    
    print(f"Searching for '{q}', limit={limit}...")
    search_result = index.search(q, {"limit": limit})
    print(f"Got {len(search_result['hits'])} hits, total: {search_result['estimatedTotalHits']}")
    
    results = []
    for i, hit in enumerate(search_result["hits"]):
        print(f"\nHit {i+1}:")
        print(f"  law_title: {hit.get('law_title', 'NOT FOUND')}")
        print(f"  article_no: {hit.get('article_no', 'NOT FOUND')}")
        print(f"  article_title: {hit.get('article_title', 'NOT FOUND')}")
        print(f"  content: {hit.get('content', 'NOT FOUND')[:60]}...")
        print(f"  effective_date: {hit.get('effective_date', 'NOT FOUND')}")
        print(f"  category: {hit.get('category', 'NOT FOUND')}")
        print(f"  _score: {hit.get('_score', 'NOT FOUND')}")
    
    print("\n✅ Search logic works fine!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    traceback.print_exc()
