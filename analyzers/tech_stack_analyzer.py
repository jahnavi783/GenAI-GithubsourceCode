"""
Analyzes the tech stack from the repo's key files.
Extracts: languages (with %), frameworks, databases, tools, and infra.
"""

import re
import os


PACKAGE_CATEGORIES = {
    "fastapi": ("Framework", "FastAPI"),
    "flask": ("Framework", "Flask"),
    "django": ("Framework", "Django"),
    "express": ("Framework", "Express.js"),
    "nestjs": ("Framework", "NestJS"),
    "langchain": ("GenAI", "LangChain"),
    "langchain_community": ("GenAI", "LangChain Community"),
    "langchain_core": ("GenAI", "LangChain Core"),
    "openai": ("GenAI", "OpenAI SDK"),
    "anthropic": ("GenAI", "Anthropic SDK"),
    "ollama": ("GenAI", "Ollama"),
    "transformers": ("GenAI", "HuggingFace Transformers"),
    "sentence-transformers": ("GenAI", "Sentence Transformers"),
    "chromadb": ("Vector DB", "ChromaDB"),
    "pinecone": ("Vector DB", "Pinecone"),
    "faiss": ("Vector DB", "FAISS"),
    "ragas": ("GenAI Eval", "RAGAS"),
    "llama-index": ("GenAI", "LlamaIndex"),
    "litellm": ("GenAI", "LiteLLM"),
    "pandas": ("Data", "Pandas"),
    "numpy": ("Data", "NumPy"),
    "scikit-learn": ("ML", "Scikit-learn"),
    "torch": ("ML", "PyTorch"),
    "tensorflow": ("ML", "TensorFlow"),
    "xgboost": ("ML", "XGBoost"),
    "sqlalchemy": ("Database", "SQLAlchemy"),
    "pymongo": ("Database", "MongoDB"),
    "redis": ("Database", "Redis"),
    "psycopg2": ("Database", "PostgreSQL"),
    "pytest": ("Testing", "Pytest"),
    "jest": ("Testing", "Jest"),
    "uvicorn": ("Server", "Uvicorn"),
    "gunicorn": ("Server", "Gunicorn"),
    "docker": ("Infra", "Docker"),
    "streamlit": ("UI", "Streamlit"),
    "gradio": ("UI", "Gradio"),
    "pygithub": ("Integration", "PyGitHub"),
    "requests": ("HTTP", "Requests"),
}

IGNORE_DIRS = {
    "node_modules", ".git", "build", "dist", ".dart_tool",
    ".pub-cache", "__pycache__", ".gradle", "Pods", ".cache",
}


def analyze_tech_stack(file_tree: list[str], key_file_contents: dict[str, str]) -> dict:
    languages = _detect_languages(file_tree)
    detected = _detect_packages(key_file_contents)
    frameworks = [{"name": label, "category": category} for category, label in detected]

    infra = []
    if any("Dockerfile" in f for f in file_tree):
        infra.append("Docker")
    if any("docker-compose" in f for f in file_tree):
        infra.append("Docker Compose")
    if any(".github/workflows" in f for f in file_tree):
        infra.append("GitHub Actions")

    return {"languages": languages, "frameworks_and_libs": frameworks, "infra": infra}


def _detect_languages(file_tree: list[str]) -> list[str]:
    ext_language_map = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".jsx": "JavaScript (React)", ".tsx": "TypeScript (React)",
        ".java": "Java", ".go": "Go", ".rs": "Rust", ".cs": "C#",
        ".cpp": "C++", ".c": "C", ".rb": "Ruby", ".php": "PHP",
        ".st": "Structured Text (PLC)", ".il": "Instruction List (PLC)",
        ".l5x": "Rockwell L5X (PLC)", ".dart": "Dart", ".swift": "Swift",
        ".kt": "Kotlin", ".kts": "Kotlin", ".html": "HTML", ".css": "CSS",
        ".scss": "SCSS", ".sh": "Shell", ".yaml": "YAML", ".yml": "YAML",
        ".json": "JSON", ".xml": "XML", ".cmake": "CMake",
        ".r": "R", ".ex": "Elixir", ".exs": "Elixir",
    }

    filtered = [f for f in file_tree if not any(ig in f for ig in IGNORE_DIRS)]

    counts = {}
    for filepath in filtered:
        _, ext = os.path.splitext(filepath)
        ext = ext.lower()
        if ext in ext_language_map:
            lang = ext_language_map[ext]
            counts[lang] = counts.get(lang, 0) + 1

    if not counts:
        return []

    total = sum(counts.values())
    sorted_langs = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [f"{lang}  {round((count / total) * 100, 1)}%" for lang, count in sorted_langs]


def _detect_packages(key_file_contents: dict[str, str]) -> list[tuple[str, str]]:
    found = []
    seen = set()
    for filepath, content in key_file_contents.items():
        filename = filepath.lower().split("/")[-1]
        if filename == "requirements.txt":
            packages = _parse_requirements(content)
        elif filename == "package.json":
            packages = _parse_package_json(content)
        elif filename in ["pyproject.toml", "setup.py", "pipfile"]:
            packages = _parse_requirements(content)
        else:
            continue
        for pkg in packages:
            pkg_lower = pkg.lower().replace("-", "_").replace(" ", "_")
            for key, (category, label) in PACKAGE_CATEGORIES.items():
                key_normalized = key.lower().replace("-", "_")
                if key_normalized in pkg_lower and label not in seen:
                    found.append((category, label))
                    seen.add(label)
    return found


def _parse_requirements(content: str) -> list[str]:
    packages = []
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            pkg = re.split(r"[>=<!;\[]", line)[0].strip()
            if pkg:
                packages.append(pkg)
    return packages


def _parse_package_json(content: str) -> list[str]:
    import json
    try:
        data = json.loads(content)
        deps = {}
        deps.update(data.get("dependencies", {}))
        deps.update(data.get("devDependencies", {}))
        return list(deps.keys())
    except Exception:
        return []
