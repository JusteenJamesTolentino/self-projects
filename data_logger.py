import os
import json
import time
from typing import List, Dict, Any, Optional


LOG_FILENAME = "data_log.jsonl"  # newline-delimited JSON


def _log_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, LOG_FILENAME)


def ensure_log_exists() -> None:
    """Create an empty log file if it does not already exist.

    This guarantees that downstream features expecting a physical file
    (e.g., watchers, backup scripts) can find it immediately on app start.
    """
    try:
        path = _log_path()
        if not os.path.exists(path):
            # Create an empty file (no JSON array, we use JSONL entries per line).
            with open(path, "w", encoding="utf-8") as f:
                f.write("")
    except Exception:
        # Silently ignore; absence will be handled lazily on first write anyway.
        pass


def log_reading(kind: str, data: Dict[str, Any]) -> None:
    """Append a single reading as a JSON line.

    kind: category e.g. 'env', 'distance', etc.
    data: dict payload (will be shallow-copied). A 'kind' and 'ts' are injected if absent.
    """
    try:
        entry = dict(data) if data else {}
        entry.setdefault("kind", kind)
        entry.setdefault("ts", time.time())
        path = _log_path()
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # Silent failure; logging must not break UI.
        pass


def load_entries(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load entries from the log file. If limit provided, return only the newest N."""
    path = _log_path()
    if not os.path.exists(path):
        return []
    entries: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            if limit is None:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        continue
            else:
                # Efficient tail read: read all then slice (file is likely small). Could optimize later.
                lines = f.readlines()
                for line in lines[-limit:]:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        continue
    except Exception:
        return []
    return entries


def clear_log() -> bool:
    try:
        path = _log_path()
        if os.path.exists(path):
            os.remove(path)
        return True
    except Exception:
        return False


def export_csv(destination_path: str) -> bool:
    import csv
    entries = load_entries()
    if not entries:
        return False
    # Collect union of keys for header
    header_keys = set()
    for e in entries:
        header_keys.update(e.keys())
    fieldnames = sorted(header_keys)
    try:
        with open(destination_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for e in entries:
                writer.writerow({k: e.get(k, "") for k in fieldnames})
        return True
    except Exception:
        return False


def compute_stats(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    from math import inf
    stats: Dict[str, Any] = {
        "count": len(entries),
        "kinds": {},
        "temperature": {"min": None, "max": None, "avg": None},
        "humidity": {"min": None, "max": None, "avg": None},
        "distance": {"min": None, "max": None, "avg": None},
        "first_ts": None,
        "last_ts": None,
    }
    if not entries:
        return stats
    temp_vals = []
    hum_vals = []
    dist_vals = []
    for e in entries:
        k = e.get("kind", "?")
        stats["kinds"][k] = stats["kinds"].get(k, 0) + 1
        ts = e.get("ts")
        if isinstance(ts, (int, float)):
            if stats["first_ts"] is None or ts < stats["first_ts"]:
                stats["first_ts"] = ts
            if stats["last_ts"] is None or ts > stats["last_ts"]:
                stats["last_ts"] = ts
        if k == "env":
            t = e.get("temperature")
            h = e.get("humidity")
            if isinstance(t, (int, float)):
                temp_vals.append(t)
            if isinstance(h, (int, float)):
                hum_vals.append(h)
        elif k == "distance":
            d = e.get("distance")
            if isinstance(d, (int, float)):
                dist_vals.append(d)
    def finalize(values, key):
        if values:
            stats[key]["min"] = min(values)
            stats[key]["max"] = max(values)
            stats[key]["avg"] = sum(values) / len(values)
    finalize(temp_vals, "temperature")
    finalize(hum_vals, "humidity")
    finalize(dist_vals, "distance")
    return stats


# Ensure the log file exists as soon as this module is imported.
ensure_log_exists()
