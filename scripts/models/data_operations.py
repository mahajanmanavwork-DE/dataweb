import os
import json
import pandas as pd
from scripts.models.dataframe import Dataframe
from scripts import auth


class DataOperations(Dataframe):
    """
    Dataframe + all transformation methods.
    Every method returns a NEW DataOperations instance (immutable-style).
    """

    # ---------------------------------------------------------------
    #  VISIBLE DF
    # ---------------------------------------------------------------

    @property
    def visible_df(self) -> pd.DataFrame:
        df = self.df.copy()
        df = df.drop(
            columns=[c for c in self.deleted if c in df.columns],
            errors="ignore",
        )
        df = df.rename(
            columns={k: v for k, v in self.renamed.items() if k in df.columns}
        )
        return df

    @property
    def row_count(self) -> int:
        return len(self.df)

    # ---------------------------------------------------------------
    #  FILTER
    # ---------------------------------------------------------------

    def filter(self, column: str, operator: str, value: str,
               case_sensitive: bool = False) -> "DataOperations":
        original = self._visible_to_original(column)
        if original is None:
            raise ValueError(f"Unknown column: {column}")

        series = self.df[original]
        mask = self._build_mask(series, operator, value, case_sensitive)
        return self._spawn(self.df[mask].reset_index(drop=True))

    def _build_mask(self, series: pd.Series, operator: str, value: str,
                    case_sensitive: bool = False) -> pd.Series:
        is_string = pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)

        if operator in ("in", "not in"):
            items = self._parse_list(value)
            items = [self._coerce_value(series, v) for v in items]
            if is_string and not case_sensitive:
                low_items = [str(i).lower() for i in items]
                mask = series.astype(str).str.lower().isin(low_items)
            else:
                mask = series.isin(items)
            return mask if operator == "in" else ~mask

        coerced = self._coerce_value(series, value)

        if operator == "=":
            if is_string and not case_sensitive:
                return series.astype(str).str.lower() == str(coerced).lower()
            return series == coerced
        if operator == "!=":
            if is_string and not case_sensitive:
                return series.astype(str).str.lower() != str(coerced).lower()
            return series != coerced
        if operator == ">":  return series > coerced
        if operator == "<":  return series < coerced
        if operator == ">=": return series >= coerced
        if operator == "<=": return series <= coerced

        raise ValueError(f"Unsupported operator: {operator}")

    @staticmethod
    def _parse_list(value: str) -> list[str]:
        s = str(value).strip()
        if s.startswith("[") and s.endswith("]"):
            s = s[1:-1]
        items = [v.strip().strip('"').strip("'") for v in s.split(",")]
        return [i for i in items if i != ""]

    # ---------------------------------------------------------------
    #  GROUP BY / ORDER BY
    # ---------------------------------------------------------------

    def group_by(self, by: list[str], aggs: dict[str, str]) -> "DataOperations":
        originals = {c: self._visible_to_original(c) for c in by}
        agg_originals = {self._visible_to_original(c): op for c, op in aggs.items()}

        missing = [c for c, o in originals.items() if o is None]
        if missing:
            raise ValueError(f"Unknown group-by columns: {missing}")

        grouped = self.df.groupby(list(originals.values())).agg(agg_originals)
        grouped = grouped.reset_index()

        if isinstance(grouped.columns, pd.MultiIndex):
            grouped.columns = [
                "_".join([str(p) for p in col if p]) for col in grouped.columns
            ]
        return self._spawn(grouped)

    def order_by(self, column: str, direction: str = "asc") -> "DataOperations":
        original = self._visible_to_original(column)
        if original is None:
            raise ValueError(f"Unknown column: {column}")

        ascending = direction.lower() != "desc"
        sorted_df = self.df.sort_values(
            by=original,
            ascending=ascending,
            na_position="last",
            kind="mergesort",
        ).reset_index(drop=True)
        return self._spawn(sorted_df)

    # ---------------------------------------------------------------
    #  DISTINCT
    # ---------------------------------------------------------------

    def distinct(self, keep: str = "first") -> "DataOperations":
        """
        Drop duplicate rows across ALL visible columns.
        keep: 'first' or 'last' — which occurrence to keep.
        Only visible columns (not deleted) count toward uniqueness.
        """
        if keep not in ("first", "last"):
            keep = "first"

        visible_cols = [c for c in self.df.columns if c not in self.deleted]
        deduped = (
            self.df.drop_duplicates(subset=visible_cols, keep=keep)
            .reset_index(drop=True)
        )
        return self._spawn(deduped)

    # ---------------------------------------------------------------
    #  LIMIT / OFFSET
    # ---------------------------------------------------------------

    def limit(self, n: int) -> "DataOperations":
        return self._spawn(self.df.head(n).reset_index(drop=True))

    def offset(self, n: int) -> "DataOperations":
        return self._spawn(self.df.iloc[n:].reset_index(drop=True))

    # ---------------------------------------------------------------
    #  SHARED HELPERS
    # ---------------------------------------------------------------

    def _spawn(self, new_df: pd.DataFrame) -> "DataOperations":
        current_order = [c for c in self.df.columns if c in new_df.columns]
        leftover = [c for c in new_df.columns if c not in current_order]
        new_df = new_df[current_order + leftover]

        return DataOperations(
            df=new_df,
            source_file=self.source_file,
            renamed=dict(self.renamed),
            deleted=list(self.deleted),
        )

    def _visible_to_original(self, visible: str) -> str | None:
        if visible in self.df.columns:
            return visible
        for original, renamed in self.renamed.items():
            if renamed == visible:
                return original
        return None

    def _coerce_value(self, series: pd.Series, value):
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return value
        s = str(value).strip()
        try:
            if pd.api.types.is_bool_dtype(series):
                low = s.lower()
                if low in ("true", "1", "yes", "y"):
                    return True
                if low in ("false", "0", "no", "n"):
                    return False
            if pd.api.types.is_integer_dtype(series):
                return int(s)
            if pd.api.types.is_float_dtype(series):
                return float(s)
            if pd.api.types.is_datetime64_any_dtype(series):
                return pd.to_datetime(s)
        except (ValueError, TypeError):
            return s
        return s

    # ---------------------------------------------------------------
    #  CURRENT  — applies the user's delete + rename + order to self.df
    # ---------------------------------------------------------------

    @classmethod
    def current(cls, user: str) -> "DataOperations":
        key = auth.get_current_key(user)
        if not key:
            raise RuntimeError("No active Dataframe. Open a file first.")

        base = Dataframe.load(key)

        renamed = {}
        deleted = []
        order = []

        ops_by_file = auth.get_operations(user)
        if base.source_file:
            entry = ops_by_file.get(base.source_file, {})
            renamed = entry.get("rename", {}) or {}
            deleted = entry.get("delete", []) or []
            order = entry.get("order", []) or []

        df = base.df
        if order:
            ordered_cols = [c for c in order if c in df.columns]
            leftover_cols = [c for c in df.columns if c not in ordered_cols]
            df = df[ordered_cols + leftover_cols]

        return cls(
            df=df,
            key=base.key,
            source_file=base.source_file,
            renamed=renamed,
            deleted=deleted,
        )
        
    def group_by_multi(self, by: list[str], aggs: list[dict]) -> "DataOperations":
        """
        by:   list of visible column names, in user-chosen order.
        aggs: list of {"col": visible_col, "func": agg_name, "alias": str or None}
        """
        if not by:
            raise ValueError("Select at least one group-by column.")
        if not aggs:
            raise ValueError("Add at least one aggregation.")

        original_by = []
        for c in by:
            orig = self._visible_to_original(c)
            if orig is None:
                raise ValueError(f"Unknown group-by column: {c}")
            if orig not in original_by:
                original_by.append(orig)

        original_aggs = []
        seen_pairs = set()
        for a in aggs:
            col_vis = a.get("col")
            func = a.get("func")
            alias = (a.get("alias") or "").strip()

            orig = self._visible_to_original(col_vis)
            if orig is None:
                raise ValueError(f"Unknown aggregation column: {col_vis}")
            if func not in ("sum", "mean", "min", "max", "count", "median", "first", "last"):
                raise ValueError(f"Unsupported aggregation: {func}")

            pair = (orig, func)
            if pair in seen_pairs:
                raise ValueError(f"Duplicate aggregation: {col_vis} {func}")
            seen_pairs.add(pair)

            original_aggs.append({
                "col": orig,
                "func": func,
                "alias": alias or f"{col_vis}_{func}",
            })

        used_aliases = set(original_by)
        final_aggs = []
        for a in original_aggs:
            name = a["alias"]
            base = name
            i = 1
            while name in used_aliases:
                i += 1
                name = f"{base}_{i}"
            used_aliases.add(name)
            final_aggs.append({**a, "alias": name})

        grouped = self.df.groupby(original_by, sort=False, as_index=False).agg(
            **{a["alias"]: (a["col"], a["func"]) for a in final_aggs}
        )
        return self._spawn(grouped)
    
    def join(self, other_df: pd.DataFrame, left_on: str, right_on: str,
             how: str = "inner") -> "DataOperations":
        original_left = self._visible_to_original(left_on) or left_on
        merged = self.df.merge(
            other_df, left_on=original_left,
            right_on=right_on, how=how, suffixes=("", "_right")
        )
        merged = merged.reset_index(drop=True)
        return self._spawn(merged)

    def window_function(
        self,
        new_col_name: str,
        func: str,
        func_col: str = "",
        offset: int = 1,
        n_tiles: int = 2,
        partition_cols: list | None = None,
        order_col: str = "",
        order_dir: str = "asc",
        frame_start: str = "unbounded_preceding",
        frame_end: str = "current_row",
        frame_start_n: int = 1,
        frame_end_n: int = 1,
    ) -> "DataOperations":
        import numpy as np

        base = new_col_name.strip()
        if not base:
            raise ValueError("Provide a name for the new column.")

        used = set(self.cols)
        name = base
        i = 1
        while name in used:
            i += 1
            name = f"{base}_{i}"

        partition_orig = []
        for c in (partition_cols or []):
            if not c:
                continue
            orig = self._visible_to_original(c)
            if orig is None:
                raise ValueError(f"Unknown partition column: {c}")
            if orig not in partition_orig:
                partition_orig.append(orig)

        order_orig = ""
        if order_col:
            order_orig = self._visible_to_original(order_col)
            if order_orig is None:
                raise ValueError(f"Unknown order column: {order_col}")

        func_col_orig = ""
        if func_col:
            func_col_orig = self._visible_to_original(func_col)
            if func_col_orig is None:
                raise ValueError(f"Unknown column: {func_col}")

        ranking = {"row_number", "rank", "dense_rank", "ntile"}
        offset_fns = {"lag", "lead"}
        agg_fns = {"sum", "count", "min", "max"}

        if func not in ranking | offset_fns | agg_fns:
            raise ValueError(f"Unsupported window function: {func}")
        if func in ranking and not order_orig:
            raise ValueError("ORDER BY is required for ranking functions.")
        if func in offset_fns | agg_fns and not func_col_orig:
            raise ValueError(f"Column is required for {func}.")

        asc = order_dir != "desc"
        result = self.df.copy()
        result["__orig_order__"] = np.arange(len(result))

        if order_orig:
            sort_cols = list(partition_orig) + [order_orig]
            sort_asc  = [True] * len(partition_orig) + [asc]
            result = result.sort_values(
                by=sort_cols, ascending=sort_asc, kind="mergesort"
            )

        def _compute(sub: pd.DataFrame) -> pd.Series:
            n = len(sub)

            if func == "row_number":
                return pd.Series(np.arange(1, n + 1), index=sub.index, dtype="Int64")

            if func == "rank":
                return sub[order_orig].rank(method="min").astype("Int64")

            if func == "dense_rank":
                return sub[order_orig].rank(method="dense").astype("Int64")

            if func == "ntile":
                N = max(1, int(n_tiles or 2))
                ranks = sub[order_orig].rank(method="first").to_numpy()
                order_idx = ranks.argsort()
                tiles = np.empty(n, dtype="int64")
                for bucket_i, idxs in enumerate(np.array_split(np.arange(n), N), start=1):
                    tiles[order_idx[idxs]] = bucket_i
                return pd.Series(tiles, index=sub.index, dtype="Int64")

            if func == "lag":
                return sub[func_col_orig].shift(int(offset or 1))

            if func == "lead":
                return sub[func_col_orig].shift(-int(offset or 1))

            s = sub[func_col_orig]

            if not order_orig:
                val = getattr(s, func)()
                return pd.Series([val] * n, index=sub.index)

            if frame_start == "unbounded_preceding" and frame_end == "current_row":
                rolled = getattr(s.expanding(), func)()
            else:
                start_n = int(frame_start_n or 1)
                end_n   = int(frame_end_n or 1)
                window = max(1, start_n + end_n + 1)
                rolled = getattr(s.rolling(window=window, min_periods=1), func)()
            return rolled

        if partition_orig:
            result[name] = (
                result.groupby(partition_orig, sort=False, group_keys=False)
                      .apply(_compute)
            )
        else:
            result[name] = _compute(result)

        # ORDER BY used → keep the sorted row order.
        # Otherwise → restore original row order.
        if order_orig:
            result = result.drop(columns="__orig_order__").reset_index(drop=True)
        else:
            result = result.sort_values("__orig_order__").drop(columns="__orig_order__")
            result = result.reset_index(drop=True)

        ordered_cols = [c for c in self.df.columns if c in result.columns]
        leftover = [c for c in result.columns if c not in ordered_cols]
        result = result[ordered_cols + leftover]

        return self._spawn(result)