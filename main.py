import os 
import json
import dotenv
from fastapi import FastAPI, Request, Body, Form, Depends
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from scripts.pandas_operations.transformations import pandas_preview
from scripts.pandas_operations.metadata_functions import (
    parse_folder, clear_metadata, read_metadata,
    initialize_operations, clear_operations, initialize_df_registry,
    clear_storage, read_log, append_log, clear_log, read_history,
    flush_session_to_history,
)
from scripts.models.operations import rem_cols, column_operations, get_open_file_data
from scripts.models.data_operations import DataOperations
# import init_project; init_project
from scripts import auth

dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "env", ".env"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Resolve relative input/output paths to project root
for k in ("input_folder", "output_folder", "storage_folder", "metadata_path", "df_registry_path", "operations_path", "current_df_key_path", "users_path"):
    v = os.getenv(k)
    if v and not os.path.isabs(v):
        os.environ[k] = os.path.join(BASE_DIR, v)

app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("secret_key", "dev-secret"),
    same_site="lax",
    https_only=False,
    session_cookie="dw_session",
)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
first_session = True

initialize_operations()
clear_storage()
initialize_df_registry()
auth.ensure_default_admin()


class NotLoggedIn(Exception):
    pass


@app.exception_handler(NotLoggedIn)
def not_logged_in_handler(request: Request, exc: NotLoggedIn):
    return RedirectResponse("/login", status_code=303)


def current_user(request: Request) -> str | None:
    return request.session.get("user")


def require_user(request: Request) -> str:
    user = current_user(request)
    if not user:
        raise NotLoggedIn()
    return user


def _visible_columns(user: str, filename: str) -> tuple[list, list]:
    return get_open_file_data(user, filename)


# -----------------------------------------------------------------
#  LOGIN / LOGOUT / SIGNUP
# -----------------------------------------------------------------

@app.get("/login", include_in_schema=False)
def login_page(request: Request):
    if current_user(request):
        return RedirectResponse("/home", status_code=303)
    return templates.TemplateResponse(request, "login.html", {})


@app.post("/login", include_in_schema=False)
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if auth.verify_user(username, password):
        # fresh session on every login: clear old operations + pointers
        auth.reset_session(username)
        request.session["user"] = username
        append_log(username, "-", "Logged in")
        return RedirectResponse("/home", status_code=303)
    return templates.TemplateResponse(
        request, "login.html", {"error": "Invalid username or password."}
    )


@app.get("/logout", include_in_schema=False)
def logout(request: Request):
    user = current_user(request) or "-"
    append_log(user, "-", "Logged out")
    flush_session_to_history(user)     # feed -> history, then clear feed
    auth.reset_session(user)           # <-- NEW: clear per-user operations + pointers
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.post("/signup", include_in_schema=False)
def signup_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if not auth.create_user(username, password):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Username already exists."}
        )
    request.session["user"] = username
    append_log(username, "-", "Signed up")
    return RedirectResponse("/home", status_code=303)


# -----------------------------------------------------------------
#  Derived Column Endpoint (optimal)
# -----------------------------------------------------------------
@app.get("/derive")
def derive_page(request: Request, user: str = Depends(require_user)):
    return templates.TemplateResponse(request, "operations/derive.html", {"result": None, "active": "derive"})

@app.post("/derive_column")
async def derive_post(request: Request, user: str = Depends(require_user),
                       old_col: str = Form(""), new_col: str = Form(...),
                       op: str = Form("pct_up"), val: str = Form("")):
    result = f"{op} on '{old_col or 'blank'}' -> '{new_col}'"
    return templates.TemplateResponse(request, "derived.html", {"result": result})

# -----------------------------------------------------------------
#  Footer slot helper
# -----------------------------------------------------------------

def render_slots(request: Request, user: str, active: str | None, extra: dict | None = None):
    ctx = {
        "active": active,
        "columns": rem_cols(user),
        "operations": column_operations(),
        "row_count": None,
        "default_name": None,
        "output_folder": os.getenv("output_folder"),
    }
    if extra:
        ctx.update(extra)
    return templates.TemplateResponse(request, "operations/footer_slots.html", ctx)


# -----------------------------------------------------------------
#  Preview / info / home / scan / open
# -----------------------------------------------------------------

@app.get("/preview/{filename}", name='preview')
def preview(request: Request, filename, user: str = Depends(require_user)):
    filepath = os.path.join(os.getenv('input_folder'), filename)  # type: ignore
    file_df = pandas_preview(filepath)
    df = file_df.to_html(classes="preview-table", index=False)
    return templates.TemplateResponse(request, "file_preview.html", {"filename": filename, "df": df})


@app.get("/info", include_in_schema=False)
def info(request: Request, user: str = Depends(require_user)):
    return templates.TemplateResponse(request, "info.html")


@app.get("/", include_in_schema=False)
@app.get("/home", include_in_schema=False)
def root(request: Request, source: str = 'home', user: str = Depends(require_user)):
    global first_session
    if first_session:
        clear_storage()
        clear_metadata()
        first_session = False
        return templates.TemplateResponse(request, "files.html", {"files_content": {}, "opened_file": None, "username": user})
    if source == 'home':
        data = read_metadata()
        return templates.TemplateResponse(request, "files.html", {"files_content": data, "opened_file": None, "username": user})
    clear_storage()
    clear_metadata()
    return templates.TemplateResponse(request, "files.html", {"files_content": {}, "opened_file": None, "username": user})


@app.get("/scan")
def scan_folder(request: Request, user: str = Depends(require_user)):
    clear_operations()
    parse_folder()

    # fresh session: wipe the user's renames / deletes / order
    auth.reset_session(user)

    clear_log(user)
    append_log(user, "-", "Scanned folder")

    metadata_path = os.getenv("metadata_path")
    with open(metadata_path, "r") as f:  # type: ignore
        files_content = json.load(f)
    return templates.TemplateResponse(
        request, "files.html",
        {"files_content": files_content, "opened_file": None, "home": "False", "username": user}
    )


@app.get("/open/{filename}", name='open')
def open_file(request: Request, filename: str, default=True, user: str = Depends(require_user)):
    auth.set_selected_file(user, filename)
    DataOperations.from_file(filename).promote(user)

    clear_log(user)
    append_log(user, filename, f"Opened {filename}")

    filtered_columns, filtered_dtypes = _visible_columns(user, filename)

    metadata_path = os.getenv("metadata_path")
    with open(metadata_path, "r") as f:  # type: ignore
        files_content = json.load(f)

    return templates.TemplateResponse(
        request, "opening_file.html",
        {
            "filename": filename,
            "files_content": files_content,
            "column_names": filtered_columns,
            "column_dtypes": filtered_dtypes,
            "default": default,
            "operations_log": read_log(user),
        }
    )


@app.get("/operations/{name}")
def make_operations(request: Request, name: str, user: str = Depends(require_user)):
    filename = auth.get_selected_file(user) or ""
    filtered_columns, filtered_dtypes = _visible_columns(user, filename)
    metadata_path = os.getenv("metadata_path")
    with open(metadata_path, "r") as f:  # type: ignore
        files_content = json.load(f)
    return templates.TemplateResponse(
        request, "dynamic_operations.html",
        {
            "filename": filename,
            "files_content": files_content,
            "column_names": filtered_columns,
            "column_dtypes": filtered_dtypes,
            "times": [1],
            "columns": [1, 2, 5, 7, 8]
        }
    )


# -----------------------------------------------------------------
#  Reorder / delete / rename
# -----------------------------------------------------------------

@app.post("/reorder/{filename}")
def reorder_columns(filename: str, new_order: list[dict] = Body(...), user: str = Depends(require_user)):
    metadata_path = os.getenv("metadata_path")
    with open(metadata_path, "r") as f:  # type: ignore
        metadata = json.load(f)
    original_columns = metadata[filename]["columns"]

    ops = auth.get_operations(user)
    entry = ops.get(filename, {})
    renamed = entry.get("rename", {}) or {}

    def visible_to_original(v: str) -> str:
        for orig, vis in renamed.items():
            if vis == v:
                return orig
        return v

    original_order = [visible_to_original(item["column"]) for item in new_order]
    for c in original_columns:
        if c not in original_order:
            original_order.append(c)

    if filename not in ops:
        ops[filename] = {}
    ops[filename]["order"] = original_order
    auth.set_operations(user, ops)

    append_log(user, filename, f"Reordered columns: {', '.join(item['column'] for item in new_order)}")
    return {"status": "success"}


@app.post("/delete/{filename}")
def delete_column(request: Request, filename: str, column: str = Form(...), user: str = Depends(require_user)):
    metadata_path = os.getenv("metadata_path")
    with open(metadata_path, "r") as f:  # type: ignore
        metadata = json.load(f)

    ops = auth.get_operations(user)
    if filename not in ops:
        ops[filename] = {}
    if "delete" not in ops[filename]:
        ops[filename]["delete"] = []

    rename_map = ops[filename].get("rename", {})
    original_column = next((old for old, new in rename_map.items() if new == column), column)

    if original_column in metadata[filename]["columns"]:
        if original_column not in ops[filename]["delete"]:
            ops[filename]["delete"].append(original_column)

    auth.set_operations(user, ops)
    append_log(user, filename, f"Deleted column: {column}")

    column_names, column_dtypes = get_open_file_data(user, filename)
    return templates.TemplateResponse(
        request, "opening_file.html",
        {
            "filename": filename,
            "column_names": column_names,
            "column_dtypes": column_dtypes,
            "operations_log": read_log(user),
        }
    )


@app.post("/rename/{filename}")
def rename_column(request: Request, filename: str, old_name: str = Form(...), new_name: str = Form(...), user: str = Depends(require_user)):
    metadata_path = os.getenv("metadata_path")
    with open(metadata_path, "r") as f:  # type: ignore
        metadata = json.load(f)

    ops = auth.get_operations(user)
    if filename not in ops:
        ops[filename] = {}
    if "rename" not in ops[filename]:
        ops[filename]["rename"] = {}

    rename_map = ops[filename]["rename"]

    original = None
    if old_name in metadata[filename]["columns"]:
        original = old_name
    else:
        for orig, vis in rename_map.items():
            if vis == old_name:
                original = orig
                break
    if original is None:
        original = old_name

    rename_map.pop(old_name, None)
    rename_map[original] = new_name

    auth.set_operations(user, ops)
    append_log(user, filename, f"Renamed '{old_name}' → '{new_name}'")

    column_names, column_dtypes = get_open_file_data(user, filename)
    return templates.TemplateResponse(
        request, "opening_file.html",
        {
            "filename": filename,
            "column_names": column_names,
            "column_dtypes": column_dtypes,
            "operations_log": read_log(user),
        }
    )


# -----------------------------------------------------------------
#  Filter / Limit / Offset / Order By / Write
# -----------------------------------------------------------------

@app.get("/filter")
def filter_operation(request: Request, user: str = Depends(require_user)):
    return render_slots(request, user, "filter")


@app.post("/filter-operation")
def filtered_operation(request: Request, col_name: str = Form(...), operator: str = Form(...), filter_value: str = Form(...), case_sensitive: str = Form("false"), user: str = Depends(require_user)):
    case_flag = case_sensitive.lower() == "true"
    before = DataOperations.current(user)
    rows_before = len(before.df)
    before.filter(col_name, operator, filter_value, case_sensitive=case_flag).promote(user)
    after = DataOperations.current(user)
    rows_after = len(after.df)
    filename = auth.get_selected_file(user) or "-"
    append_log(user, filename, f"Filter: {col_name} {operator} {filter_value} ({rows_before} → {rows_after} rows)")

    return render_slots(request, user, "filter", {
        "rows_before": rows_before,
        "rows_after": rows_after,
        "diff": rows_before - rows_after,
    })


@app.get("/limit")
def limit_form(request: Request, user: str = Depends(require_user)):
    return render_slots(request, user, "limit", {"row_count": DataOperations.current(user).row_count})


@app.post("/limit-operation")
def limit_operation(request: Request, n: str = Form(...), user: str = Depends(require_user)):
    current = DataOperations.current(user)
    total = current.row_count
    filename = auth.get_selected_file(user) or "-"

    try:
        n_int = int(n)
    except (ValueError, TypeError):
        return render_slots(request, user, "limit", {"error": f"'{n}' is not a valid integer.", "row_count": total})

    if n_int < 1:
        return render_slots(request, user, "limit", {"error": "Limit must be at least 1.", "row_count": total})

    if n_int > total:
        return render_slots(request, user, "limit", {"error": f"Limit cannot exceed {total} rows.", "row_count": total})

    current.limit(n_int).promote(user)
    append_log(user, filename, f"Limit {n_int} rows ({total} → {n_int})")

    return render_slots(request, user, "limit", {
        "rows_before": total, "rows_after": n_int,
        "diff": total - n_int, "row_count": total,
    })


@app.get("/offset")
def offset_form(request: Request, user: str = Depends(require_user)):
    return render_slots(request, user, "offset", {"row_count": DataOperations.current(user).row_count})


@app.post("/offset-operation")
def offset_operation(request: Request, n: str = Form(...), user: str = Depends(require_user)):
    current = DataOperations.current(user)
    total = current.row_count
    filename = auth.get_selected_file(user) or "-"

    try:
        n_int = int(n)
    except (ValueError, TypeError):
        return render_slots(request, user, "offset", {"error": f"'{n}' is not a valid integer.", "row_count": total})

    if n_int < 0:
        return render_slots(request, user, "offset", {"error": "Offset must be 0 or greater.", "row_count": total})

    if n_int >= total:
        return render_slots(request, user, "offset", {"error": f"Offset must be less than {total} rows.", "row_count": total})

    current.offset(n_int).promote(user)
    rows_after = total - n_int
    append_log(user, filename, f"Offset {n_int} rows ({total} → {rows_after})")

    return render_slots(request, user, "offset", {
        "rows_before": total, "rows_after": rows_after,
        "diff": n_int, "row_count": total,
    })


@app.get("/orderby")
def orderby_form(request: Request, user: str = Depends(require_user)):
    return render_slots(request, user, "orderby")


@app.post("/orderby-operation")
def orderby_operation(request: Request, column: str = Form(...), direction: str = Form("asc"), user: str = Depends(require_user)):
    columns = rem_cols(user)
    current = DataOperations.current(user)
    total = current.row_count
    filename = auth.get_selected_file(user) or "-"

    if column not in columns:
        return render_slots(request, user, "orderby", {"error": f"Unknown column: {column}"})

    direction = direction.lower()
    if direction not in ("asc", "desc"):
        return render_slots(request, user, "orderby", {"error": f"Invalid direction: {direction}"})

    if total == 0:
        return render_slots(request, user, "orderby", {"error": "No rows to sort."})

    try:
        current.order_by(column, direction).promote(user)
    except Exception as e:
        return render_slots(request, user, "orderby", {"error": f"Sort failed: {e}"})

    append_log(user, filename, f"Order by {column} {direction}")

    return render_slots(request, user, "orderby", {
        "row_count": total, "column": column, "direction": direction,
    })


@app.get("/write")
def write_form(request: Request, user: str = Depends(require_user)):
    filename = auth.get_selected_file(user) or "output"
    stem = filename.rsplit(".", 1)[0] if filename else "output"
    current = DataOperations.current(user)
    cols = list(current.visible_df.columns) if hasattr(current, 'visible_df') and current.visible_df is not None else rem_cols(user)
    return render_slots(request, user, "write", {"default_name": f"{stem}_output", "columns": cols})


@app.post("/write-operation")
def write_operation(file_name: str = Form(...), file_format: str = Form(...), selected_cols: list[str] = Form([]), user: str = Depends(require_user)):
    output_folder = os.getenv("output_folder")
    os.makedirs(output_folder, exist_ok=True)  # type: ignore

    df = DataOperations.current(user).visible_df
    if selected_cols:
        df = df[selected_cols]
    else:
        # If nothing selected, use all visible columns
        selected_cols = list(df.columns)
    # Ensure we don't write empty dataframe
    if df.empty or len(df.columns) == 0:
        return Response(status_code=400, content="No columns selected or no data.")
    full_path = os.path.join(output_folder, f"{file_name}.{file_format}")  # type: ignore

    if file_format == "csv":
        df.to_csv(full_path, index=False)
    elif file_format == "parquet":
        df.to_parquet(full_path, index=False)
    elif file_format == "json":
        df.to_json(full_path, orient="records", indent=2)
    elif file_format == "xlsx":
        df.to_excel(full_path, index=False)
    else:
        return Response(status_code=400)

    append_log(user, auth.get_selected_file(user) or "-", f"Wrote {file_name}.{file_format}")
    return Response(status_code=204)


@app.get("/join")
def join_form(request: Request, user: str = Depends(require_user)):
    metadata_path = os.getenv("metadata_path")
    with open(metadata_path, "r") as f:
        files_content = json.load(f)
    right_columns = []
    join_file = request.query_params.get("join_file", "")
    if join_file:
        try:
            right_path = os.path.join(os.getenv("input_folder"), join_file)  # type: ignore
            right_df = pandas_preview(right_path)
            right_columns = list(right_df.columns)
        except:
            pass
    return render_slots(request, user, "join", {
        "files_content": files_content,
        "filename": auth.get_selected_file(user) or "",
        "right_columns": right_columns,
        "columns": rem_cols(user),
        "pairs": [{"left":"","right":""}],
        "join_file": join_file,
        "join_type": "inner",
        "right_file": join_file,
    })

@app.post("/join-operation")
async def join_operation(request: Request, user: str = Depends(require_user)):
    form = await request.form()
    action = form.get("action", "")
    current = DataOperations.current(user)
    filename = auth.get_selected_file(user) or "-"
    join_file = form.get("join_file", "")
    left_col = form.get("left_col", "")
    right_col = form.get("right_col", "")
    join_type = form.get("join_type", "inner")
    metadata_path = os.getenv("metadata_path")
    with open(metadata_path, "r") as f:
        files_content = json.load(f)
    right_columns = []
    if join_file:
        try:
            right_path = os.path.join(os.getenv("input_folder"), join_file)
            right_df = pandas_preview(right_path)
            right_columns = list(right_df.columns)
        except:
            pass
    if not left_col or not right_col:
        return render_slots(request, user, "join", {
            "join_file": join_file, "join_type": join_type,
            "files_content": files_content, "filename": filename,
            "right_file": join_file, "columns": rem_cols(user),
            "right_columns": right_columns, "error": "Select at least one key pair.",
        })
    left_col_use = left_col
    right_col_use = right_col
    if not join_file:
        return render_slots(request, user, "join", {"error": "Select a file to join."})
    try:
        right_path = os.path.join(os.getenv("input_folder"), join_file)  # type: ignore
        right_df = pandas_preview(right_path)
        rows_before = current.row_count
        current.join(right_df, left_col_use, right_col_use, how=join_type or "inner").promote(user)
        after = DataOperations.current(user)
        rows_after = after.row_count
        append_log(user, filename, f"Join: {filename}[{left_col_use}] + {join_file}[{right_col_use}] {join_type or 'inner'} → {rows_after} rows")
        return render_slots(request, user, "join", {
            "rows_after": rows_after, "rows_before": rows_before,
            "left_file": filename, "right_file": join_file,
            "left_col": left_col_use, "right_col": right_col_use,
            "join_type": join_type,
            "files_content": files_content, "filename": filename,
            "right_columns": right_columns,
            "columns": rem_cols(user),
        })
    except Exception as e:
        return render_slots(request, user, "join", {
            "join_file": join_file,
            "join_type": join_type,
            "files_content": files_content,
            "filename": filename,
            "right_file": join_file,
            "columns": rem_cols(user),
            "right_columns": right_columns,
            "error": f"Join failed: {e}",
        })

@app.get("/join-file-columns")
def join_file_columns(request: Request, join_file: str = "", user: str = Depends(require_user)):
    columns = []
    if join_file:
        try:
            right_path = os.path.join(os.getenv("input_folder"), join_file)  # type: ignore
            right_df = pandas_preview(right_path)
            columns = list(right_df.columns)
        except:
            pass
    return templates.TemplateResponse(request, "operations/join_right_col.html", {"columns": columns})

@app.get("/close-slot")
def close_slot(request: Request, user: str = Depends(require_user)):
    return render_slots(request, user, None)


@app.get("/notepad")
def notepad(request: Request, user: str = Depends(require_user)):
    filename = auth.get_selected_file(user) or "-"
    return templates.TemplateResponse(
        request, "operations/notepad.html",
        {"filename": filename, "operations_log": read_log(user)}
    )


@app.post("/clear-log/{filename}")
def clear_log_route(request: Request, filename: str, user: str = Depends(require_user)):
    clear_log(user)
    append_log(user, filename, "Cleared operations log")
    return templates.TemplateResponse(
        request, "operations/notepad.html",
        {"filename": filename, "operations_log": read_log(user)}
    )



@app.get("/distinct")
def distinct_form(request: Request, user: str = Depends(require_user)):
    return render_slots(request, user, "distinct")


@app.post("/distinct-operation")
def distinct_operation(request: Request, keep: str = Form("first"), user: str = Depends(require_user)):
    current = DataOperations.current(user)
    rows_before = current.row_count
    filename = auth.get_selected_file(user) or "-"

    try:
        current.distinct(keep=keep).promote(user)
    except Exception as e:
        return render_slots(request, user, "distinct", {
            "error": f"Distinct failed: {e}",
        })

    after = DataOperations.current(user)
    rows_after = after.row_count
    diff = rows_before - rows_after

    append_log(user, filename,
               f"Distinct ({keep}): {rows_before} → {rows_after} rows"
               + ("" if diff else " (all rows unique)"))

    return render_slots(request, user, "distinct", {
        "rows_before": rows_before,
        "rows_after": rows_after,
        "diff": diff,
    })
    
AGG_FUNCS = ["sum", "mean", "min", "max", "count", "median", "first", "last"]
WINDOW_FUNCS = [
    "row_number", "rank", "dense_rank", "ntile",
    "lag", "lead",
    "sum", "count", "min", "max",
]


# -----------------------------------------------------------------
#  GROUP BY  (stateless: all state travels through the form)
# -----------------------------------------------------------------

def _groupby_ctx(user: str, group_cols, agg_rows, error=None, **extra):
    ctx = {
        "columns": rem_cols(user),
        "agg_functions": AGG_FUNCS,
        "group_cols": group_cols,
        "agg_rows": agg_rows,
        "error": error,
    }
    ctx.update(extra)
    return ctx


def _render_groupby(request: Request, user: str, ctx: dict):
    return templates.TemplateResponse(
        request, "operations/footer_slots.html",
        {"active": "groupby", "operations": column_operations(),
         "row_count": None, "default_name": None,
         "output_folder": os.getenv("output_folder"), **ctx}
    )


@app.get("/groupby")
def groupby_form(request: Request, user: str = Depends(require_user)):
    ctx = _groupby_ctx(
        user,
        group_cols=[""],
        agg_rows=[{"col": "", "func": "sum", "alias": ""}],
    )
    return _render_groupby(request, user, ctx)


@app.post("/groupby-edit")
async def groupby_edit(request: Request, user: str = Depends(require_user)):
    form = await request.form()

    action = form.get("action", "")

    # Read the incoming state
    group_cols = list(form.getlist("group_col"))
    agg_cols   = list(form.getlist("agg_col"))
    agg_funcs  = list(form.getlist("agg_func"))
    agg_aliases = list(form.getlist("agg_alias"))

    agg_rows = [
        {"col": agg_cols[i] if i < len(agg_cols) else "",
         "func": agg_funcs[i] if i < len(agg_funcs) else "sum",
         "alias": agg_aliases[i] if i < len(agg_aliases) else ""}
        for i in range(len(agg_cols))
    ]

    if not group_cols:
        group_cols = [""]
    if not agg_rows:
        agg_rows = [{"col": "", "func": "sum", "alias": ""}]

    # ---- Row mutations ----
    if action == "add_group":
        group_cols.append("")
    elif action == "add_agg":
        agg_rows.append({"col": "", "func": "sum", "alias": ""})
    elif action.startswith("remove_group:"):
        try:
            i = int(action.split(":", 1)[1])
            if 0 <= i < len(group_cols):
                group_cols.pop(i)
                if not group_cols:
                    group_cols = [""]
        except ValueError:
            pass
    elif action.startswith("remove_agg:"):
        try:
            i = int(action.split(":", 1)[1])
            if 0 <= i < len(agg_rows):
                agg_rows.pop(i)
                if not agg_rows:
                    agg_rows = [{"col": "", "func": "sum", "alias": ""}]
        except ValueError:
            pass

    # ---- Apply ----
    if action == "apply":
        used_group_cols = [c for c in group_cols if c]
        used_aggs = [a for a in agg_rows if a["col"]]

        error = None
        if not used_group_cols:
            error = "Select at least one group-by column."
        elif not used_aggs:
            error = "Add at least one aggregation."
        elif len(used_group_cols) != len(set(used_group_cols)):
            error = "Group-by columns cannot repeat."
        else:
            seen = set()
            for a in used_aggs:
                key = (a["col"], a["func"])
                if key in seen:
                    error = f"Duplicate aggregation: {a['col']} {a['func']}"
                    break
                seen.add(key)

        if error:
            ctx = _groupby_ctx(user, group_cols, agg_rows, error=error)
            return _render_groupby(request, user, ctx)

        current = DataOperations.current(user)
        rows_before = current.row_count
        filename = auth.get_selected_file(user) or "-"

        try:
            current.group_by_multi(used_group_cols, used_aggs).promote(user)
        except Exception as e:
            ctx = _groupby_ctx(user, group_cols, agg_rows, error=str(e))
            return _render_groupby(request, user, ctx)

        after = DataOperations.current(user)
        rows_after = after.row_count

        summary_group = ", ".join(used_group_cols)
        summary_aggs = ", ".join(f"{a['func']}({a['col']})" for a in used_aggs)
        append_log(user, filename,
                   f"Group by [{summary_group}] → {summary_aggs} "
                   f"({rows_before} → {rows_after} groups)")

        ctx = _groupby_ctx(
            user, group_cols, agg_rows,
            rows_before=rows_before,
            rows_after=rows_after,
            summary_group=summary_group,
            summary_aggs=summary_aggs,
        )
        return _render_groupby(request, user, ctx)

    # ---- add/remove → just re-render ----
    ctx = _groupby_ctx(user, group_cols, agg_rows)
    return _render_groupby(request, user, ctx)



# -----------------------------------------------------------------
#  WINDOW FUNCTION  (stateless, all state in the form)
# -----------------------------------------------------------------

def _window_defaults():
    return {
        "new_col_name": "",
        "func": "row_number",
        "func_col": "",
        "offset": 1,
        "n_tiles": 2,
        "partition_cols": [""],
        "order_col": "",
        "order_dir": "asc",
        "frame_start": "unbounded_preceding",
        "frame_end": "current_row",
        "frame_start_n": 1,
        "frame_end_n": 1,
    }


def _window_ctx(user: str, state: dict, error=None, summary=None):
    ctx = {
        "columns": rem_cols(user),
        "funcs": WINDOW_FUNCS,
        "error": error,
        "summary": summary,
        **state,
    }
    return ctx


def _render_window(request: Request, user: str, ctx: dict):
    return templates.TemplateResponse(
        request, "operations/footer_slots.html",
        {
            "active": "window",
            "operations": column_operations(),
            "row_count": None,
            "default_name": None,
            "output_folder": os.getenv("output_folder"),
            **ctx,
        }
    )


def _parse_window_form(form) -> dict:
    return {
        "new_col_name": (form.get("new_col_name") or "").strip(),
        "func": form.get("func") or "row_number",
        "func_col": form.get("func_col") or "",
        "offset": _safe_int(form.get("offset"), 1),
        "n_tiles": _safe_int(form.get("n_tiles"), 2),
        "partition_cols": list(form.getlist("partition_col")),
        "order_col": form.get("order_col") or "",
        "order_dir": (form.get("order_dir") or "asc").lower(),
        "frame_start": form.get("frame_start") or "unbounded_preceding",
        "frame_end": form.get("frame_end") or "current_row",
        "frame_start_n": _safe_int(form.get("frame_start_n"), 1),
        "frame_end_n": _safe_int(form.get("frame_end_n"), 1),
    }


def _safe_int(v, default):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


@app.get("/window")
def window_form(request: Request, user: str = Depends(require_user)):
    state = _window_defaults()
    return _render_window(request, user, _window_ctx(user, state))


@app.post("/window-edit")
async def window_edit(request: Request, user: str = Depends(require_user)):
    form = await request.form()
    action = form.get("action", "")

    state = _parse_window_form(form)

    if not state["partition_cols"]:
        state["partition_cols"] = [""]

    # Row mutations
    if action == "add_partition":
        state["partition_cols"].append("")
    elif action.startswith("remove_partition:"):
        try:
            i = int(action.split(":", 1)[1])
            if 0 <= i < len(state["partition_cols"]):
                state["partition_cols"].pop(i)
                if not state["partition_cols"]:
                    state["partition_cols"] = [""]
        except ValueError:
            pass

    # Apply
    if action == "apply":
        current = DataOperations.current(user)
        rows_before = current.row_count
        filename = auth.get_selected_file(user) or "-"

        try:
            current.window_function(**state).promote(user)
        except Exception as e:
            return _render_window(request, user, _window_ctx(user, state, error=str(e)))

        after = DataOperations.current(user)
        rows_after = after.row_count

        summary = (
            f"{state['func']}"
            + (f"({state['func_col']})" if state["func_col"] else "")
            + (f" partition by {', '.join(c for c in state['partition_cols'] if c)}"
               if any(state["partition_cols"]) else "")
            + (f" order by {state['order_col']} {state['order_dir']}"
               if state["order_col"] else "")
        )

        append_log(user, filename,
                   f"Window: {state['new_col_name']} = {summary} ({rows_after} rows)")

        ctx = _window_ctx(user, state, summary=summary)
        return _render_window(request, user, ctx)

    # add/remove → re-render
    return _render_window(request, user, _window_ctx(user, state))