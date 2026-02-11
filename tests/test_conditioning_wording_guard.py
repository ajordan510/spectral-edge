from pathlib import Path


LEGACY_RUNNING_MEAN_PHRASES = (
    "Running mean: on",
    "Running mean: off",
)


def test_no_legacy_running_mean_phrases_in_production_code():
    production_root = Path("spectral_edge")
    python_files = production_root.rglob("*.py")

    for path in python_files:
        content = path.read_text(encoding="utf-8", errors="ignore")
        for phrase in LEGACY_RUNNING_MEAN_PHRASES:
            assert phrase not in content, f"Legacy phrasing found in {path}: '{phrase}'"
