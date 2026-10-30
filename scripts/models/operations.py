import json 
import dotenv 
import os 

from scripts import auth

dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "env", ".env"))


def _active_df(user: str):
    from scripts.models.data_operations import DataOperations
    try:
        return DataOperations.current(user)
    except RuntimeError:
        return None


def _visible_cols_and_dtypes(user: str) -> tuple[list, list]:
    """
    Columns and dtypes as the user sees them right now:
      1. Start from the active df's columns.
      2. Drop any the user deleted.
      3. Apply the user's rename map for display.
      4. Preserve the user's column order.
    Dtypes: prefer the original metadata.json for original columns,
    fall back to pandas for new columns (group by, joins).
    """
    current = _active_df(user)
    if current is None:
        return [], []

    source = current.source_file
    meta_dtypes: dict[str, str] = {}
    if source:
        try:
            with open(os.getenv("metadata_path"), "r") as f:  # type: ignore
                meta = json.load(f).get(source, {})
            meta_dtypes = dict(zip(meta.get("columns", []), meta.get("dtypes", [])))
        except (json.JSONDecodeError, OSError, TypeError):
            meta_dtypes = {}

    ops_by_file = auth.get_operations(user)
    entry = ops_by_file.get(source, {}) if source else {}
    deleted = entry.get("delete", []) or []
    renamed = entry.get("rename", {}) or {}
    order   = entry.get("order", []) or []

    # 1. base columns in current df order
    kept = [c for c in current.df.columns if c not in deleted]

    # 2. reorder (only for columns that still exist)
    if order:
        ordered = [c for c in order if c in kept]
        leftovers = [c for c in kept if c not in ordered]
        kept = ordered + leftovers

    # 3. rename for display
    visible = [renamed.get(c, c) for c in kept]
    dtypes = [
        meta_dtypes.get(c, str(current.df.dtypes[c]))
        for c in kept
    ]

    return visible, dtypes


def rem_cols(user: str) -> list:
    cols, _ = _visible_cols_and_dtypes(user)
    return cols


def column_operations():
    return ["=", "!=", ">", "<", ">=", "<=", "in", "not in"]


def get_open_file_data(user: str, filename: str) -> tuple[list, list]:
    return _visible_cols_and_dtypes(user)