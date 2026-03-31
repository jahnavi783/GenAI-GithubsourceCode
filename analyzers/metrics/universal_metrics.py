"""
Universal metrics — same 6-row table for ANY repository type.
Rows (always in this order):
  1. Total Project Files
  2. Primary Language Adoption
  3. Test Files
  4. Test / Lint / Build Score
  5. Dependencies
  6. Dockerfile Present
"""

import json
import re
import os
from analyzers.metrics.base_metrics import BaseMetrics

EXT_LANGUAGE_MAP = {
    ".py": "Python", ".dart": "Dart", ".swift": "Swift",
    ".kt": "Kotlin", ".kts": "Kotlin", ".js": "JavaScript",
    ".jsx": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".java": "Java", ".go": "Go", ".rs": "Rust", ".cs": "C#",
    ".cpp": "C++", ".c": "C", ".rb": "Ruby", ".php": "PHP",
    ".st": "Structured Text", ".l5x": "Rockwell L5X",
}

IGNORE_DIRS = {
    "node_modules", ".git", "build", "dist", ".dart_tool",
    ".pub-cache", "__pycache__", ".gradle", "Pods", ".cache",
}


class UniversalMetrics(BaseMetrics):

    def compute(self, file_tree: list[str], key_file_contents: dict[str, str]) -> list[dict]:
        metrics = []

        # ── 1. TOTAL PROJECT FILES ────────────────────────────────────────
        filtered = [f for f in file_tree if not any(ig in f for ig in IGNORE_DIRS)]
        metrics.append({
            "metric": "Total Project Files",
            "value":  str(len(filtered)),
            "status": "ℹ️ Info",
        })

        # ── 2. PRIMARY LANGUAGE ADOPTION ──────────────────────────────────
        lang_counts = {}
        for filepath in filtered:
            _, ext = os.path.splitext(filepath)
            lang = EXT_LANGUAGE_MAP.get(ext.lower())
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

        if lang_counts:
            total_code = sum(lang_counts.values())
            primary_lang, primary_count = max(lang_counts.items(), key=lambda x: x[1])
            adoption_pct = round((primary_count / total_code) * 100, 1)
            metrics.append({
                "metric": "Primary Language",
                "value":  f"{primary_lang}  {adoption_pct}%  ({primary_count} files)",
                "status": self._status(adoption_pct, 60, 30),
            })
        else:
            metrics.append({
                "metric": "Primary Language",
                "value":  "Unknown",
                "status": "ℹ️ Info",
            })

        # ── 3. TEST FILES ─────────────────────────────────────────────────
        test_files = [f for f in filtered if "test" in f.lower() or "spec" in f.lower()]
        metrics.append({
            "metric": "Test Files",
            "value":  str(len(test_files)),
            "status": self._status(len(test_files), 5, 1),
        })

        # ── 4. TEST / LINT / BUILD SCORE ──────────────────────────────────
        test_score = "N/A"
        lint_score = "N/A"
        build_score = "N/A"
        overall_score = 0
        checks = 0

        # package.json (Node / React)
        pkg_raw = next((v for k, v in key_file_contents.items() if k.endswith("package.json")), "")
        if pkg_raw:
            try:
                pkg = json.loads(pkg_raw)
                scripts = pkg.get("scripts", {})
                test_score  = "100%" if "test"  in scripts else "0%"
                lint_score  = "100%" if "lint"  in scripts else "0%"
                build_score = "100%" if "build" in scripts else "0%"
                overall_score += sum([
                    100 if "test"  in scripts else 0,
                    100 if "lint"  in scripts else 0,
                    100 if "build" in scripts else 0,
                ])
                checks += 3
            except Exception:
                pass

        # pubspec.yaml (Flutter / Dart)
        pubspec_raw = next(
            (v for k, v in key_file_contents.items() if "pubspec.yaml" in k or "pubspec.yml" in k), ""
        )
        if pubspec_raw and test_score == "N/A":
            has_flutter_test = "flutter_test" in pubspec_raw
            has_build_runner = "build_runner" in pubspec_raw
            test_score  = "100%" if has_flutter_test else "0%"
            build_score = "100%" if has_build_runner else "0%"
            lint_score  = "N/A"
            overall_score += (100 if has_flutter_test else 0) + (100 if has_build_runner else 0)
            checks += 2

        # requirements.txt (Python)
        req_raw = next((v for k, v in key_file_contents.items() if "requirements" in k.lower()), "")
        if req_raw and test_score == "N/A":
            has_pytest = "pytest" in req_raw.lower()
            has_lint   = "flake8" in req_raw.lower() or "pylint" in req_raw.lower()
            test_score  = "100%" if has_pytest else "0%"
            lint_score  = "100%" if has_lint   else "0%"
            build_score = "N/A"
            overall_score += (100 if has_pytest else 0) + (100 if has_lint else 0)
            checks += 2

        # Gradle (Kotlin / Android)
        gradle_raw = next((v for k, v in key_file_contents.items() if "build.gradle" in k), "")
        if gradle_raw and test_score == "N/A":
            has_test  = "testImplementation" in gradle_raw
            has_build = "assembleRelease" in gradle_raw or "buildTypes" in gradle_raw
            test_score  = "100%" if has_test  else "0%"
            build_score = "100%" if has_build else "0%"
            overall_score += (100 if has_test else 0) + (100 if has_build else 0)
            checks += 2

        # GitHub Actions CI (any language — gives build signal)
        ci_files = [f for f in file_tree if ".github/workflows" in f]
        if ci_files and build_score == "N/A":
            build_score = "100%"
            overall_score += 100
            checks += 1

        score_str = f"test={test_score}, lint={lint_score}, build={build_score}"
        avg = round(overall_score / checks) if checks > 0 else 0
        metrics.append({
            "metric": "Test / Lint / Build",
            "value":  score_str,
            "status": self._status(avg, 67, 34),
        })

        # ── 5. DEPENDENCIES ───────────────────────────────────────────────
        dep_value = "N/A"

        if pkg_raw:
            try:
                pkg = json.loads(pkg_raw)
                prod = len(pkg.get("dependencies", {}))
                dev  = len(pkg.get("devDependencies", {}))
                dep_value = f"{prod} prod, {dev} dev  (package.json)"
            except Exception:
                pass

        if dep_value == "N/A" and pubspec_raw:
            dep_lines = re.findall(r"^\s{2}[\w_]+:", pubspec_raw, re.MULTILINE)
            dep_value = f"{len(dep_lines)} packages  (pubspec.yaml)"

        if dep_value == "N/A" and req_raw:
            dep_lines = [l for l in req_raw.splitlines() if l.strip() and not l.startswith("#")]
            dep_value = f"{len(dep_lines)} packages  (requirements.txt)"

        if dep_value == "N/A" and gradle_raw:
            deps = re.findall(r"implementation|testImplementation", gradle_raw)
            dep_value = f"{len(deps)} packages  (build.gradle)"

        metrics.append({
            "metric": "Dependencies",
            "value":  dep_value,
            "status": "ℹ️ Info",
        })

        # ── 6. DOCKERFILE PRESENT ─────────────────────────────────────────
        has_docker = any("Dockerfile" in f for f in file_tree)
        metrics.append({
            "metric": "Dockerfile Present",
            "value":  "Yes" if has_docker else "No",
            "status": "✅ Good" if has_docker else "⚠️ Average",
        })

        return metrics
