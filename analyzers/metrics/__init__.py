from analyzers.metrics.universal_metrics import UniversalMetrics


def get_metrics_for_repo_type(repo_type: str):
    """All repo types now use the same unified 6-row metrics table."""
    return UniversalMetrics()


def compute_metrics(repo_type: str, file_tree: list[str], key_file_contents: dict[str, str]) -> list[dict]:
    """Convenience function - runs universal metrics for any repo type."""
    return UniversalMetrics().compute(file_tree, key_file_contents)
