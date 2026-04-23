# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run from source:**
```bash
pip install -r requirements.txt
python app.py
```

**Build standalone executable:**
```bash
# Linux/macOS
pyinstaller --onefile --name sfera-kanban \
  --add-data "templates:templates" \
  --add-data "static:static" \
  --add-data "config/app.ini.example:config" \
  app.py

# Windows (PowerShell)
pyinstaller --onefile --name sfera-kanban `
  --add-data "templates;templates" `
  --add-data "static;static" `
  --add-data "config/app.ini.example;config" `
  app.py
```

Executable lands in `dist/`. A `config/app.ini` must exist next to the executable at runtime.

**Configuration setup:**
```bash
cp config/app.ini.example config/app.ini
# then edit config/app.ini with Sfera credentials
```

Config path override: `export SFERA_KANBAN_CONFIG=/path/to/app.ini`

There is no test suite.

## Architecture

Flask web app that fetches tasks from an internal Sfera API and displays them as a Kanban board.

### Data flow

1. User submits query form (`/`) with a label or date range
2. `POST /start-fetch` spawns a background thread (tracked in `fetch_jobs` dict)
3. Thread calls `sfera_api.generate_tasks_label()` or `generate_tasks_dates()`:
   - Authenticates via `POST /api/auth/login` → Bearer token
   - Paginates `GET /app/tasks/api/v1/entity-views`
   - Normalizes tasks and writes `tasks_dict.pickle`
   - Updates global `tasks` and `label_to_match` in `app.py`
4. Frontend polls `GET /fetch-status/<job_id>` until complete, then redirects to `/kanban`
5. `/kanban` groups tasks via `task_utils`, applies custom ordering from config, renders board

### Module responsibilities

- **`app.py`** — Flask routes, global state (`tasks`, `label_to_match`, `selected_area`, `last_fetch_params`), job queue with threading lock, sorting helpers, label string generation
- **`utils/app_config.py`** — Resolves and parses `config/app.ini`; exports constants (`APP_HOST`, `APP_PORT`, `SFERA_BASE_URL`, `SFERA_USERNAME`, `SFERA_PASSWORD`, `ASSIGNEE_ORDER`, `SYSTEM_ORDER`, etc.)
- **`utils/sfera_api.py`** — Sfera REST client; retry logic; task normalization (`_build_task()`); serializes result to `tasks_dict.pickle`
- **`utils/task_utils.py`** — `group_tasks_by_assignee()`, `group_tasks_by_system()`, `sort_tasks()` with status-priority mapping

### Key constraints

- **SSL verification is disabled** (`verify=False`) for all Sfera API requests — the target is an internal host (`tasks.example.local`) with a self-signed cert.
- **Global mutable state** (`tasks`, `label_to_match`, etc.) in `app.py` is shared across requests without per-request isolation; concurrent fetches use a lock only on `fetch_jobs`.
- Kanban status columns are hardcoded in Russian: `Создано, Анализ, В очереди, В работе, В ожидании, Выполнено, Закрыто`.
- Frontend JavaScript and CSS (`static/script.js`, `static/style.css`) are currently empty; all logic lives inline in the Jinja2 templates.
