"""
Detects the type of repository based on its file tree and key file contents.

Supported repo types:
  - genai    : LangChain, OpenAI, HuggingFace, Ollama, RAG-based projects
  - python   : General Python projects (no GenAI markers)
  - node     : Node.js / JavaScript / TypeScript projects
  - flutter  : Dart / Flutter projects
  - swift    : Swift / iOS / macOS projects
  - kotlin   : Kotlin / Android projects
  - plc      : PLC / Industrial Automation (L5X, ST, IL files)
  - mixed    : Combination of multiple types
  - unknown  : Cannot determine
"""

GENAI_MARKERS = [
    "langchain", "openai", "anthropic", "ollama", "transformers",
    "huggingface", "llama", "chromadb", "pinecone", "faiss",
    "sentence-transformers", "ragas", "llmchain", "langchain_community",
    "langchain_core", "tiktoken", "litellm", "groq", "mistral",
]

PLC_EXTENSIONS = [".l5x", ".L5X", ".st", ".il", ".fbd", ".ld", ".acd"]
PLC_FILENAMES = ["ladder.xml", "plc_project.xml"]


def detect_repo_type(file_tree: list[str], key_file_contents: dict[str, str]) -> str:
    """
    Returns the detected repo type as a string.
    Priority order: plc > flutter > swift > kotlin > genai > node > python > unknown
    """
    all_content = " ".join(key_file_contents.values()).lower()

    # PLC first (very specific extensions)
    for filepath in file_tree:
        ext = _get_extension(filepath)
        filename = filepath.lower().split("/")[-1]
        if ext in PLC_EXTENSIONS or filename in PLC_FILENAMES:
            return "plc"

    # Flutter / Dart
    has_dart_files = any(_get_extension(f) == ".dart" for f in file_tree)
    has_pubspec = any("pubspec.yaml" in f or "pubspec.yml" in f for f in file_tree)
    if has_dart_files or has_pubspec:
        return "flutter"

    # Swift
    has_swift_files = any(_get_extension(f) == ".swift" for f in file_tree)
    if has_swift_files:
        return "swift"

    # Kotlin
    has_kotlin_files = any(_get_extension(f) in [".kt", ".kts"] for f in file_tree)
    if has_kotlin_files:
        return "kotlin"

    # Python / GenAI
    has_python_files = any(_get_extension(f) == ".py" for f in file_tree)
    has_package_json = any("package.json" in f for f in file_tree)
    has_js_ts_files = any(_get_extension(f) in [".js", ".ts", ".jsx", ".tsx"] for f in file_tree)
    is_genai = any(marker in all_content for marker in GENAI_MARKERS)

    if is_genai and has_python_files:
        return "genai"

    if has_python_files and has_package_json:
        return "mixed"

    if has_python_files:
        return "python"

    if has_package_json or has_js_ts_files:
        return "node"

    return "unknown"


def _get_extension(filepath: str) -> str:
    _, ext = __import__("os.path", fromlist=["splitext"]).splitext(filepath)
    return ext
