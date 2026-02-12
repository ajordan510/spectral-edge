"""
Shared utilities for batch output modules (CSV, Excel, PowerPoint).
"""

from typing import Optional


def sanitize_filename_component(value: Optional[str]) -> str:
    """Return a filesystem-safe filename component.

    Replaces characters that are not alphanumeric, hyphens, or underscores
    with underscores and strips leading/trailing underscores.

    Parameters
    ----------
    value : str or None
        Raw filename component (e.g. event name, prefix).

    Returns
    -------
    str
        Sanitized string safe for use in file paths.  Empty string if
        *value* is None or blank.
    """
    text = (value or "").strip()
    if not text:
        return ""
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in text)
    return safe.strip("_")
