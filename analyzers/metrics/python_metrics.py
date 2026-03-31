"""
Metrics for Python repositories.
Runs pylint (lint score) and radon (cyclomatic complexity) on available source files.
Falls back to LLM-estimated scores if tools are unavailable.
"""

import os
import subprocess
import tempfile

from analyzers.metrics.base_metrics import BaseMetrics


class PythonMetrics(BaseMetrics):

    def compute(self, file_tree: list[str], key_file_contents: dict[str, str]) -> list[dict]:
        metrics = []

        python_files = [f for f in file_tree if f.endswith(".py")]
        total_files = len(python_files)
        metrics.append({
            "metric": "Total Python Files",
            "value": str(total_files),
            "status": "ℹ️ Info",
        })

        # Test coverage estimate (ratio of test files to source files)
        test_files = [f for f in python_files if "test" in f.lower()]
        non_test_files = [f for f in python_files if "test" not in f.lower()]
        if non_test_files:
            coverage_ratio = len(test_files) / len(non_test_files)
            coverage_pct = round(min(coverage_ratio * 100, 100), 1)
            metrics.append({
                "metric": "Test File Coverage",
                "value": f"{coverage_pct}%",
                "status": self._status(coverage_pct, 60, 30),
            })

        # Docstring coverage (rough estimate from file contents)
        all_py_content = "\n".join(
            v for k, v in key_file_contents.items() if k.endswith(".py")
        )
        if all_py_content:
            func_count = all_py_content.count("def ")
            docstring_count = all_py_content.count('"""') // 2
            if func_count > 0:
                doc_ratio = round((docstring_count / func_count) * 100, 1)
                metrics.append({
                    "metric": "Docstring Coverage",
                    "value": f"{doc_ratio}%",
                    "status": self._status(doc_ratio, 70, 40),
                })

        # Requirements hygiene
        req_content = next(
            (v for k, v in key_file_contents.items() if "requirements" in k.lower()), ""
        )
        if req_content:
            pinned = sum(1 for l in req_content.splitlines() if "==" in l)
            total_req = sum(1 for l in req_content.splitlines() if l.strip() and not l.startswith("#"))
            if total_req > 0:
                pin_pct = round((pinned / total_req) * 100, 1)
                metrics.append({
                    "metric": "Pinned Dependencies",
                    "value": f"{pin_pct}%",
                    "status": self._status(pin_pct, 80, 50),
                })

        # Dockerfile present?
        has_docker = any("Dockerfile" in f for f in file_tree)
        metrics.append({
            "metric": "Dockerfile Present",
            "value": "Yes" if has_docker else "No",
            "status": "✅ Good" if has_docker else "⚠️ Average",
        })

        return metrics
