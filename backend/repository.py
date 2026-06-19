import json
import sqlite3


SCHEMA_TABLES = {
    "scenic_spot",
    "chat_record",
    "route_record",
    "knowledge_document",
    "feedback_record",
    "persona_config",
}


def connect_database(db_path):
    connection = sqlite3.connect(db_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode = MEMORY")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def quote_table_name(table_name):
    if table_name not in SCHEMA_TABLES:
        raise ValueError(f"非法数据表名：{table_name}")
    return f'"{table_name}"'


def column_names(connection, table_name):
    rows = connection.execute(f"PRAGMA table_info({quote_table_name(table_name)})").fetchall()
    return {row["name"] for row in rows}


def add_column_if_missing(connection, table_name, column_name, definition):
    if column_name not in column_names(connection, table_name):
        connection.execute(f"ALTER TABLE {quote_table_name(table_name)} ADD COLUMN {column_name} {definition}")


def execute_in_clause(connection, sql_prefix, values, prefix_params=()):
    if not values:
        return
    placeholders = ",".join("?" for _ in values)
    connection.execute(f"{sql_prefix} ({placeholders})", tuple(prefix_params) + tuple(values))


def safe_json_loads(value, default):
    try:
        return json.loads(value) if value else default
    except (TypeError, json.JSONDecodeError):
        return default
