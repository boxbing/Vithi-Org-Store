---
description: "Use when editing code, templates, deployment config, or docs in this repository; preserves the hybrid Python/Node eCommerce stack, JSON/PostgreSQL fallback, and deployment conventions."
applyTo: ["server.py", "server.js", "requirements.txt", "package.json", "README.md", "styles.css", "script.js", "templates/**", "views/**", "admin/**", "data/**"]
---
# Repository Conventions

- Treat this repository as a hybrid storefront: `server.py` is the Python backend entrypoint, `server.js` is the Node/Express entrypoint, and `templates/`, `views/`, `admin/`, and the static assets work together as one storefront.
- Prefer the smallest change that fixes the root cause.
- Keep runtime behavior backward compatible unless a breaking change is explicitly requested.
- Preserve PostgreSQL support and JSON fallback paths when touching persistence, authentication, or order flows.
- Keep secrets and credentials in environment variables; do not hardcode them into source, templates, or sample data.
- When updating deployment or startup behavior, keep `README.md`, scripts, and server entrypoints aligned.
- Reuse existing partials, template structure, and CSS patterns rather than inventing a new layout system unless the task calls for a redesign.
- Validate with the narrowest meaningful check available after editing.
