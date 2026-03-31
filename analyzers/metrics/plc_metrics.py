"""Metrics for PLC / Industrial Automation repositories."""

from analyzers.metrics.base_metrics import BaseMetrics

PLC_EXTENSIONS = {".l5x", ".L5X", ".st", ".il", ".fbd", ".ld", ".acd"}


class PLCMetrics(BaseMetrics):

    def compute(self, file_tree: list[str], key_file_contents: dict[str, str]) -> list[dict]:
        metrics = []

        plc_files = [f for f in file_tree if any(f.endswith(ext) for ext in PLC_EXTENSIONS)]
        metrics.append({
            "metric": "Total PLC Files",
            "value": str(len(plc_files)),
            "status": "ℹ️ Info",
        })

        # File type breakdown
        ext_counts = {}
        for f in plc_files:
            ext = f.rsplit(".", 1)[-1].upper()
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
        if ext_counts:
            breakdown = ", ".join(f"{ext}: {count}" for ext, count in ext_counts.items())
            metrics.append({
                "metric": "File Type Breakdown",
                "value": breakdown,
                "status": "ℹ️ Info",
            })

        # Documentation presence
        doc_files = [f for f in file_tree if f.lower().endswith((".md", ".docx", ".pdf", ".txt"))]
        metrics.append({
            "metric": "Documentation Files",
            "value": str(len(doc_files)),
            "status": self._status(len(doc_files), 3, 1),
        })

        # README
        has_readme = any("readme" in f.lower() for f in file_tree)
        metrics.append({
            "metric": "README Present",
            "value": "Yes" if has_readme else "No",
            "status": "✅ Good" if has_readme else "❌ Needs Attention",
        })

        # Structured Text vs Ladder
        st_files = [f for f in plc_files if f.endswith(".st")]
        l5x_files = [f for f in plc_files if f.lower().endswith(".l5x")]
        metrics.append({
            "metric": "Structured Text Files",
            "value": str(len(st_files)),
            "status": "ℹ️ Info",
        })
        metrics.append({
            "metric": "Rockwell L5X Files",
            "value": str(len(l5x_files)),
            "status": "ℹ️ Info",
        })

        # Version control hygiene
        has_gitignore = any(".gitignore" in f for f in file_tree)
        metrics.append({
            "metric": "Git Hygiene (.gitignore)",
            "value": "Present" if has_gitignore else "Not Found",
            "status": "✅ Good" if has_gitignore else "⚠️ Average",
        })

        return metrics
