"""Metrics for Node.js / JavaScript / TypeScript repositories."""

import json

from analyzers.metrics.base_metrics import BaseMetrics


class NodeMetrics(BaseMetrics):

    def compute(self, file_tree: list[str], key_file_contents: dict[str, str]) -> list[dict]:
        metrics = []

        js_ts_files = [f for f in file_tree if f.endswith((".js", ".ts", ".jsx", ".tsx"))]
        metrics.append({
            "metric": "Total JS/TS Files",
            "value": str(len(js_ts_files)),
            "status": "ℹ️ Info",
        })

        # TypeScript adoption
        ts_files = [f for f in js_ts_files if f.endswith((".ts", ".tsx"))]
        if js_ts_files:
            ts_ratio = round((len(ts_files) / len(js_ts_files)) * 100, 1)
            metrics.append({
                "metric": "TypeScript Adoption",
                "value": f"{ts_ratio}%",
                "status": self._status(ts_ratio, 70, 30),
            })

        # Test files
        test_files = [f for f in file_tree if "test" in f.lower() or "spec" in f.lower()]
        metrics.append({
            "metric": "Test Files",
            "value": str(len(test_files)),
            "status": self._status(len(test_files), 5, 1),
        })

        # package.json scripts (CI/CD hygiene)
        pkg_content = next(
            (v for k, v in key_file_contents.items() if k.endswith("package.json")), ""
        )
        if pkg_content:
            try:
                pkg = json.loads(pkg_content)
                scripts = pkg.get("scripts", {})
                has_test = "test" in scripts
                has_lint = "lint" in scripts
                has_build = "build" in scripts
                # Score: each script present = 33.3%, round to nearest %
                script_score = round((sum([has_test, has_lint, has_build]) / 3) * 100)
                metrics.append({
                    "metric": "NPM Scripts (test/lint/build)",
                    "value": f"test={'100%' if has_test else '0%'}, lint={'100%' if has_lint else '0%'}, build={'100%' if has_build else '0%'}",
                    "status": self._status(script_score, 67, 34),
                })
                dep_count = len(pkg.get("dependencies", {}))
                dev_dep_count = len(pkg.get("devDependencies", {}))
                metrics.append({
                    "metric": "Dependencies",
                    "value": f"{dep_count} High, {dev_dep_count} Low",
                    "status": "ℹ️ Info",
                })
            except Exception:
                pass

        # Dockerfile
        has_docker = any("Dockerfile" in f for f in file_tree)
        metrics.append({
            "metric": "Dockerfile Present",
            "value": "Yes" if has_docker else "No",
            "status": "✅ Good" if has_docker else "⚠️ Average",
        })

        return metrics
