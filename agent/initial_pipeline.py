"""
Initial pipeline — generates a full system design document from a GitHub repo URL.

This runs ONCE when a user pastes a GitHub URL for the first time.
It produces:
  1. A full .docx design document (saved locally + pushed as DOCUMENTATION.md to the repo)
  2. A section-map JSON file that records which source files each doc section was built from.
     This map is used by the webhook pipeline to do smart partial updates.

Pipeline steps:
  fetch_repo_context → detect_repo_type → analyze_tech_stack → compute_metrics
  → generate_system_overview → save_docx → push_markdown → save_section_map
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import env_loader  # noqa: F401

from analyzers.metrics import compute_metrics
from analyzers.repo_type_detector import detect_repo_type
from analyzers.tech_stack_analyzer import analyze_tech_stack
from github.fetcher import fetch_repo_context
from github.pusher import push_markdown_to_repo
from llm.model import get_llm
from llm.prompts import (
    ARCHITECTURE_TEMPLATE,
    API_SECTION_TEMPLATE,
    DATA_FLOW_TEMPLATE,
    REPO_DESCRIPTION_TEMPLATE,
)
from agent.docx_builder import build_initial_docx
from agent.section_map import save_section_map

INITIAL_PIPELINE_ORDER = [
    "fetch_repo_context",
    "detect_repo_type",
    "analyze_tech_stack",
    "compute_metrics",
    "generate_repo_description",
    "generate_architecture",
    "generate_api_section",
    "generate_data_flow",
    "save_docx",
    "push_markdown",
    "save_section_map",
]


def run_initial_pipeline(
    owner: str,
    repo: str,
    branch: str = "main",
    on_step_update: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """
    Generates a full design document for a GitHub repo from scratch.
    Returns a result dict with status, docx_path, markdown_url.
    """
    print(f"\n{'=' * 55}")
    print("Initial pipeline started")
    print(f"Repo  : {owner}/{repo}  Branch: {branch}")
    print(f"{'=' * 55}\n")

    ctx: dict[str, Any] = {
        "owner": owner,
        "repo": repo,
        "branch": branch,
        "is_initial": True,
    }

    steps_completed: list[str] = []
    result: dict[str, Any] = {
        "owner": owner,
        "repo": repo,
        "branch": branch,
        "status": "failed",
        "docx_path": None,
        "markdown_url": None,
        "error": None,
        "steps_completed": steps_completed,
        "current_step": None,
    }

    def _notify(step: str):
        result["current_step"] = step
        if on_step_update:
            on_step_update({
                "current_step": step,
                "steps_completed": list(steps_completed),
            })

    # ── Step functions ────────────────────────────────────────────────────────

    def fetch_repo_ctx():
        repo_data = fetch_repo_context(owner=owner, repo=repo)
        ctx["file_tree"] = repo_data["file_tree"]
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

    def generate_repo_description():
        llm = get_llm()
        repo_name = repo
        key_files_text = ""
        for filepath, content in ctx["key_file_contents"].items():
            key_files_text += f"\n--- {filepath} ---\n{content[:2000]}\n"
            if len(key_files_text) > 10000:
                break
        file_tree_text = "\n".join(ctx["file_tree"][:150])
        prompt = REPO_DESCRIPTION_TEMPLATE.format(
            repo_name=repo_name,
            file_tree=file_tree_text,
            key_files_content=key_files_text,
        )
        ctx["repo_description"] = str(llm.invoke(prompt))
        # Tag: which files contributed to repo description
        ctx["_section_files"] = ctx.get("_section_files", {})
        ctx["_section_files"]["repo_description"] = list(ctx["key_file_contents"].keys())
        print("  Repo description generated")

    def generate_architecture():
        llm = get_llm()
        file_tree_text = "\n".join(ctx["file_tree"][:200])
        key_files_text = ""
        for filepath, content in ctx["key_file_contents"].items():
            key_files_text += f"\n--- {filepath} ---\n{content[:1500]}\n"
            if len(key_files_text) > 8000:
                break
        prompt = ARCHITECTURE_TEMPLATE.format(
            repo_name=repo,
            file_tree=file_tree_text,
            key_files_content=key_files_text,
        )
        ctx["architecture"] = str(llm.invoke(prompt))
        ctx["_section_files"]["architecture"] = [
            f for f in ctx["file_tree"]
            if any(f.endswith(ext) for ext in (".py", ".ts", ".tsx", ".js", ".jsx", ".dart", ".kt", ".swift"))
            and "test" not in f.lower()
        ][:20]
        print("  Architecture section generated")

    def generate_api_section():
        llm = get_llm()
        # Find API-related files
        api_files = [
            f for f in ctx["file_tree"]
            if any(k in f.lower() for k in ("route", "api", "endpoint", "controller", "view", "handler"))
        ]
        api_content = ""
        for filepath in api_files[:10]:
            from github.fetcher import _fetch_file_content, _get_base_and_headers
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
            api_content = "No explicit API/route files found. Infer from available code."

        prompt = API_SECTION_TEMPLATE.format(
            repo_name=repo,
            api_files_content=api_content,
        )
        ctx["api_section"] = str(llm.invoke(prompt))
        ctx["_section_files"]["api_section"] = api_files[:20]
        print("  API section generated")

    def generate_data_flow():
        llm = get_llm()
        # Find model/db/schema files
        data_files = [
            f for f in ctx["file_tree"]
            if any(k in f.lower() for k in ("model", "schema", "db", "database", "migration", "entity", "store", "repository"))
        ]
        data_content = ""
        for filepath in data_files[:10]:
            from github.fetcher import _fetch_file_content, _get_base_and_headers
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
            data_content = "No explicit model/schema files found. Infer from available code."

        prompt = DATA_FLOW_TEMPLATE.format(
            repo_name=repo,
            data_files_content=data_content,
        )
        ctx["data_flow"] = str(llm.invoke(prompt))
        ctx["_section_files"]["data_flow"] = data_files[:20]
        print("  Data flow section generated")

    def save_docx():
        docx_path = build_initial_docx(ctx)
        ctx["docx_path"] = docx_path
        print(f"  DOCX saved: {docx_path}")

    def push_markdown():
        md = _build_initial_markdown(ctx)
        url = push_markdown_to_repo(md, "initial", branch, owner=owner, repo=repo)
        ctx["markdown_url"] = url
        print(f"  Markdown pushed: {url}")

    def do_save_section_map():
        save_section_map(owner, repo, ctx.get("_section_files", {}))
        print("  Section map saved")

    step_fns = {
        "fetch_repo_context":       fetch_repo_ctx,
        "detect_repo_type":         detect_type,
        "analyze_tech_stack":       analyze_stack,
        "compute_metrics":          run_metrics,
        "generate_repo_description": generate_repo_description,
        "generate_architecture":    generate_architecture,
        "generate_api_section":     generate_api_section,
        "generate_data_flow":       generate_data_flow,
        "save_docx":                save_docx,
        "push_markdown":            push_markdown,
        "save_section_map":         do_save_section_map,
    }

    try:
        for step_name in INITIAL_PIPELINE_ORDER:
            _notify(step_name)
            step_fns[step_name]()
            steps_completed.append(step_name)
            if on_step_update:
                on_step_update({
                    "current_step": step_name,
                    "steps_completed": list(steps_completed),
                })

        result["status"] = "success"
        result["docx_path"] = ctx.get("docx_path")
        result["markdown_url"] = ctx.get("markdown_url")
        if on_step_update:
            on_step_update({
                "status": "success",
                "steps_completed": list(steps_completed),
                "docx_path": result["docx_path"],
                "markdown_url": result["markdown_url"],
                "error": None,
            })

        print(f"\n{'=' * 55}")
        print("Initial pipeline completed successfully")
        print(f"DOCX     : {ctx.get('docx_path')}")
        print(f"Markdown : {ctx.get('markdown_url')}")
        print(f"{'=' * 55}\n")

    except Exception as error:
        result["error"] = str(error)
        result["docx_path"] = ctx.get("docx_path")
        if on_step_update:
            on_step_update({
                "status": "failed",
                "current_step": result["current_step"],
                "steps_completed": list(steps_completed),
                "error": result["error"],
            })
        print(f"Initial pipeline failed at '{result['current_step']}': {error}")

    return result


def _build_initial_markdown(ctx: dict) -> str:
    repo_name = ctx.get("repo", "Unknown")
    owner = ctx.get("owner", "")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    branch = ctx.get("branch", "main")

    lines = [
        f"# System Design Document — {owner}/{repo_name}",
        f"\n> Auto-generated | Created: {now} | Branch: `{branch}`\n",
        "> This document is automatically regenerated on every commit by the Git Doc Agent.\n",
        "---\n",
    ]

    repo_desc = ctx.get("repo_description", "")
    if repo_desc:
        lines.append(repo_desc)
        lines.append("\n---\n")

    architecture = ctx.get("architecture", "")
    if architecture:
        lines.append("## Architecture\n")
        lines.append(architecture)
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
        infra = tech.get("infra", [])
        if infra:
            lines.append(f"\n**Infrastructure:** {', '.join(infra)}\n")
        lines.append("\n---\n")

    metrics = ctx.get("metrics", [])
    if metrics:
        lines.append("## Code Quality Metrics\n")
        lines.append("| Metric | Value | Status |")
        lines.append("|---|---|---|")
        for m in metrics:
            lines.append(f"| {m.get('metric','')} | {m.get('value','')} | {m.get('status','')} |")
        lines.append("\n---\n")

    api_section = ctx.get("api_section", "")
    if api_section:
        lines.append("## API Endpoints\n")
        lines.append(api_section)
        lines.append("\n---\n")

    data_flow = ctx.get("data_flow", "")
    if data_flow:
        lines.append("## Data Flow\n")
        lines.append(data_flow)
        lines.append("\n---\n")

    return "\n".join(lines)
