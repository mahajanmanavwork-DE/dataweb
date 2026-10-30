import os
import json
import uuid
import dotenv
import pandas as pd
from scripts import auth

dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))


class Dataframe:
    """
    Wraps a pandas DataFrame with:
      - disk-backed storage (parquet)
      - a shared registry (key → path)
      - a stable 'key' used to look it up later
    The active snapshot is tracked per user in metadata/users.json.
    """

    def __init__(self, df: pd.DataFrame,
                 key: str | None = None,
                 source_file: str | None = None,
                 renamed: dict | None = None,
                 deleted: list | None = None):

        self.df = df
        self.key = key or self._new_key()
        self.source_file = source_file
        self.renamed = renamed or {}
        self.deleted = deleted or []

        os.makedirs(os.getenv("storage_folder"), exist_ok=True)  # type: ignore

    @staticmethod
    def _new_key() -> str:
        return uuid.uuid4().hex[:12]

    @property
    def path(self) -> str:
        folder = os.getenv("storage_folder")
        return os.path.join(folder, f"{self.key}.parquet")  # type: ignore

    @property
    def cols(self) -> list[str]:
        visible = []
        for col in self.df.columns:
            if col in self.deleted:
                continue
            visible.append(self.renamed.get(col, col))
        return visible

    # ---------------------------------------------------------------
    #  SAVE
    # ---------------------------------------------------------------

    def save(self) -> str:
        self.df.to_parquet(self.path, index=False)
        self._update_registry()
        return self.key

    def _update_registry(self):
        registry_path = os.getenv("df_registry_path")
        if os.path.exists(registry_path):  # type: ignore
            with open(registry_path, "r") as f:  # type: ignore
                registry = json.load(f)
        else:
            registry = {}

        registry[self.key] = {
            "path": self.path,
            "source_file": self.source_file,
            "cols": self.cols,
            "renamed": self.renamed,
            "deleted": self.deleted,
        }

        with open(registry_path, "w") as f:  # type: ignore
            json.dump(registry, f, indent=4)

    # ---------------------------------------------------------------
    #  LOAD
    # ---------------------------------------------------------------

    @classmethod
    def load(cls, key: str) -> "Dataframe":
        registry_path = os.getenv("df_registry_path")
        with open(registry_path, "r") as f:  # type: ignore
            registry = json.load(f)

        if key not in registry:
            raise KeyError(f"No Dataframe registered for key={key}")

        entry = registry[key]
        path = entry.get("path", "")
        if os.path.isabs(path):
            folder = os.getenv("storage_folder")
            path = os.path.join(folder, os.path.basename(path))
        df = pd.read_parquet(path)

        return cls(
            df=df,
            key=key,
            source_file=entry.get("source_file"),
            renamed=entry.get("renamed", {}),
            deleted=entry.get("deleted", []),
        )

    # ---------------------------------------------------------------
    #  CURRENT  (per-user)
    # ---------------------------------------------------------------

    @classmethod
    def current(cls, user: str) -> "Dataframe":
        """
        Load the Dataframe currently active for `user`.
        Reads the key from that user's session block in users.json.
        """
        key = auth.get_current_key(user)
        if not key:
            raise RuntimeError("No active Dataframe. Open a file first.")
        return cls.load(key)

    def promote(self, user: str) -> "Dataframe":
        """
        Save this Dataframe and set it as the active one for `user`.
        Save this Dataframe and set it as the active one for `user`.
        """
        self.save()
        auth.set_current_key(user, self.key)
        return self

    @classmethod
    def from_file(cls, filename: str, file_type: str | None = None) -> "Dataframe":
        input_folder = os.getenv("input_folder")
        filepath = os.path.join(input_folder, filename)  # type: ignore

        ext = (file_type or filename.split(".")[-1]).lower()

        if ext == "csv":
            df = pd.read_csv(filepath)
        elif ext == "parquet":
            df = pd.read_parquet(filepath)
        elif ext == "json":
            try:
                df = pd.read_json(filepath, lines=True)
            except ValueError:
                df = pd.read_json(filepath)
        elif ext in ("xlsx", "xls"):
            df = pd.read_excel(filepath)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        instance = cls(df=df, source_file=filename)
        instance.save()
        return instance