import os 
import dotenv
import json
import pandas as pd
from datetime import datetime

dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "env", ".env"))


def clear_metadata():
    metadata_file = os.getenv('metadata_path')
    selected_filepath = os.getenv("selected_filepath")
    metadata = {}
    with open(metadata_file, 'w') as f:  # type: ignore
        json.dump(metadata, f, indent=4)
    with open(selected_filepath, "w") as f:  # type: ignore
        pass


def read_metadata():
    metadata_file = os.getenv('metadata_path')
    with open(metadata_file, 'r') as f:  # type: ignore
        data = json.load(f)
    return data


def check_extension(files):
    if len(files) == 0:
        return
    else:
        valid_extensions = ['csv', 'json', 'parquet', 'xlsx', 'xls']
        valid_files = []
        for file in files:
            file_ext = file.split('.')[-1]
            if file_ext in valid_extensions:
                valid_files.append(file)
        parse_files(valid_files)
        return


def parse_files(files):
    metadata_file = os.getenv('metadata_path')
    metadata = {}
    for i in range(len(files)):
        file = files[i]
        filepath = os.path.join(os.getenv('input_folder'), file)  # type: ignore
        if filepath.split(".")[-1] == "csv":
            df = pd.read_csv(filepath, nrows=5)
        elif filepath.split(".")[-1] == "parquet":
            df = pd.read_parquet(filepath)
        elif filepath.split(".")[-1] == "json":
            try:
                df = pd.read_json(filepath, lines=True, nrows=5)
            except Exception as e:
                df = pd.read_json(filepath)
        elif filepath.split(".")[-1] == "xlsx" or filepath.split(".")[-1] == "xls":
            df = pd.read_excel(filepath, nrows=5)
        columns = dataframe_column(df)
        dtypes = dataframe_types(df)
        metadata[f"{file}"] = {
            "file_type": file.split('.')[-1],
            "columns": columns,
            "dtypes": dtypes
        }
    with open(metadata_file, 'w') as f:  # type: ignore
        json.dump(metadata, f, indent=4)


def parse_folder():
    input_folder = os.getenv('input_folder')
    files = os.listdir(input_folder)
    check_extension(files)


def dataframe_column(df):
    return df.columns.tolist()


def dataframe_types(df):
    return df.dtypes.astype(str).tolist()


def initialize_operations():
    operations_file = os.getenv("operations_path")
    if not os.path.exists(operations_file):  # type: ignore
        with open(operations_file, "w") as f:  # type: ignore
            json.dump({}, f, indent=4)
    clear_operations()


def clear_operations():
    operations_file = os.getenv("operations_path")
    with open(operations_file, "w") as f:  # type: ignore
        json.dump({}, f, indent=4)


def initialize_df_registry():
    registry_path = os.getenv("df_registry_path")
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)  # type: ignore
    if not os.path.exists(registry_path):  # type: ignore
        with open(registry_path, "w") as f:  # type: ignore
            json.dump({}, f, indent=4)


def clear_storage():
    storage_folder = os.getenv("storage_folder")
    registry_path = os.getenv("df_registry_path")
    key_path = os.getenv("current_df_key_path")

    if storage_folder and os.path.exists(storage_folder):
        for name in os.listdir(storage_folder):
            full = os.path.join(storage_folder, name)
            if os.path.isfile(full) and name.endswith(".parquet"):
                try:
                    os.remove(full)
                except OSError:
                    pass

    os.makedirs(os.path.dirname(registry_path), exist_ok=True)  # type: ignore
    with open(registry_path, "w") as f:  # type: ignore
        json.dump({}, f, indent=4)

    with open(key_path, "w") as f:  # type: ignore
        f.write("")


# ---------------------------------------------------------------
#  LOGS
# ---------------------------------------------------------------

def _user_log_path(user: str) -> str:
    folder = os.getenv("storage_folder")
    safe = "".join(c for c in (user or "_") if c.isalnum() or c in ("-", "_")) or "_"
    return os.path.join(folder, f"log_{safe}.json")  # type: ignore


def _history_path() -> str:
    return os.path.join(os.getenv("storage_folder"), "history.json")  # type: ignore


def _read_json_list(path: str) -> list:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write_json_list(path: str, data: list) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def read_log(user: str = "admin") -> list:
    return _read_json_list(_user_log_path(user))


def read_history() -> list:
    return _read_json_list(_history_path())


def append_log(user: str, filename: str, operation: str):
    """Append to the user's feed AND to the permanent history."""
    entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user or "-",
        "file": filename or "-",
        "op": operation,
    }

    feed = _read_json_list(_user_log_path(user))
    feed.append(entry)
    _write_json_list(_user_log_path(user), feed)

    hist = _read_json_list(_history_path())
    hist.append(entry)
    _write_json_list(_history_path(), hist)


def clear_log(user: str = "admin"):
    """Clear only the user's live feed — history untouched."""
    _write_json_list(_user_log_path(user), [])


def flush_session_to_history(user: str):
    """
    On logout: copy any leftover entries from the user's feed into
    history.json (so nothing is lost), then clear the feed.
    Entries were already appended to history when created, so this
    only re-adds ones that somehow got out of sync — dedup by
    (time, user, file, op).
    """
    feed = _read_json_list(_user_log_path(user))
    if not feed:
        _write_json_list(_user_log_path(user), [])
        return

    hist = _read_json_list(_history_path())
    seen = {(e.get("time"), e.get("user"), e.get("file"), e.get("op")) for e in hist}

    for entry in feed:
        key = (entry.get("time"), entry.get("user"), entry.get("file"), entry.get("op"))
        if key not in seen:
            hist.append(entry)
            seen.add(key)

    _write_json_list(_history_path(), hist)
    _write_json_list(_user_log_path(user), [])