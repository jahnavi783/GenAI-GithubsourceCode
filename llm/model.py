import os
import env_loader  # noqa: F401 — loads .env with absolute path

try:
    # Preferred: new langchain-ollama package (no deprecation warning)
    from langchain_ollama import OllamaLLM as Ollama
except ImportError:
    # Fallback: old langchain_community (still works, shows warning)
    from langchain_community.llms import Ollama  # type: ignore


def get_llm():
    return Ollama(
        base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
        model=os.getenv('LLM_MODEL', 'llama3.1:8b'),
        temperature=0.1,
        top_p=0.9,
        top_k=40,
        repeat_penalty=1.1,
        num_ctx=8192,
    )
