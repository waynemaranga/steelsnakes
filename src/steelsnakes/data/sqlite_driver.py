import sqlite3
import json
import hashlib # this is for generating unique IDs
from dataclasses import dataclass
import pathlib
from typing import Optional, Any, Dict, Iterable, List, Tuple
from datetime import datetime

@dataclass
class Schema:
    """SQLite schema"""

    @staticmethod
    def get_schema() -> str:
        """Return the SQL schema for the SQLite database."""
        # Intentionally minimal. We dynamically create per-table schemas
        # for each JSON file instead of using a single static schema.
        return ""

class Database:
    """..."""
    def __init__(self, db_path: pathlib.Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize the database with schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.executescript(Schema.get_schema())
            # Enable foreign key support
            cursor.execute("PRAGMA foreign_keys = ON;")
            # conn.commit()

    def get_section(self, section_type: str, designation: str) -> Optional[dict[str, Any]]:
        """Retrieve a section by type and designation."""
        # TODO: probably not working, double-check this
        # TODO: use try/except for error handling
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            section = cursor.execute(
                "SELECT * FROM sections WHERE section_type = ? AND designation = ?",
                (section_type.upper(), designation)
            ).fetchone()

            if not section:
                return None

            # Convert Row to dict
            section_dict = {key: section[key] for key in section.keys()}
            section_dict['section_type'] = section_dict['section_type'].lower()
            section_dict['designation'] = section_dict['designation'].upper()   
            return section_dict

    def search_sections(self, section_type: str, designation: Optional[str] = None) -> list[dict[str, Any]]:
        """Search for sections by type and optional designation."""
        return NotImplementedError


# -------------------------
# UK JSON → SQLite builder
# -------------------------

def _sanitize_table_name(name: str) -> str:
    """Return a safe SQLite table name derived from a filename stem."""
    safe = ''.join(ch if ch.isalnum() or ch == '_' else '_' for ch in name)
    # SQLite is case-insensitive for identifiers, keep upper for readability
    return safe.upper()


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool)) or value is None


def _coerce_bool_to_int(value: Any) -> Any:
    if isinstance(value, bool):
        return int(value)
    return value


def _infer_sql_type(values: Iterable[Any]) -> str:
    """Infer a suitable SQLite column affinity from a sample of Python values."""
    seen_text = False
    seen_real = False
    seen_int = False
    for v in values:
        if v is None:
            continue
        if isinstance(v, bool):
            seen_int = True
        elif isinstance(v, int):
            seen_int = True
        elif isinstance(v, float):
            seen_real = True
        elif isinstance(v, str):
            seen_text = True
        else:
            # Fallback to TEXT for anything else
            seen_text = True
    if seen_text:
        return "TEXT"
    if seen_real:
        return "REAL"
    if seen_int:
        return "INTEGER"
    return "TEXT"


def _flatten_rows_from_json(data: Any) -> List[Dict[str, Any]]:
    """
    Convert a JSON object into a list of row dicts.

    Strategy:
    - If the root is {designation -> props}, produce one row per key.
    - If the root is {category -> {designation -> props}}, produce rows
      with 'category' set and designation as "{category}:{key}" if missing.
    - For deeper nested structures, preserve the full object into a 'data' field
      (JSON string) and only surface top-level scalars as columns.
    """
    rows: List[Dict[str, Any]] = []

    if isinstance(data, dict):
        # Heuristic: check if values are dict-like of properties
        values = list(data.values())
        if values and all(isinstance(v, dict) for v in values):
            # Level 1: designation -> props OR category -> {...}
            for k, v in data.items():
                if isinstance(v, dict) and v and all(isinstance(v2, dict) for v2 in v.values()):
                    # Likely category -> {designation -> props}
                    category = k
                    for sub_key, sub_val in v.items():
                        row: Dict[str, Any] = {}
                        if isinstance(sub_val, dict):
                            row.update({kk: vv for kk, vv in sub_val.items() if _is_scalar(vv)})
                            # Always stash full sub-object as JSON string
                            row['data'] = json.dumps(sub_val, separators=(',', ':'), ensure_ascii=False)
                        else:
                            row['value'] = sub_val
                        row['category'] = category
                        # Prefer existing designation, else synthesize
                        designation = sub_val.get('designation') if isinstance(sub_val, dict) else None
                        if not designation:
                            designation = f"{category}:{sub_key}"
                        row['designation'] = str(designation)
                        rows.append(row)
                else:
                    # designation -> props
                    props = v if isinstance(v, dict) else {'value': v}
                    row: Dict[str, Any] = {}
                    row.update({kk: vv for kk, vv in props.items() if _is_scalar(vv)})
                    row['data'] = json.dumps(props, separators=(',', ':'), ensure_ascii=False)
                    # Prefer explicit designation, else key
                    designation = props.get('designation') if isinstance(props, dict) else None
                    if not designation:
                        designation = k
                    row['designation'] = str(designation)
                    rows.append(row)
        else:
            # Root dict of scalars → single row
            row = {kk: vv for kk, vv in data.items() if _is_scalar(vv)}
            row['data'] = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            if 'designation' not in row:
                row['designation'] = 'ITEM'
            rows.append(row)
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            row = {}
            if isinstance(item, dict):
                row.update({kk: vv for kk, vv in item.items() if _is_scalar(vv)})
                row['data'] = json.dumps(item, separators=(',', ':'), ensure_ascii=False)
            else:
                row['value'] = item
                row['data'] = json.dumps(item, separators=(',', ':'), ensure_ascii=False)
            if 'designation' not in row:
                row['designation'] = f"ITEM_{idx}"
            rows.append(row)
    else:
        # Single scalar
        rows.append({
            'designation': 'ITEM',
            'value': data,
            'data': json.dumps(data, separators=(',', ':'), ensure_ascii=False),
        })

    return rows


def _collect_column_types(rows: List[Dict[str, Any]]) -> Dict[str, str]:
    """Collect union of scalar columns across rows and infer SQLite types.

    Column names are normalized to avoid case-sensitive duplicates such as
    'I_yy' vs 'i_yy' and to keep only alphanumerics/underscore.
    """

    def _normalize_column_name(name: str) -> str:
        sanitized = ''.join(ch if (ch.isalnum() or ch == '_') else '_' for ch in name)
        if not sanitized:
            sanitized = 'col'
        if sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized.lower()

    samples: Dict[str, List[Any]] = {}
    for row in rows:
        for key, value in row.items():
            if key == 'data':
                continue
            if _is_scalar(value):
                nk = _normalize_column_name(key)
                samples.setdefault(nk, []).append(value)
    # Always ensure designation exists
    samples.setdefault('designation', []).append('')

    return {col: _infer_sql_type(vals) for col, vals in samples.items()}


def _create_table(conn: sqlite3.Connection, table: str, column_types: Dict[str, str]) -> None:
    cols = []
    # id primary key
    cols.append("id INTEGER PRIMARY KEY AUTOINCREMENT")
    # Stable columns first
    for name in sorted(column_types.keys()):
        if name == 'designation':
            cols.append("designation TEXT NOT NULL")
        else:
            cols.append(f"{name} {column_types[name]}")
    # JSON blob of full record
    cols.append("data TEXT")
    cols.append("created_at TEXT DEFAULT (datetime('now'))")

    ddl = f"CREATE TABLE IF NOT EXISTS {table} (" + ", ".join(cols) + ")"
    idx = f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{table}_designation ON {table}(designation)"
    cur = conn.cursor()
    cur.execute(ddl)
    cur.execute(idx)


def _insert_rows(conn: sqlite3.Connection, table: str, rows: List[Dict[str, Any]], column_types: Dict[str, str]) -> None:
    if not rows:
        return
    # Build ordered column list (excluding id/created_at)
    columns = sorted(column_types.keys()) + ['data']
    placeholders = ",".join([":" + c for c in columns])
    sql = f"INSERT OR REPLACE INTO {table} (" + ",".join(columns) + ") VALUES (" + placeholders + ")"
    payload = []
    def _normalize_column_name(name: str) -> str:
        sanitized = ''.join(ch if (ch.isalnum() or ch == '_') else '_' for ch in name)
        if not sanitized:
            sanitized = 'col'
        if sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized.lower()

    for row in rows:
        item = {c: None for c in columns}
        normalized_row: Dict[str, Any] = {}
        for k, v in row.items():
            if k == 'data':
                continue
            normalized_row[_normalize_column_name(k)] = v
        for c in column_types.keys():
            val = normalized_row.get(c)
            val = _coerce_bool_to_int(val)
            item[c] = val
        item['data'] = row.get('data', json.dumps(row, separators=(',', ':'), ensure_ascii=False))
        payload.append(item)
    cur = conn.cursor()
    cur.executemany(sql, payload)


def build_uk_sqlite_db(
    db_path: Optional[pathlib.Path] = None,
    source_dir: Optional[pathlib.Path] = None,
) -> pathlib.Path:
    """
    Build a single SQLite database containing one table per UK JSON file.

    - Each JSON filename becomes a table (e.g., UB.json → UB).
    - Top-level scalar fields become columns; full record is stored in 'data' JSON.

    Returns the path to the created database file.
    """
    if source_dir is None:
        source_dir = pathlib.Path(__file__).parent / "sections" / "UK"
    if db_path is None:
        db_path = pathlib.Path(__file__).parent / "UK_sections.sqlite3"

    source_dir = source_dir.resolve()
    db_path = db_path.resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")

        for path in sorted(source_dir.glob("*.json")):
            if path.name.lower() in {"jsons.py", "lists.py"}:
                continue
            try:
                with path.open("r", encoding="utf-8") as f:
                    raw = json.load(f)
            except Exception as e:
                # Skip unreadable JSON files
                continue

            table = _sanitize_table_name(path.stem)

            rows = _flatten_rows_from_json(raw)
            if not rows:
                continue

            column_types = _collect_column_types(rows)
            _create_table(conn, table, column_types)
            _insert_rows(conn, table, rows, column_types)
        conn.commit()

    return db_path


if __name__ == "__main__":
    # Convenience CLI: python sqlite_driver.py will (re)build the UK DB
    built = build_uk_sqlite_db()
    print(f"Built UK sections database at: {built}")