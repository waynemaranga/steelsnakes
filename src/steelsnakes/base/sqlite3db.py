from __future__ import annotations
import logging
from abc import ABC
from pathlib import Path
import json
import sqlite3
from typing import Any, Optional, Iterable


logger: logging.Logger = logging.getLogger(__name__)


# 🪶SQLite JSON Interface
class SQLiteJSONInterface:
    """Interface for converting JSON steel section data to SQLite database.
    Handles the conversion of JSON files containing steel section data into
    optimized SQLite tables with dynamic schema and indexing.
    """
    
    def __init__(self, db_path: Path):
        self.db_path: Path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
    def convert_directory(self, source_dir: Path) -> Path:
        """Convert all JSON files in a directory to SQLite database.
        source_dir: Directory containing JSON files to convert
        Returns: Path to the created SQLite database
        Raises: ValueError: If source directory doesn't exist
        and RuntimeError: If database creation fails"""

        if not source_dir.exists() or not source_dir.is_dir():
            raise ValueError(f"Source directory does not exist: {source_dir}")
            
        source_dir = source_dir.resolve()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Configure SQLite for optimal performance
                conn.execute("PRAGMA foreign_keys = ON;")
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA synchronous = NORMAL;")
                
                json_files = list(source_dir.glob("*.json"))
                if not json_files:
                    logger.warning(f"No JSON files found in {source_dir}")
                    return self.db_path
                
                logger.info(f"Converting {len(json_files)} JSON files to SQLite")
                
                for json_path in sorted(json_files):
                    # Skip non-data files
                    if json_path.name.lower() in {"jsons.py", "lists.py"}:
                        continue
                        
                    self._convert_json_file(conn, json_path)
                    
                conn.commit()
                logger.info(f"Successfully created SQLite database: {self.db_path}")
                
        except Exception as e:
            logger.error(f"Failed to create SQLite database: {e}")
            raise RuntimeError(f"Database creation failed: {e}") from e
            
        return self.db_path
    
    def _convert_json_file(self, conn: sqlite3.Connection, json_path: Path) -> None:
        """Convert a single JSON file to a SQLite table. Takes conn: SQLite connection
        and json_path: Path to JSON file to convert"""

        try:
            with json_path.open("r", encoding="utf-8") as f:
                raw_data = json.load(f)
                
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Skipping invalid JSON file {json_path}: {e}")
            return
        except Exception as e:
            logger.error(f"Error reading {json_path}: {e}")
            return
            
        table_name = self._sanitize_table_name(json_path.stem)
        logger.debug(f"Converting {json_path.name} -> table '{table_name}'")
        
        # Convert JSON structure to rows
        rows = self._flatten_json_to_rows(raw_data)
        if not rows:
            logger.warning(f"No data rows extracted from {json_path}")
            return
            
        # Analyze data to determine schema
        column_types = self._analyze_column_types(rows)
        
        # Create table and insert data
        self._create_table(conn, table_name, column_types)
        self._insert_rows(conn, table_name, rows, column_types)
        
        logger.debug(f"Inserted {len(rows)} rows into table '{table_name}'")
    
    def get_section(self, table_name: str, designation: str) -> Optional[dict[str, Any]]:
        """Retrieve a section by table and designation. Takes table_name: Name of the table (section type)
        and designation: Section designation to find. Returns: Section data dictionary or None if not found"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Use parameterized query (table name needs to be sanitized separately)
                safe_table = self._sanitize_table_name(table_name)
                query = f"SELECT * FROM {safe_table} WHERE designation = ? LIMIT 1"
                
                result = cursor.execute(query, (designation,)).fetchone()
                
                if result:
                    # Convert Row to dict and parse JSON data
                    section_dict = dict(result)
                    if 'data' in section_dict and section_dict['data']:
                        try:
                            section_dict['parsed_data'] = json.loads(section_dict['data'])
                        except json.JSONDecodeError:
                            pass
                    return section_dict
                    
        except sqlite3.Error as e:
            logger.error(f"Database error retrieving section {designation} from {table_name}: {e}")
        except Exception as e:
            logger.error(f"Error retrieving section {designation}: {e}")
            
        return None
    
    def list_tables(self) -> list[str]:
        """List all tables in the SQLite database.
        Returns: list of table names"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error listing tables: {e}")
            return []
    
    def search_sections(self, table_name: str, **criteria) -> list[dict[str, Any]]:
        """Search for sections in a table based on criteria.
        Takes table_name: Name of the table to search and **criteria: Search criteria as column=value pairs
        Returns: list of matching section dictionaries"""
        
        if not criteria:
            return []
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                safe_table = self._sanitize_table_name(table_name)
                
                # Build WHERE clause safely
                conditions = []
                values = []
                for key, value in criteria.items():
                    safe_key = self._normalize_column_name(key)
                    conditions.append(f"{safe_key} = ?")
                    values.append(value)
                
                where_clause = " AND ".join(conditions)
                query = f"SELECT * FROM {safe_table} WHERE {where_clause}"
                
                results = cursor.execute(query, values).fetchall()
                
                return [dict(row) for row in results]
                
        except sqlite3.Error as e:
            logger.error(f"Database error searching {table_name}: {e}")
        except Exception as e:
            logger.error(f"Error searching sections: {e}")
            
        return []

    # Helper methods for data processing
    
    @staticmethod
    def _sanitize_table_name(name: str) -> str:
        """Convert filename to safe SQLite table name."""
        safe = ''.join(ch if ch.isalnum() or ch == '_' else '_' for ch in name)
        return safe.upper() if safe else 'TABLE'
    
    @staticmethod
    def _normalize_column_name(name: str) -> str:
        """Normalize column name to SQLite-safe format."""
        sanitized = ''.join(ch if (ch.isalnum() or ch == '_') else '_' for ch in name)
        if not sanitized or sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized.lower()
    
    @staticmethod
    def _is_scalar(value: Any) -> bool:
        """Check if value is a scalar type suitable for column storage."""
        return isinstance(value, (str, int, float, bool)) or value is None
    
    @staticmethod
    def _coerce_bool_to_int(value: Any) -> Any:
        """Convert boolean values to integers for SQLite storage."""
        return int(value) if isinstance(value, bool) else value
    
    def _infer_sql_type(self, values: Iterable[Any]) -> str:
        """Infer SQLite column type from sample values."""
        seen_text = seen_real = seen_int = False
        
        for v in values:
            if v is None:
                continue
            elif isinstance(v, bool):
                seen_int = True
            elif isinstance(v, int):
                seen_int = True
            elif isinstance(v, float):
                seen_real = True
            elif isinstance(v, str):
                seen_text = True
            else:
                seen_text = True  # Fallback to TEXT
                
        # Return most restrictive applicable type
        if seen_text:
            return "TEXT"
        elif seen_real:
            return "REAL"
        elif seen_int:
            return "INTEGER"
        else:
            return "TEXT"
    
    def _flatten_json_to_rows(self, data: Any) -> list[dict[str, Any]]:
        """
        Convert JSON data structure to list of row dictionaries.
        
        Handles various JSON structures:
        - {designation -> properties}
        - {category -> {designation -> properties}}
        - Arrays of objects
        - Single objects
        """
        rows: list[dict[str, Any]] = []
        
        if isinstance(data, dict):
            values = list(data.values())
            
            # Check if this looks like {designation -> properties}
            if values and all(isinstance(v, dict) for v in values):
                for key, props in data.items():
                    if isinstance(props, dict) and props and all(isinstance(v2, dict) for v2 in props.values()):
                        # Category -> {designation -> properties}
                        category = key
                        for sub_key, sub_props in props.items():
                            row = self._create_row_from_dict(sub_props, category, sub_key)
                            rows.append(row)
                    else:
                        # designation -> properties
                        row = self._create_row_from_dict(props, designation=key)
                        rows.append(row)
            else:
                # Single object with scalar values
                row = self._create_row_from_dict(data)
                rows.append(row)
                
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                if isinstance(item, dict):
                    row = self._create_row_from_dict(item, designation=f"ITEM_{idx}")
                else:
                    row = {
                        'designation': f"ITEM_{idx}",
                        'value': item,
                        'data': json.dumps(item, separators=(',', ':'), ensure_ascii=False)
                    }
                rows.append(row)
        else:
            # Single scalar value
            rows.append({
                'designation': 'ITEM',
                'value': data,
                'data': json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            })
            
        return rows
    
    def _create_row_from_dict(self, props: dict[str, Any], category: Optional[str] = None, designation: Optional[str] = None) -> dict[str, Any]:
        """Create a database row from a properties dictionary."""
        row: dict[str, Any] = {}
        
        # Extract scalar values as columns
        for key, value in props.items():
            if self._is_scalar(value):
                row[key] = value
                
        # Store full object as JSON
        row['data'] = json.dumps(props, separators=(',', ':'), ensure_ascii=False)
        
        # Set category if provided
        if category:
            row['category'] = category
            
        # Determine designation
        if designation:
            row['designation'] = str(designation)
        elif 'designation' in props:
            row['designation'] = str(props['designation'])
        elif category and designation:
            row['designation'] = f"{category}:{designation}"
        else:
            row['designation'] = 'ITEM'
            
        return row
    
    def _analyze_column_types(self, rows: list[dict[str, Any]]) -> dict[str, str]:
        """Analyze rows to determine optimal column types."""
        samples: dict[str, list[Any]] = {}
        
        for row in rows:
            for key, value in row.items():
                if key != 'data' and self._is_scalar(value):
                    normalized_key = self._normalize_column_name(key)
                    samples.setdefault(normalized_key, []).append(value)
        
        # Ensure designation column exists
        samples.setdefault('designation', []).append('')
        
        return {col: self._infer_sql_type(vals) for col, vals in samples.items()}
    
    def _create_table(self, conn: sqlite3.Connection, table_name: str, column_types: dict[str, str]) -> None:
        """Create SQLite table with dynamic schema."""
        columns = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
        
        # Add columns in sorted order for consistency
        for col_name in sorted(column_types.keys()):
            if col_name == 'designation':
                columns.append("designation TEXT NOT NULL")
            else:
                columns.append(f"{col_name} {column_types[col_name]}")
        
        # Add standard columns
        columns.extend([
            "data TEXT",  # Full JSON object
            "created_at TEXT DEFAULT (datetime('now'))"
        ])
        
        # Create table and index
        create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
        index_sql = f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{table_name}_designation ON {table_name}(designation)"
        
        cursor = conn.cursor()
        cursor.execute(create_sql)
        cursor.execute(index_sql)
    
    def _insert_rows(self, conn: sqlite3.Connection, table_name: str, rows: list[dict[str, Any]], column_types: dict[str, str]) -> None:
        """Insert rows into SQLite table."""
        if not rows:
            return
            
        # Build column list and prepare SQL
        columns = sorted(column_types.keys()) + ['data']
        placeholders = ', '.join([f":{col}" for col in columns])
        sql = f"INSERT OR REPLACE INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        # Prepare data for insertion
        payload = []
        for row in rows:
            item = {col: None for col in columns}
            
            # Map row data to normalized columns
            for key, value in row.items():
                if key == 'data':
                    continue
                normalized_key = self._normalize_column_name(key)
                if normalized_key in column_types:
                    item[normalized_key] = self._coerce_bool_to_int(value)
            
            # Ensure data field is set
            item['data'] = row.get('data', json.dumps(row, separators=(',', ':'), ensure_ascii=False))
            payload.append(item)
        
        # Execute batch insert
        cursor = conn.cursor()
        cursor.executemany(sql, payload)



# 🪶 SQLite: Backwards compatibility function
def build_regional_sqlite_db(db_path: Path, source_dir: Path) -> Path:
    """Build SQLite database from JSON files in a directory.
    This function provides backwards compatibility with the old module.
    db_path: Path where SQLite database will be created.
    source_dir: Directory containing JSON files to convert
    Returns: Path to the created SQLite database
    """
    interface = SQLiteJSONInterface(db_path)
    return interface.convert_directory(source_dir)


if __name__ == "__main__":
    
    print("🐬")