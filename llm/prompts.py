# from langchain_core.prompts import PromptTemplate

# # ── REPO DESCRIPTION ──────────────────────────────────────────────────────────
# REPO_DESCRIPTION_TEMPLATE = PromptTemplate(
#     input_variables=['repo_name', 'file_tree', 'key_files_content'],
#     template='''
# You are a senior software architect. Based on the repository structure and key file contents below,
# write a professional description of what this codebase does.

# REPOSITORY: {repo_name}

# FILE TREE:
# {file_tree}

# KEY FILE CONTENTS:
# {key_files_content}

# CRITICAL LANGUAGE RULE:
# - Detect the programming language automatically from file extensions in the FILE TREE.
# - DO NOT assume Python by default.
# - If you see .dart files -> it is a Dart/Flutter project.
# - If you see .swift files -> it is a Swift/iOS project.
# - If you see .kt files -> it is a Kotlin/Android project.
# - If you see .tsx/.jsx files -> it is a React project.
# - Always use the correct markdown code block language tag (dart, swift, kotlin, tsx, js, cpp, etc.)
# - All explanations must come DIRECTLY from the repository files, structure, and naming conventions.
# - Do NOT use hardcoded or generic examples. Every reference must be real from this repo.
# - Understand the domain context from the code. For example:
#   * If the repo is about Field Service Management (FSM) -> describe concepts like service engineers, work orders, machine details, service history.
#   * If the repo is a chatbot -> describe the conversation flow, intents, responses.
#   * Always derive the domain from actual file/folder names and code content.

# OUTPUT FORMAT RULES — STRICTLY ENFORCED:
# - Every section MUST use bullet points. NO plain paragraphs anywhere.
# - Each bullet point MUST start with a bold label: **Label:** followed by the content.
# - Each bullet point is ONE standalone concept — do NOT merge multiple ideas into one bullet.
# - Keep each bullet concise: 1–2 sentences maximum per bullet.
# - Do NOT use tables. Do NOT write prose paragraphs.
# - Separate each section with its ## heading.

# Write EXACTLY the sections below.

# ## Overview
# Write EXACTLY ONE bullet point — a single concise sentence describing the purpose of this application.
# No bold label on this one. Just one clean sentence: "A [language] + [framework] [domain] application that [core purpose]."

# ## Description
# Write 3–5 bullet points. Each bullet uses a bold label. Cover:
# - **Core Product:** what the app manages or delivers
# - **Problem Solved:** the inefficiency or gap it eliminates
# - **Key Features:** the 2–3 most important capabilities (list them inline, comma-separated)
# - **Entry Point:** the main file that initialises the app (use `code` formatting for filenames)
# All content must be derived from actual files — no generic statements.

# ## What the Codebase Does
# Write 5–7 bullet points describing the ACTUAL end-to-end flow of this specific application.
# Each bullet MUST have a bold label and reference a real file, component, route, or domain concept.
# Use labels like: **Entry Point:**, **Core Feature – [name]:**, **User Flow:**, **Data Layer:**, **Output:**
# Every bullet must be about something REAL in the code. Use domain-specific terms from the project.

# ## System Overview
# Write 4–6 bullet points, one per major component.
# Each bullet format: **`folder/file`** — one sentence on what it actually does in this codebase.
# Cover: application purpose, key modules, core workflows, important files and their roles.

# # ## Codebase Structure
# # Write one bullet per top-level folder. Format: **`folder/`** — one sentence on its role.

# # Then produce a Mermaid diagram. Follow these STRICT RULES — any violation causes a parse error in GitHub:
# # - Use flowchart TD only.
# # - Node IDs must be simple letters only: A, B, C, D, E etc. NEVER use slashes, dots, or special characters as IDs.
# # - Node labels go inside ([label]) — plain text with slashes/dots allowed inside the label.
# # - Arrows: use ONLY --> with no labels. NEVER use -->|label|> or any arrow label syntax.
# # - NEVER use: subgraph, style, classDef, [color:...], or **bold** inside node labels.
# # - Max 12 nodes total. Every node must connect with -->.
# # - Wrap in a mermaid code fence. No text before or after the fence.
# # SYNTAX REFERENCE (structure only — replace ALL labels with real paths from this repo's FILE TREE):
# # ```mermaid
# # flowchart TD
# # A([entry-point-file]) --> B([top-level-folder/])
# # B --> C([subfolder1/])
# # B --> D([subfolder2/])
# # C --> E([key-file-or-folder])
# # D --> F([key-file-or-folder])
# # ```

# # After the mermaid block, write EXACTLY 2 sentences (no bullet points) describing the overall
# # module structure and how components relate to each other.
# # '''
# )


# # ── IMPACT ANALYSIS ───────────────────────────────────────────────────────────
# IMPACT_ANALYSIS_TEMPLATE = PromptTemplate(
#     input_variables=['repo_overview', 'files_changed', 'diff'],
#     template='''
# You are a senior developer performing impact analysis for a code change.

# REPO CONTEXT:
# {repo_overview}

# FILES CHANGED IN THIS COMMIT:
# {files_changed}

# GIT DIFF:
# {diff}

# LANGUAGE RULE:
# - Detect the programming language from the file extensions in the diff (e.g. .dart, .swift, .tsx, .py).
# - Do NOT assume Python. Use the correct language name in all descriptions.
# - Use domain-specific terminology from the project context when describing changes.

# Produce ONLY a markdown table with these exact columns:
# | Area Impacted | Type of Impact | Severity | Description | Action Required |

# Rules:
# - One row per changed file.
# - Area Impacted: which module/component/feature is affected.
# - Type of Impact: Functional / Performance / Security / UI / Data.
# - Severity: Low / Medium / High only.
# - Description: one short sentence about what changes.
# - Action Required: what needs to be done next, or "None".
# - Tables must be compact — use short values, avoid long sentences in cells.
# - Always produce EXACTLY 5 columns per row, no more, no less.
# - No text before or after the table. No sub-headings.
# '''
# )


# # ── COMMIT DOCUMENTATION ──────────────────────────────────────────────────────
# DOC_TEMPLATE = PromptTemplate(
#     input_variables=[
#         'author', 'branch', 'sha',
#         'timestamp', 'files', 'context', 'diff'
#     ],
#     template='''
# You are a senior developer writing a commit change documentation report.
# Analyse the git diff below and document ONLY what is new or changed.
# Do not invent anything. Only use what exists in the diff.

# LANGUAGE RULE:
# - Detect the programming language from the file extensions in the diff (e.g. .dart, .swift, .tsx, .py).
# - Do NOT assume Python. Use the correct language name in all descriptions.
# - Use domain-specific terminology from the project context when describing changes.
# - Tables must be compact and screen-friendly. Use <br> to break long content within a cell.

# COMMIT DETAILS:
# Author    : {author}
# Branch    : {branch}
# SHA       : {sha}
# Timestamp : {timestamp}
# Files     : {files}

# REFERENCE FROM SIMILAR PAST COMMITS:
# {context}

# GIT DIFF:
# {diff}

# Produce EXACTLY ONE markdown table with these columns (no other text, no headings before or after):

# | File Changed | Change Type | Description | Lines Added | Lines Removed | Risk Level |

# Rules:
# - One row per changed file.
# - File Changed: the filename or path.
# - Change Type: Added | Modified | Deleted
# - Description: one short phrase summarising what changed in this file.
# - Lines Added: approximate number of lines added, or "0".
# - Lines Removed: approximate number of lines removed, or "0".
# - Risk Level: Low / Medium / High only.
# - Use <br> to separate multiple items within a single cell.
# - Always produce EXACTLY 6 columns per row, no more, no less.
# - No text before or after the table.
# '''
# )


# # ── ARCHITECTURE ──────────────────────────────────────────────────────────────
# ARCHITECTURE_TEMPLATE = PromptTemplate(
#     input_variables=['repo_name', 'file_tree', 'key_files_content'],
#     template='''
# You are a senior software architect. Write a detailed Architecture section for the repository below.

# REPOSITORY: {repo_name}

# FILE TREE:
# {file_tree}

# KEY FILE CONTENTS:
# {key_files_content}

# OUTPUT FORMAT RULES — STRICTLY ENFORCED:
# - Every subsection MUST use bullet points. NO prose paragraphs.
# - Each bullet point MUST start with a bold label: **Label:** followed by one concise sentence.
# - One concept per bullet. Do NOT merge multiple ideas into a single bullet.
# - Keep each bullet to 1–2 sentences maximum.
# - Use `code` formatting for all file and folder names.

# Write the Architecture section using ## and ### headings with bullet points only.

# ## Architecture

# ## Codebase Structure
# Write one bullet per top-level folder. Format: **`folder/`** — one sentence on its role.

# Then produce a Mermaid diagram. Follow these STRICT RULES — any violation causes a parse error in GitHub:
# - Use flowchart TD only.
# - Node IDs must be simple letters only: A, B, C, D, E etc. NEVER use slashes, dots, or special characters as IDs.
# - Node labels go inside ([label]) — plain text with slashes/dots allowed inside the label.
# - Arrows: use ONLY --> with no labels. NEVER use -->|label|> or any arrow label syntax.
# - NEVER use: subgraph, style, classDef, [color:...], or **bold** inside node labels.
# - Max 12 nodes total. Every node must connect with -->.
# - Wrap in a mermaid code fence. No text before or after the fence.
# SYNTAX REFERENCE (structure only — replace ALL labels with real paths from this repo's FILE TREE):
# ```mermaid
# flowchart TD
# A([entry-point-file]) --> B([top-level-folder/])
# B --> C([subfolder1/])
# B --> D([subfolder2/])
# C --> E([key-file-or-folder])
# D --> F([key-file-or-folder])
# ```

# After the mermaid block, write EXACTLY 2 sentences (no bullet points) describing the overall
# module structure and how components relate to each other.


# ### High-Level Design
# - **Pattern:** Name the architectural pattern used (e.g., Feature-first, MVC, Clean Architecture, BLoC, microservices).
# - **Structure:** Describe how the top-level folders reflect this pattern, referencing real folder names.
# - **State Management:** Name the state management approach if applicable (e.g., BLoC, Redux, Provider, MobX).

# ### Key Components
# One bullet per major module or folder. Format: **`folder/`** — one sentence on its role.
# Reference only real folder/file names from the FILE TREE.

# ### Component Interactions
# - **Request Flow:** Describe how a user action flows through the layers (e.g., UI → BLoC → service → API).
# - **Data Direction:** Describe how responses/data flow back to the UI.
# - **Shared Services:** Name any shared/core modules that multiple features depend on.

# ### Entry Points
# - **Main Entry:** The first file executed at startup (use `code` format for filename).
# - **App Init:** The file that initialises the app framework/widget tree.
# - **Routing:** The file or module responsible for navigation/routing.

# Use only what exists in the repository. No generic filler. Reference real file names.
# '''
# )


# # ── API ENDPOINTS ─────────────────────────────────────────────────────────────
# API_SECTION_TEMPLATE = PromptTemplate(
#     input_variables=['repo_name', 'api_files_content'],
#     template='''
# You are a senior developer. Document the API endpoints for this repository.

# REPOSITORY: {repo_name}

# API / ROUTE FILE CONTENTS:
# {api_files_content}

# OUTPUT FORMAT RULES — STRICTLY ENFORCED:
# - Every endpoint MUST be its own bullet point. NO prose paragraphs.
# - Each bullet format: **METHOD /path** — one sentence describing what it does.
# - One endpoint per bullet. Do NOT group multiple endpoints into a single bullet.
# - Use ### subheadings to group endpoints by resource (e.g., ### Work Orders, ### Engineers).
# - Keep each bullet concise: method, path, and a single short description.

# ## API Information

# Group endpoints by resource using ### subheadings.
# For each endpoint, write one bullet:
# - **GET /path** — short description of what it returns
# - **POST /path** — short description of what it creates or updates
# - **PUT /path** — short description of what it modifies
# - **DELETE /path** — short description of what it removes

# If no REST API is found, document the main public function signatures as bullets instead:
# - **`functionName(params)`** — what it does and what it returns

# Use only what exists in the files. Do NOT invent endpoints or functions.
# '''
# )


# # ── DATA FLOW ─────────────────────────────────────────────────────────────────
# DATA_FLOW_TEMPLATE = PromptTemplate(
#     input_variables=['repo_name', 'data_files_content'],
#     template='''
# You are a senior data engineer. Document the data flow for this repository.

# REPOSITORY: {repo_name}

# MODEL / SCHEMA / DATABASE FILE CONTENTS:
# {data_files_content}

# OUTPUT FORMAT RULES — STRICTLY ENFORCED:
# - Every subsection MUST use bullet points. NO prose paragraphs.
# - Each bullet MUST start with a bold label: **Label:** followed by one concise sentence.
# - One concept per bullet. Do NOT merge multiple ideas into a single bullet.
# - Keep each bullet to 1–2 sentences maximum.
# - Use `code` formatting for all model names, field names, and file names.

# ## Data Flow

# ### Data Models
# One bullet per model/entity found in the code. Format:
# - **`ModelName`:** List 3–5 key fields inline (e.g., id, status, assignedTo). One sentence on its purpose.

# ### Data Flow Description
# Write a numbered step-by-step flow showing how data moves through the system.
# Format as a numbered list, not bullets:
# 1. **UI Layer:** How the user triggers data retrieval or mutation.
# 2. **State/Logic Layer:** Which BLoC event, action, or controller handles it.
# 3. **Service Layer:** Which service or use case processes the request.
# 4. **API/Network Layer:** The API call made (method + endpoint).
# 5. **Repository Layer:** How the response is parsed and returned.
# 6. **State Update:** How the UI is updated with the new data.

# ### Storage
# One bullet per storage mechanism:
# - **`StorageType`:** Name the technology (e.g., SQLite, PostgreSQL, REST API, SharedPreferences) and what it stores.

# Use only what exists in the files. Do NOT invent models or storage systems.
# '''
# )
from langchain_core.prompts import PromptTemplate

# ── REPO DESCRIPTION ──────────────────────────────────────────────────────────
REPO_DESCRIPTION_TEMPLATE = PromptTemplate(
    input_variables=['repo_name', 'file_tree', 'key_files_content'],
    template='''
You are a senior software architect. Based on the repository structure and key file contents below,
write a professional description of what this codebase does.

REPOSITORY: {repo_name}

FILE TREE:
{file_tree}

KEY FILE CONTENTS:
{key_files_content}

CRITICAL LANGUAGE RULE:
- Detect the programming language automatically from file extensions in the FILE TREE.
- DO NOT assume Python by default.
- If you see .dart files -> it is a Dart/Flutter project.
- If you see .swift files -> it is a Swift/iOS project.
- If you see .kt files -> it is a Kotlin/Android project.
- If you see .tsx/.jsx files -> it is a React project.
- Always use the correct markdown code block language tag (dart, swift, kotlin, tsx, js, cpp, etc.)
- All explanations must come DIRECTLY from the repository files, structure, and naming conventions.
- Do NOT use hardcoded or generic examples. Every reference must be real from this repo.
- Understand the domain context from the code. For example:
  * If the repo is about Field Service Management (FSM) -> describe concepts like service engineers, work orders, machine details, service history.
  * If the repo is a chatbot -> describe the conversation flow, intents, responses.
  * Always derive the domain from actual file/folder names and code content.

OUTPUT FORMAT RULES — STRICTLY ENFORCED:
- Every section MUST use bullet points. NO plain paragraphs anywhere.
- Each bullet point MUST start with a bold label: **Label:** followed by the content.
- Each bullet point is ONE standalone concept — do NOT merge multiple ideas into one bullet.
- Keep each bullet concise: 1–2 sentences maximum per bullet.
- Do NOT use tables. Do NOT write prose paragraphs.
- Separate each section with its ## heading.
- DO NOT include any Mermaid diagram or Codebase Structure section here.

Write EXACTLY the sections below.

## Overview
Write EXACTLY ONE bullet point — a single concise sentence describing the purpose of this application.
No bold label on this one. Just one clean sentence: "A [language] + [framework] [domain] application that [core purpose]."

## Description
Write 3–5 bullet points. Each bullet uses a bold label. Cover:
- **Core Product:** what the app manages or delivers
- **Problem Solved:** the inefficiency or gap it eliminates
- **Key Features:** the 2–3 most important capabilities (list them inline, comma-separated)
- **Entry Point:** the main file that initialises the app (use `code` formatting for filenames)
All content must be derived from actual files — no generic statements.

## What the Codebase Does
Write 5–7 bullet points describing the ACTUAL end-to-end flow of this specific application.
Each bullet MUST have a bold label and reference a real file, component, route, or domain concept.
Use labels like: **Entry Point:**, **Core Feature – [name]:**, **User Flow:**, **Data Layer:**, **Output:**
Every bullet must be about something REAL in the code. Use domain-specific terms from the project.

## System Overview
Write 4–6 bullet points, one per major component.
Each bullet format: **`folder/file`** — one sentence on what it actually does in this codebase.
Cover: application purpose, key modules, core workflows, important files and their roles.
'''
)


# ── IMPACT ANALYSIS ───────────────────────────────────────────────────────────
IMPACT_ANALYSIS_TEMPLATE = PromptTemplate(
    input_variables=['repo_overview', 'files_changed', 'diff'],
    template='''
You are a senior developer performing impact analysis for a code change.

REPO CONTEXT:
{repo_overview}

FILES CHANGED IN THIS COMMIT:
{files_changed}

GIT DIFF:
{diff}

LANGUAGE RULE:
- Detect the programming language from the file extensions in the diff (e.g. .dart, .swift, .tsx, .py).
- Do NOT assume Python. Use the correct language name in all descriptions.
- Use domain-specific terminology from the project context when describing changes.

Produce ONLY a markdown table with these exact columns:
| Area Impacted | Type of Impact | Severity | Description | Action Required |

Rules:
- One row per changed file.
- Area Impacted: which module/component/feature is affected.
- Type of Impact: Functional / Performance / Security / UI / Data.
- Severity: Low / Medium / High only.
- Description: one short sentence about what changes.
- Action Required: what needs to be done next, or "None".
- Tables must be compact — use short values, avoid long sentences in cells.
- Always produce EXACTLY 5 columns per row, no more, no less.
- No text before or after the table. No sub-headings.
'''
)


# ── COMMIT DOCUMENTATION ──────────────────────────────────────────────────────
DOC_TEMPLATE = PromptTemplate(
    input_variables=[
        'author', 'branch', 'sha',
        'timestamp', 'files', 'context', 'diff'
    ],
    template='''
You are a senior developer writing a commit change documentation report.
Analyse the git diff below and document ONLY what is new or changed.
Do not invent anything. Only use what exists in the diff.

LANGUAGE RULE:
- Detect the programming language from the file extensions in the diff (e.g. .dart, .swift, .tsx, .py).
- Do NOT assume Python. Use the correct language name in all descriptions.
- Use domain-specific terminology from the project context when describing changes.
- Tables must be compact and screen-friendly. Use <br> to break long content within a cell.

COMMIT DETAILS:
Author    : {author}
Branch    : {branch}
SHA       : {sha}
Timestamp : {timestamp}
Files     : {files}

REFERENCE FROM SIMILAR PAST COMMITS:
{context}

GIT DIFF:
{diff}

Produce EXACTLY ONE markdown table with these columns (no other text, no headings before or after):

| File Changed | Change Type | Description | Lines Added | Lines Removed | Risk Level |

Rules:
- One row per changed file.
- File Changed: the filename or path.
- Change Type: Added | Modified | Deleted
- Description: one short phrase summarising what changed in this file.
- Lines Added: approximate number of lines added, or "0".
- Lines Removed: approximate number of lines removed, or "0".
- Risk Level: Low / Medium / High only.
- Use <br> to separate multiple items within a single cell.
- Always produce EXACTLY 6 columns per row, no more, no less.
- No text before or after the table.
'''
)


# ── ARCHITECTURE ──────────────────────────────────────────────────────────────
ARCHITECTURE_TEMPLATE = PromptTemplate(
    input_variables=['repo_name', 'file_tree', 'key_files_content'],
    template='''
You are a senior software architect. Write a detailed Architecture section for the repository below.

REPOSITORY: {repo_name}

FILE TREE:
{file_tree}

KEY FILE CONTENTS:
{key_files_content}

OUTPUT FORMAT RULES — STRICTLY ENFORCED:
- Every subsection MUST use bullet points. NO prose paragraphs.
- Each bullet point MUST start with a bold label: **Label:** followed by one concise sentence.
- One concept per bullet. Do NOT merge multiple ideas into a single bullet.
- Keep each bullet to 1–2 sentences maximum.
- Use `code` formatting for all file and folder names.

Write the Architecture section using ## and ### headings with bullet points only.

## Architecture

## Codebase Structure
Write one bullet per top-level folder using ONLY real folder names visible in the FILE TREE above.
Format: **`folder/`** — one sentence on its actual role in this codebase.

## Architecture Diagram
IMPORTANT: Produce a Mermaid flowchart using ONLY real file and folder names from the FILE TREE above.

Rules — strictly enforced:
- First line: ```mermaid
- Second line: flowchart TD
- Node IDs: single capital letters only (A, B, C, D ...). NEVER use slashes or dots as IDs.
- Node labels: ([real/path]) — must be exact file or folder names taken from the FILE TREE.
- Arrows: --> only, no labels, no pipes.
- No subgraph, style, classDef, or bold text inside labels.
- 6 to 10 nodes. Every node must connect with -->.
- Last line: ```
- NO placeholder names. EVERY label must exist in the FILE TREE provided above.
- DO NOT use names like "entry-point-file", "top-level-folder", "subfolder1" — these are forbidden.

After the closing ``` write EXACTLY 2 plain sentences (no bullets) describing how the real
modules in this specific repo connect to each other.

### High-Level Design
- **Pattern:** Name the architectural pattern used (e.g., Feature-first, MVC, Clean Architecture, BLoC, microservices).
- **Structure:** Describe how the top-level folders reflect this pattern, referencing real folder names.
- **State Management:** Name the state management approach if applicable (e.g., BLoC, Redux, Provider, MobX).

### Key Components
One bullet per major module or folder. Format: **`folder/`** — one sentence on its role.
Reference only real folder/file names from the FILE TREE.

### Component Interactions
- **Request Flow:** Describe how a user action flows through the layers (e.g., UI → BLoC → service → API).
- **Data Direction:** Describe how responses/data flow back to the UI.
- **Shared Services:** Name any shared/core modules that multiple features depend on.

### Entry Points
- **Main Entry:** The first file executed at startup (use `code` format for filename).
- **App Init:** The file that initialises the app framework/widget tree.
- **Routing:** The file or module responsible for navigation/routing.

Use only what exists in the repository. No generic filler. Reference real file names.
'''
)


# ── API ENDPOINTS ─────────────────────────────────────────────────────────────
API_SECTION_TEMPLATE = PromptTemplate(
    input_variables=['repo_name', 'api_files_content'],
    template='''
You are a senior developer. Document the API endpoints for this repository.

REPOSITORY: {repo_name}

API / ROUTE FILE CONTENTS:
{api_files_content}

OUTPUT FORMAT RULES — STRICTLY ENFORCED:
- Every endpoint MUST be its own bullet point. NO prose paragraphs.
- Each bullet format: **METHOD /path** — one sentence describing what it does.
- One endpoint per bullet. Do NOT group multiple endpoints into a single bullet.
- Use ### subheadings to group endpoints by resource (e.g., ### Work Orders, ### Engineers).
- Keep each bullet concise: method, path, and a single short description.

## API Information

Group endpoints by resource using ### subheadings.
For each endpoint, write one bullet:
- **GET /path** — short description of what it returns
- **POST /path** — short description of what it creates or updates
- **PUT /path** — short description of what it modifies
- **DELETE /path** — short description of what it removes

If no REST API is found, document the main public function signatures as bullets instead:
- **`functionName(params)`** — what it does and what it returns

Use only what exists in the files. Do NOT invent endpoints or functions.
'''
)


# ── DATA FLOW ─────────────────────────────────────────────────────────────────
DATA_FLOW_TEMPLATE = PromptTemplate(
    input_variables=['repo_name', 'data_files_content'],
    template='''
You are a senior data engineer. Document the data flow for this repository.

REPOSITORY: {repo_name}

MODEL / SCHEMA / DATABASE FILE CONTENTS:
{data_files_content}

OUTPUT FORMAT RULES — STRICTLY ENFORCED:
- Every subsection MUST use bullet points. NO prose paragraphs.
- Each bullet MUST start with a bold label: **Label:** followed by one concise sentence.
- One concept per bullet. Do NOT merge multiple ideas into a single bullet.
- Keep each bullet to 1–2 sentences maximum.
- Use `code` formatting for all model names, field names, and file names.

## Data Flow

### Data Models
One bullet per model/entity found in the code. Format:
- **`ModelName`:** List 3–5 key fields inline (e.g., id, status, assignedTo). One sentence on its purpose.

### Data Flow Description
Write a numbered step-by-step flow showing how data moves through the system.
Format as a numbered list, not bullets:
1. **UI Layer:** How the user triggers data retrieval or mutation.
2. **State/Logic Layer:** Which BLoC event, action, or controller handles it.
3. **Service Layer:** Which service or use case processes the request.
4. **API/Network Layer:** The API call made (method + endpoint).
5. **Repository Layer:** How the response is parsed and returned.
6. **State Update:** How the UI is updated with the new data.

### Storage
One bullet per storage mechanism:
- **`StorageType`:** Name the technology (e.g., SQLite, PostgreSQL, REST API, SharedPreferences) and what it stores.

Use only what exists in the files. Do NOT invent models or storage systems.
'''
)