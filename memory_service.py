import os
import json
import chromadb
from sentence_transformers import SentenceTransformer

class EnhancedMemoryService:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        """Initialize embedding model and vector database."""
        # Embedding model
        self.embedding_model = SentenceTransformer(model_name)

        # Ensure memory directory exists
        os.makedirs("./chatbot_memory", exist_ok=True)

        # Chroma client with persistent storage
        self.client = chromadb.PersistentClient(path="./chatbot_memory")

        # Create collections for different memory types
        self.long_term_memory = self.client.get_or_create_collection(
            name="long_term_conversations",
            metadata={"hnsw:space": "cosine"}
        )

        self.recent_memory = self.client.get_or_create_collection(
            name="recent_conversations",
            metadata={"hnsw:space": "cosine"}
        )

    def store_message(self, message_id, content, metadata=None, is_recent=True):
        """Store a message in the appropriate memory collection."""
        # Generate embedding
        embedding = self.embedding_model.encode(content).tolist()

        # Choose collection based on recency
        collection = self.recent_memory if is_recent else self.long_term_memory

        # Serialize metadata to ensure it can be stored
        serialized_metadata = {}
        if metadata:
            for key, value in metadata.items():
                # Convert non-serializable types
                if not isinstance(value, (str, int, float, bool)):
                    serialized_metadata[key] = json.dumps(value)
                else:
                    serialized_metadata[key] = str(value)

        # Add to collection
        collection.add(
            ids=[str(message_id)],
            embeddings=[embedding],
            documents=[content],
            metadatas=[serialized_metadata or {}]
        )

    def retrieve_similar_messages(self, query, top_k=10, include_long_term=True):
        """Retrieve similar messages from both recent and long-term memory."""
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query).tolist()

        # Search recent memory
        recent_results = self.recent_memory.query(
            query_embeddings=[query_embedding],
            n_results=top_k // 2
        )

        # Search long-term memory if requested
        long_term_results = []
        if include_long_term:
            long_term_results = self.long_term_memory.query(
                query_embeddings=[query_embedding],
                n_results=top_k // 2
            )

        # Process and combine results
        def process_results(res_docs, res_metadata):
            processed = []
            for doc, meta in zip(res_docs[0], res_metadata[0]):
                # Deserialize metadata
                processed_meta = {}
                for key, value in meta.items():
                    try:
                        # Try to parse JSON, fallback to original value
                        processed_meta[key] = json.loads(value) if isinstance(value, str) else value
                    except (json.JSONDecodeError, TypeError):
                        processed_meta[key] = value
                processed.append((doc, processed_meta))
            return processed

        recent_processed = process_results(recent_results['documents'], recent_results['metadatas'])
        long_term_processed = process_results(long_term_results['documents'],
                                             long_term_results['metadatas']) if include_long_term else []

        # Combine and sort results
        return recent_processed + long_term_processed