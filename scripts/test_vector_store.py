from src.vector_store import vector_store

if __name__ == "__main__":
    print("--- 1. Ingesting Runbooks ---")
    count = vector_store.ingest_runbooks()
    print(f"Total documents in vector DB: {count}\n")

    print("--- 2. Testing Similarity Queries ---")
    test_queries = [
        "Database Connection Timeout on pool acquisition",
        "Redis cluster unreachable host=10.0.4.12",
        "Rate limiter triggered user_id=89231",
    ]

    for q in test_queries:
        print(f"nQuery: '{q}'")
        results = vector_store.query_runbooks(q, n_results=1)
        if results:
            match = results[0]
            print(f"Top Match: {match['metadata']['title']} (Source: {match['metadata']['source']})")
            print(f"Similarity Score (Disctance): {match['distance']:.4f}")
            print(f"Preview: {match['content'][:150].strip()}...")
        else:
            print("No matches found.")