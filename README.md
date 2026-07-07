# Vithi Organics Storefront

This project is a storefront with a Python backend that can persist users and orders in PostgreSQL, with JSON fallback when no PostgreSQL server is available.

## Run the app

```bash
cd /home/sonu/Projects/vithi-organics-homepage
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python server.py
```

Then open `http://127.0.0.1:8000/` in your browser.

If you see `OSError: [Errno 98] Address already in use`, another copy of the app is already running on port 8000. Stop the existing `server.py` process or run with a different port, for example `PORT=8001 ./.venv/bin/python server.py`.

## PostgreSQL

Set `DATABASE_URL` before starting the server if you want database-backed persistence:

```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/vithi
./.venv/bin/python server.py
```

Current behavior:

- If PostgreSQL is reachable, registrations and orders are stored in PostgreSQL.
- If PostgreSQL is not reachable, the app falls back to `data/users.json` and `data/orders.json`.

## Features

- Shared header/footer using templates
- Login and registration flows
- PostgreSQL-backed persistence for users and orders, with JSON fallback
- Product detail pages and cart/wishlist routes

## Data files

- `data/users.json` — stored user accounts
- `data/orders.json` — stored order records
