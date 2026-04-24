"""
Vector Store using ChromaDB for RAG retrieval.
Stores and retrieves chunked documents with metadata.
"""

import logging
import hashlib
from typing import Optional
import chromadb
from chromadb.config import Settings
from src.config import CHROMA_DIR, EMBEDDING_MODEL, TOP_K_RESULTS

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB-based vector store for sentiment and deal data."""

    COLLECTION_NAME = "nse_sentiment"

    def __init__(self, persist_dir: str = None):
        persist = persist_dir or str(CHROMA_DIR)
        logger.info("Initializing ChromaDB at %s", persist)
        self.client = chromadb.PersistentClient(path=persist)
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Collection '%s' has %d documents", self.COLLECTION_NAME, self.collection.count())

    def add_documents(self, chunks: list[dict]) -> int:
        """
        Add document chunks to the vector store.
        Each chunk must have 'text' and 'metadata' keys.
        Returns number of documents added.
        """
        if not chunks:
            return 0

        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            text = chunk.get("text", "").strip()
            if not text:
                continue
            import uuid
            doc_id = hashlib.md5(text.encode()).hexdigest() + f"-{uuid.uuid4().hex[:8]}"
            meta = chunk.get("metadata", {})
            # ChromaDB requires metadata values to be str/int/float/bool
            clean_meta = {}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)
            ids.append(doc_id)
            documents.append(text)
            metadatas.append(clean_meta)

        if not documents:
            return 0

        # Upsert in batches (ChromaDB limit)
        batch_size = 100
        added = 0
        for i in range(0, len(documents), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_docs = documents[i:i+batch_size]
            batch_meta = metadatas[i:i+batch_size]
            try:
                self.collection.upsert(ids=batch_ids, documents=batch_docs, metadatas=batch_meta)
                added += len(batch_ids)
            except Exception as e:
                logger.error("Failed to upsert batch %d: %s", i//batch_size, e)

        logger.info("Added %d documents to vector store (total: %d)", added, self.collection.count())
        return added

    def query(self, query_text: str, top_k: int = None, symbol_filter: str = None) -> list[dict]:
        """
        Query the vector store for relevant documents.
        Returns list of dicts with 'text', 'metadata', and 'distance'.
        """
        k = top_k or TOP_K_RESULTS
        where_filter = None
        if symbol_filter:
            where_filter = {"symbol": symbol_filter.upper()}

        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=k,
                where=where_filter,
            )
        except Exception as e:
            logger.warning("Query with filter failed (%s), retrying without filter", e)
            results = self.collection.query(query_texts=[query_text], n_results=k)

        docs = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                dist = results["distances"][0][i] if results.get("distances") else 0
                docs.append({"text": doc, "metadata": meta, "distance": dist})

        logger.debug("Query returned %d results for: %s", len(docs), query_text[:60])
        return docs

    def clear(self):
        """Clear all documents from the collection."""
        self.client.delete_collection(self.COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Cleared vector store")

    def stats(self) -> dict:
        """Get statistics about the vector store."""
        count = self.collection.count()
        return {"total_documents": count, "collection": self.COLLECTION_NAME}
