"""
Webhook pipeline — runs on every GitHub commit.

Now fully repo-aware: owner/repo are read from the webhook payload (passed in
as arguments), not from the hardcoded .env. This means one running instance
handles webhooks from ANY repo the GitHub App is installed on.

Smart update logic:
  1. Fetch commit diff → identify changed files
  2. Load section map → determine which doc sections are affected
  3. Regenerate ONLY affected sections
  4. Always regenerate: commit_docs + impact_analysis (they are per-commit)
  5. Save .docx + push DOCUMENTATION.md to repo
"""

import os
import env_loader  # noqa: F401
from typing import Any, Callable

from agent.section_map import get_affected_sections, update_section_map
from agent.docx_builder import build_incremental_docx

from analyzers.metrics import compute_metrics
from analyzers.repo_type_detector import detect_repo_type
from analyzers.tech_stack_analyzer import analyze_tech_stack
from github.fetcher import fetch_commit_diff, fetch_repo_context, _fetch_file_content, _get_base_and_headers
from github.pusher import push_markdown_to_repo
from llm.model import get_llm
from llm.prompts import (
    DOC_TEMPLATE,
    IMPACT_ANALYSIS_TEMPLATE,
    REPO_DESCRIPTION_TEMPLATE,
    ARCHITECTURE_TEMPLATE,
    API_SECTION_TEMPLATE,
    DATA_FLOW_TEMPLATE,
)
from vectordb.store import retrieve_similar, store_commit


PIPELINE_ORDER = [
    "fetch_diff",
    "fetch_repo_context",
    "detect_repo_type",
    "analyze_tech_stack",
    "compute_metrics",
    "resolve_affected_sections",
    "retrieve_context",
    "regenerate_sections",
    "generate_impact_analysis",
    "generate_commit_docs",
    "save_vectordb",
    "save_docx",
    "push_markdown",
]


class PipelineStepError(RuntimeError):
    def __init__(self, step: str, original_error: Exception):
        self.step = step
        self.original_error = original_error
        super().__init__(f"Step '{step}' failed: {original_error}")


def run_pipeline(
    commit_sha: str,
    branch: str,
    owner: str = None,
    repo: str = None,
    on_step_update: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    # Resolve owner/repo: prefer explicit args, fall back to env
    owner = (owner or os.getenv("GITHUB_OWNER", "")).strip()
    repo  = (repo  or os.getenv("GITHUB_REPO",  "")).strip()

    print(f"\n{'=' * 50}")
    print("Webhook pipeline started")
    print(f"Repo   : {owner}/{repo}")
    print(f"Commit : {commit_sha[:7]}")
    print(f"Branch : {branch}")
    print(f"{'=' * 50}\n")

    ctx: dict[str, Any] = {
        "commit_sha": commit_sha,
        "branch":     branch,
        "owner":      owner,
        "repo":       repo,
    }

    steps_completed: list[str] = []
    result: dict[str, Any] = {
        "commit_sha": commit_sha,
        "branch":     branch,
        "owner":      owner,
        "repo":       repo,
        "status":     "failed",
        "docx_path":  None,
        "markdown_url": None,
        "error":      None,
        "steps_completed": steps_completed,
        "current_step":    None,
    }

    def _notify(step: str):
        result["current_step"] = step
        if on_step_update:
            on_step_update({"current_step": step, "steps_completed": list(steps_completed)})

    # ── Step functions ─────────────────────────────────────────────────────────

    def fetch_diff():
        data = fetch_commit_diff(ctx["commit_sha"], owner=owner, repo=repo)
        ctx.update(data)
        print(f"  Fetched diff for {ctx['commit_sha'][:7]}: {ctx.get('files_changed', [])}")

    def fetch_repo_ctx():
        repo_data = fetch_repo_context(owner=owner, repo=repo)
        ctx["file_tree"]         = repo_data["file_tree"]
        ctx["key_file_contents"] = repo_data["key_file_contents"]
        print(f"  Fetched repo context: {len(ctx['file_tree'])} files")

    def detect_type():
        ctx["repo_type"] = detect_repo_type(ctx["file_tree"], ctx["key_file_contents"])
        print(f"  Repo type: {ctx['repo_type']}")

    def analyze_stack():
        ctx["tech_stack"] = analyze_tech_stack(ctx["file_tree"], ctx["key_file_contents"])
        print(f"  Tech stack: {ctx['tech_stack'].get('languages', [])}")

    def run_metrics():
        ctx["metrics"] = compute_metrics(
            ctx["repo_type"], ctx["file_tree"], ctx["key_file_contents"]
        )
        print(f"  Computed {len(ctx['metrics'])} metrics")

    def resolve_affected_sections():
        changed_files = ctx.get("files_changed", [])
        affected = get_affected_sections(owner, repo, changed_files)
        ctx["affected_sections"] = affected
        print(f"  Affected sections: {affected}")

    def retrieve_context():
        ctx["similar_docs"] = retrieve_similar(ctx.get("diff", ""), top_k=3)
        print(f"  Retrieved {len(ctx['similar_docs'])} similar docs")

    def regenerate_sections():
        llm = get_llm()
        affected       = ctx.get("affected_sections", [])
        repo_name      = repo
        file_tree_text = "\n".join(ctx["file_tree"][:150])
        key_files_text = ""
        for filepath, content in ctx["key_file_contents"].items():
            key_files_text += f"\n--- {filepath} ---\n{content[:2000]}\n"
            if len(key_files_text) > 10000:
                break

        if "repo_description" in affected:
            prompt = REPO_DESCRIPTION_TEMPLATE.format(
                repo_name=repo_name,
                file_tree=file_tree_text,
                key_files_content=key_files_text,
            )
            ctx["repo_description"] = str(llm.invoke(prompt))
            update_section_map(owner, repo, "repo_description", list(ctx["key_file_contents"].keys()))
            print("  Regenerated: repo_description")

        if "architecture" in affected:
            prompt = ARCHITECTURE_TEMPLATE.format(
                repo_name=repo_name,
                file_tree=file_tree_text,
                key_files_content=key_files_text,
            )
            ctx["architecture"] = str(llm.invoke(prompt))
            print("  Regenerated: architecture")

        if "api_section" in affected:
            api_files = [f for f in ctx["file_tree"]
                         if any(k in f.lower() for k in ("route", "api", "endpoint", "controller", "view", "handler"))]
            api_content = ""
            for filepath in api_files[:10]:
                try:
                    base, headers_json, _ = _get_base_and_headers(owner=owner, repo=repo)
                    content = _fetch_file_content(base, filepath, headers_json)
                    if content:
                        api_content += f"\n--- {filepath} ---\n{content[:1500]}\n"
                except Exception:
                    pass
                if len(api_content) > 8000:
                    break
            if not api_content:
                api_content = "No explicit API/route files found."
            prompt = API_SECTION_TEMPLATE.format(repo_name=repo_name, api_files_content=api_content)
            ctx["api_section"] = str(llm.invoke(prompt))
            update_section_map(owner, repo, "api_section", api_files[:20])
            print("  Regenerated: api_section")

        if "data_flow" in affected:
            data_files = [f for f in ctx["file_tree"]
                          if any(k in f.lower() for k in ("model", "schema", "db", "database", "migration", "entity", "store", "repository"))]
            data_content = ""
            for filepath in data_files[:10]:
                try:
                    base, headers_json, _ = _get_base_and_headers(owner=owner, repo=repo)
                    content = _fetch_file_content(base, filepath, headers_json)
                    if content:
                        data_content += f"\n--- {filepath} ---\n{content[:1500]}\n"
                except Exception:
                    pass
                if len(data_content) > 8000:
                    break
            if not data_content:
                data_content = "No explicit model/schema files found."
            prompt = DATA_FLOW_TEMPLATE.format(repo_name=repo_name, data_files_content=data_content)
            ctx["data_flow"] = str(llm.invoke(prompt))
            update_section_map(owner, repo, "data_flow", data_files[:20])
            print("  Regenerated: data_flow")

    def generate_impact_analysis():
        llm = get_llm()
        repo_overview = ctx.get("repo_description", "")[:2000]
        files_changed = ", ".join(ctx.get("files_changed", []))
        prompt = IMPACT_ANALYSIS_TEMPLATE.format(
            repo_overview=repo_overview,
            files_changed=files_changed,
            diff=ctx.get("diff", "")[:3000],
        )
        ctx["impact_analysis"] = str(llm.invoke(prompt))
        print("  Impact analysis generated")

    def generate_commit_docs():
        llm = get_llm()
        context = "\n---\n".join(
            [item.get("documentation", "") for item in ctx.get("similar_docs", [])]
        )
        prompt = DOC_TEMPLATE.format(
            author=ctx.get("author", "Unknown"),
            branch=ctx.get("branch", "Unknown"),
            sha=ctx.get("commit_sha", "Unknown"),
            timestamp=ctx.get("timestamp", ""),
            files=", ".join(ctx.get("files_changed", [])),
            context=context if context else "No similar past commits found",
            diff=ctx.get("diff", "")[:4000],
        )
        ctx["documentation"] = str(llm.invoke(prompt))
        print("  Commit documentation generated")

    def save_to_vectordb():
        store_commit(
            ctx["commit_sha"], ctx.get("diff", ""),
            ctx.get("documentation", ""), ctx.get("author", "Unknown")
        )
        print("  Saved to ChromaDB")

    def save_docx():
        docx_path = build_incremental_docx(ctx)
        ctx["docx_path"] = docx_path
        print(f"  DOCX saved: {docx_path}")

    def push_markdown():
        md = _build_incremental_markdown(ctx)
        url = push_markdown_to_repo(md, ctx["commit_sha"], ctx.get("branch", "main"),
                                    owner=owner, repo=repo)
        ctx["markdown_url"] = url
        print(f"  Markdown pushed: {url}")

    steps = {
        "fetch_diff":                fetch_diff,
        "fetch_repo_context":        fetch_repo_ctx,
        "detect_repo_type":          detect_type,
        "analyze_tech_stack":        analyze_stack,
        "compute_metrics":           run_metrics,
        "resolve_affected_sections": resolve_affected_sections,
        "retrieve_context":          retrieve_context,
        "regenerate_sections":       regenerate_sections,
        "generate_impact_analysis":  generate_impact_analysis,
        "generate_commit_docs":      generate_commit_docs,
        "save_vectordb":             save_to_vectordb,
        "save_docx":                 save_docx,
        "push_markdown":             push_markdown,
    }

    try:
        for step_name in PIPELINE_ORDER:
            _notify(step_name)
            steps[step_name]()
            steps_completed.append(step_name)
            if on_step_update:
                on_step_update({"current_step": step_name, "steps_completed": list(steps_completed)})

        result["status"]       = "success"
        result["docx_path"]    = ctx.get("docx_path")
        result["markdown_url"] = ctx.get("markdown_url")
        if on_step_update:
            on_step_update({
                "status":          "success",
                "steps_completed": list(steps_completed),
                "docx_path":       result["docx_path"],
                "markdown_url":    result["markdown_url"],
                "error":           None,
            })
        print(f"\n{'=' * 50}\nPipeline completed for {owner}/{repo}\nDOCX: {ctx.get('docx_path')}\n{'=' * 50}\n")

    except Exception as error:
        result["error"] = str(error)
        result["docx_path"] = ctx.get("docx_path")
        if on_step_update:
            on_step_update({
                "status":          "failed",
                "current_step":    result["current_step"],
                "steps_completed": list(steps_completed),
                "error":           result["error"],
            })
        print(f"Pipeline failed at '{result['current_step']}' for {owner}/{repo} commit {commit_sha[:7]}: {error}")

    return result


def _build_incremental_markdown(ctx: dict) -> str:
    from datetime import datetime
    repo_name = ctx.get("repo", "Unknown")
    owner     = ctx.get("owner", "")
    now       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sha       = ctx.get("commit_sha", "")[:7]
    branch    = ctx.get("branch", "")
    author    = ctx.get("author", "Unknown")
    affected  = ctx.get("affected_sections", [])

    lines = [
        f"# Documentation — {owner}/{repo_name}",
        f"\n> Auto-generated | Updated: {now} | Commit: `{sha}` on `{branch}` by {author}\n",
        "> This file is automatically updated on every commit by the Git Doc Agent.\n",
        "---\n",
        "## Sections Updated This Commit\n",
    ]
    all_sections = ["repo_description", "architecture", "api_section", "data_flow"]
    for s in affected:
        if s in all_sections:
            lines.append(f"- ✅ Updated: **{s.replace('_', ' ').title()}**")
    for s in all_sections:
        if s not in affected:
            lines.append(f"- — Unchanged: {s.replace('_', ' ').title()}")
    lines.append("\n---\n")

    for key, heading in [("repo_description", None), ("architecture", "## Architecture"),
                         ("api_section", "## API Endpoints"), ("data_flow", "## Data Flow")]:
        val = ctx.get(key, "")
        if val:
            if heading:
                lines.append(heading + "\n")
            lines.append(val)
            lines.append("\n---\n")

    tech = ctx.get("tech_stack", {})
    if tech:
        lines.append("## Tools & Tech Stack\n")
        langs = tech.get("languages", [])
        if langs:
            lines.append("**Languages:** " + ", ".join(langs) + "\n")
        libs = tech.get("frameworks_and_libs", [])
        if libs:
            lines.append("\n| Library / Framework | Category |")
            lines.append("|---|---|")
            for lib in libs:
                lines.append(f"| {lib['name']} | {lib['category']} |")
        lines.append("\n---\n")

    metrics = ctx.get("metrics", [])
    if metrics:
        lines.append("## Code Quality Metrics\n")
        lines.append("| Metric | Value | Status |")
        lines.append("|---|---|---|")
        for m in metrics:
            lines.append(f"| {m.get('metric','')} | {m.get('value','')} | {m.get('status','')} |")
        lines.append("\n---\n")

    impact = ctx.get("impact_analysis", "")
    if impact:
        lines.append("## Impact Analysis\n")
        lines.append(impact)
        lines.append("\n---\n")

    docs = ctx.get("documentation", "")
    if docs:
        lines.append("## Commit Change Details\n")
        lines.append(docs)
        lines.append("\n---\n")

    return "\n".join(lines)
