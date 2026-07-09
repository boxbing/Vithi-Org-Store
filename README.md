# Vithi Organics Storefront

This repository is a hybrid storefront with two runtimes:

- Primary runtime (source of truth): Python in `server.py` with templates in `templates/` and `admin/templates/`
- Secondary runtime (UI/reference/testing support): Node in `server.js` with views in `views/`

All production feature work should be validated against the Python runtime first.

## Runtime governance

- Do not treat Node output as the functional baseline for production behavior.
- Preserve Python routes, session/auth behavior, and persistence as canonical behavior.
- Use the runtime check commands below before debugging feature issues.

## Run the primary app (Python)

```bash
cd /home/sonu/Projects/Vithi-Org-Store
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python server.py
```

Then open `http://127.0.0.1:8000/` in your browser.

If you see `OSError: [Errno 98] Address already in use`, another copy of the app is already running on port 8000. Stop the existing `server.py` process or run with a different port, for example `PORT=8001 ./.venv/bin/python server.py`.

## Run the secondary app (Node, optional)

```bash
npm install
npm run start:node
```

Default Node port is `8001` to avoid clashing with Python on `8000`.

## Runtime checks (drift guard)

Use these commands when behavior seems different across environments:

```bash
# Which process is serving port 8000 (expected: python server.py)
lsof -i :8000

# Which process is serving port 8001 (optional node runtime)
lsof -i :8001

# Quick Python storefront check
curl -i http://localhost:8000/
```

If Python is not serving `8000`, start it before validating feature behavior.

## PostgreSQL

Set `DATABASE_URL` before starting the server if you want database-backed persistence:

```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/vithi
./.venv/bin/python server.py
```

Current behavior:

- If PostgreSQL is reachable, registrations and orders are stored in PostgreSQL.
- If PostgreSQL is not reachable, the app falls back to `data/users.json` and `data/orders.json`.

## Drift removal policy

- New UI changes should be integrated into Python templates first.
- Node view updates should not remove or redefine existing Python behavior.
- When adding UX blocks, keep existing Python template variables and form endpoints unchanged.
- Validate key flows in Python after UI edits: login, register, category, product, cart, wishlist, orders.

## Features

- Shared header/footer using templates
- Login and registration flows
- PostgreSQL-backed persistence for users and orders, with JSON fallback
- Product detail pages and cart/wishlist routes

## NPM scripts

- `npm start` starts Python runtime for convenience in mixed teams.
- `npm run start:node` starts Node runtime for reference/testing.
- `npm test` runs Node-side cart tests.

## Data files

- `data/users.json` — stored user accounts
- `data/orders.json` — stored order records
