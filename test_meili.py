#!/usr/bin/env python3
import sys
import traceback
import config
from meilisearch import Client

try:
    print(f"Connecting to Meilisearch at {config.MEILISEARCH_HOST}...")
    client = Client(config.MEILISEARCH_HOST, config.MEILISEARCH_MASTER_KEY)
    
    # Test connection
    health = client.health()
    print(f"Health: {health}")
    
    # List indexes (v0.x API)
    indexes = client.get_indexes()
    print(f"\nIndexes:")
    if hasattr(indexes, "results"):
        for idx in indexes.results:
            print(f"  - {idx.uid}: {idx.primary_key}")
    else:
        print(f"  {indexes}")
    
    # Check if our index exists
    try:
        index_exists = client.get_index("legal_cn")
        print(f"\nIndex 'legal_cn' exists: YES (uid: {index_exists.uid})")
    except Exception as e:
        print(f"\nIndex 'legal_cn' does NOT exist: {e}")
        raise
    
    # Test search
    print(f"\nTesting search for '违法解除'...")
    result = client.index("legal_cn").search("违法解除", {"limit": 5})
    print(f"Search succeeded! {len(result['hits'])} hits found, total: {result['estimatedTotalHits']}")
    
    print("\n✅ All tests passed!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    traceback.print_exc()
