import os
#from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from src.config import settings


class RunbookVectorStore:
    def __init__(self):
        # Create storage directory if it doesn't exist
        os.makedirs(settings.CHROMA_DB_DIR, exist_ok=True)

        # Initialize persistent ChromaDB client
        self.client = chromadb.PersistentClient(path=str(settings.CHROMA_DB_DIR))

        # Use default lightweight SentenceTransformer embeddings (runs locally on CPU)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="sre_runbooks",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def ingest_runbooks(self) -> int:
        """Reads all markdown files from settings.RUNBOOKS_DIR and populates ChromaDB."""
        runbooks_dir = settings.RUNBOOKS_DIR
        if not runbooks_dir.exists():
            print(f"[VectorStore] Warning: Directory {runbooks_dir} does not exist.")
            return 0

        documents = []
        metadatas = []
        ids = []

        for filepath in runbooks_dir.glob("*.md"):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            doc_id = filepath.stem # e.g., "db_connection_timeout"
            documents.append(content)
            metadatas.append({"source": filepath.name, "title": doc_id.replace("_", " ").title()})
            ids.append(doc_id)

        if documents:
            # Upsert updates existing records or inserts new ones
            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )
            print(f"[VectorStore] Successfully ingested {len(documents)} runbooks into ChromaDB.")

        return len(documents)

    def query_runbooks(self, query_text: str, n_results: int = 1) -> list[dict]:
        """Queries the vector database for the most relevant runbook context."""
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
        )

        matched_docs = []
        if results and results.get("documents"):
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                matched_docs.append({
                    "content": doc,
                    "metadata": meta,
                    "distance": dist, # Lower distance = higher similarity
                })

        return matched_docs



# Global instance
vector_store = RunbookVectorStore()