"""
Metrics specific to GenAI / LLM repositories.
Checks for evaluation frameworks, prompt hygiene, RAG components, safety measures.
"""

from analyzers.metrics.base_metrics import BaseMetrics

EVAL_FRAMEWORKS = ["ragas", "deepeval", "promptfoo", "trulens", "langsmith"]
RAG_COMPONENTS = ["chromadb", "pinecone", "faiss", "weaviate", "qdrant", "vector"]
SAFETY_MARKERS = ["guardrail", "moderation", "safety", "filter", "redact"]
PROMPT_MARKERS = ["prompt_template", "PromptTemplate", "system_prompt", "few_shot"]
OBSERVABILITY = ["langsmith", "mlflow", "wandb", "prometheus", "opentelemetry"]


class GenAIMetrics(BaseMetrics):

    def compute(self, file_tree: list[str], key_file_contents: dict[str, str]) -> list[dict]:
        metrics = []
        all_content = " ".join(key_file_contents.values()).lower()
        all_files_str = " ".join(file_tree).lower()

        # Evaluation framework
        has_eval = any(fw in all_content for fw in EVAL_FRAMEWORKS)
        metrics.append({
            "metric": "Evaluation Framework",
            "value": _find_first(EVAL_FRAMEWORKS, all_content) or "Not Found",
            "status": "✅ Good" if has_eval else "❌ Needs Attention",
        })

        # RAG / Vector DB
        has_rag = any(r in all_content for r in RAG_COMPONENTS)
        metrics.append({
            "metric": "RAG / Vector DB",
            "value": _find_first(RAG_COMPONENTS, all_content) or "Not Found",
            "status": "✅ Good" if has_rag else "ℹ️ Info",
        })

        # Prompt management
        has_prompts = any(p in all_content for p in PROMPT_MARKERS)
        prompt_files = [f for f in file_tree if "prompt" in f.lower()]
        metrics.append({
            "metric": "Prompt Management",
            "value": f"{len(prompt_files)} prompt file(s)" if prompt_files else ("Inline prompts" if has_prompts else "Not Found"),
            "status": "✅ Good" if (prompt_files or has_prompts) else "⚠️ Average",
        })

        # Safety / Guardrails
        has_safety = any(s in all_content for s in SAFETY_MARKERS)
        metrics.append({
            "metric": "Safety / Guardrails",
            "value": "Present" if has_safety else "Not Found",
            "status": "✅ Good" if has_safety else "⚠️ Average",
        })

        # Observability / Logging
        has_observability = any(o in all_content for o in OBSERVABILITY)
        metrics.append({
            "metric": "Observability",
            "value": _find_first(OBSERVABILITY, all_content) or "Basic logging only",
            "status": "✅ Good" if has_observability else "⚠️ Average",
        })

        # Test files
        test_files = [f for f in file_tree if "test" in f.lower() and f.endswith(".py")]
        metrics.append({
            "metric": "Test Coverage",
            "value": f"{len(test_files)} test file(s)",
            "status": self._status(len(test_files), 3, 1),
        })

        # .env.example present (good secret hygiene)
        has_env_example = any(".env.example" in f or ".env.sample" in f for f in file_tree)
        metrics.append({
            "metric": "Secret Hygiene (.env.example)",
            "value": "Present" if has_env_example else "Not Found",
            "status": "✅ Good" if has_env_example else "⚠️ Average",
        })

        return metrics


def _find_first(markers: list[str], content: str) -> str:
    for m in markers:
        if m in content:
            return m.title()
    return ""
