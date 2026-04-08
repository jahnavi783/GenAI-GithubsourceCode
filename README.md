# 🚀 GitHub Source Code Documentation Generator

---

## 📌 Overview

This project **automatically generates and maintains system design documentation** from any GitHub repository.

👉 No manual documentation  
👉 Always stays in sync with code  
👉 Works on every commit

---

## ✨ Key Features

| Feature                  | Description                                      |
| ------------------------ | ------------------------------------------------ |
| 🚀 First-time generation | Paste GitHub URL → full design document          |
| 🔄 Auto-update on commit | Webhook triggers → only changed sections updated |
| 📤 Push to repo          | `DOCUMENTATION.md` auto-pushed                   |
| 📄 Multi-format output   | `.docx` + Markdown                               |
| 🧠 Smart updates         | Section mapping → regenerate only impacted parts |

---

## 🛠️ Tech Stack

- ⚡ FastAPI (Backend)
- 🎨 Streamlit (UI Dashboard)
- 🧠 Ollama (LLM)
- 📦 ChromaDB (Vector DB)
- 🔗 GitHub Webhooks

---

## ⚙️ Setup

### 1️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

# Configure .env

# GitHub

GITHUB_APP_ID=123456
GITHUB_INSTALLATION_ID=112854524
GITHUB_OWNER=your-org-or-username
GITHUB_REPO=your-repo-name
GITHUB_PRIVATE_KEY_PATH=/path/to/private-key.pem
GITHUB_WEBHOOK_SECRET=your_secret

# Ollama

OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.1:8b
EMBED_MODEL=nomic-embed-text

# Storage

CHROMA_PATH=./chroma_db
DOCS_FOLDER=./generated_docs

# start ollama

ollama pull llama3.1:8b
ollama pull nomic-embed-text
ollama serve

# start backend

uvicorn main:app --host 0.0.0.0 --port 8001

# start Dashboard

streamlit run dashboard\app.py
