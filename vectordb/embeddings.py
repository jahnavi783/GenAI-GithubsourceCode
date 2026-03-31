import os
import env_loader  # noqa: F401 — loads .env with absolute path
from chromadb.utils import embedding_functions


def get_embedding_fn():
    return embedding_functions.OllamaEmbeddingFunction(
        url=f"{os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}/api/embeddings",
        model_name=os.getenv('EMBED_MODEL', 'nomic-embed-text')
    )