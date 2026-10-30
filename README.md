# UI-Based SQL / Data Operations Platform

A FastAPI web application that lets users interact with CSV, JSON, Parquet, and Excel files through a visual UI — applying SQL-like operations (filter, limit, offset, group by, window functions, order by, rename, delete, reorder, distinct, write) without writing raw SQL queries.

## Who This Is For (Best Fit)

- Data analysts and students who need quick data exploration without a full database setup.
- Small teams or labs that want a lightweight server-deployed file-processing interface.
- Educators teaching SQL concepts through a guided visual form (group-by, window functions, filtering) mapped to pandas operations.
- Organizations that want an internal, authorized-access server tool for non-technical users to process structured files securely.

## Deployment & Authorization

This project is designed to run as a server application:
- User authentication (signup/login/logout) with session-based access control.
- Per-user session state and operations tracking (history, logs, selected files).
- Role-friendly: only authorized users can open, transform, and export data files.
- Deploy with `main.py` (FastAPI) behind a reverse proxy or container; `.env` paths resolve relative to file location for portability.

## Key Features

- File scanning and preview
- Column rename, delete, reorder
- Filter, limit, offset, order by, distinct
- Multi-column group-by with aggregations (sum, mean, min, max, count, median, first, last)
- Window functions (row_number, rank, lag, lead, tiles, frames)
- Export to CSV, JSON, Parquet, Excel
- Operation history and per-user logs

## Tech Stack

- Python, FastAPI, Jinja2 templates
- Pandas for data processing
- dotenv for environment config (portable paths)
- Session middleware for authorization

## Usage (Server)

1. Configure `.env` with `input_folder`, `output_folder`, `metadata_path`, etc.
2. Run: `python main.py` (or deploy with Uvicorn/Gunicorn).
3. Access via browser; sign up/log in to use files.
