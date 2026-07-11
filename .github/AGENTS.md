---
description: "Vithi Organics eCommerce Store — AI agent entry point with project overview, conventions, skills, and key documentation links. CRITICAL: Read SRS/LastStatus and inspect codebase BEFORE making changes. Never claim completion without testing."
---

# Vithi Organics Store — AI Agent Instructions

Welcome! This document serves as the entry point for AI coding agents working on the **Vithi Organics eCommerce Store**.

---

## 🚨 CRITICAL: Pre-Task Checklist

**EVERY task must begin with these steps — do not skip:**

1. ✅ **Read all relevant SRS documents**
   - [Product Listing & Detail Page SRS](../../productListingDetailFrontSRS.md) — for storefront work
   - [Admin Category Management SRS](../../categoryManageAdminSRS.md) — for admin panel work
   - Search for any `.SRS.md` or `SRS*.md` files in the workspace

2. ✅ **Read LastStatus.md**
   - [LastStatus.md](../../LastStatus.md) — understand what was last completed, known issues, and exact next step
   - This prevents duplicate work and identifies blockers

3. ✅ **Inspect the existing codebase**
   - Run the Python app: `python server.py` (primary runtime, port 8000)
   - Test the feature/flow you will be modifying by hand
   - Identify all affected routes, templates, API endpoints, data models
   - Check for existing implementation that may be partial or hidden
   - Read relevant code sections before deciding something is missing

4. ✅ **Preserve existing working functionality**
   - Do not modify behavior unless the SRS explicitly requires it
   - If a requirement conflicts with existing behavior, document the conflict and ask before changing
   - Test existing flows after your changes to ensure no regression

5. ✅ **Never claim completion without testing**
   - Happy path: User-facing flow works end-to-end
   - Error handling: Invalid input, empty states, and edge cases are handled
   - Regression: Existing major flows still operate
   - Platform parity: If Python + Node both exist, test both (Python first)
   - Mobile-responsive: UI looks correct on mobile, tablet, desktop

---

## Quick Project Overview

Vithi Organics Store is a **hybrid Python/Node eCommerce storefront** with:

- **Primary runtime (source of truth):** Python `server.py` with templates in `templates/` and `admin/templates/`
- **Secondary runtime (UI/reference):** Node `server.js` with views in `views/`
- **Data persistence:** PostgreSQL with JSON fallback (`data/*.json`)
- **Admin panel:** Category, brand, and product management with image uploads
- **Storefront features:** Product browsing, search, cart, wishlist, orders, reviews, SEO

**Key governance rule:** Python runtime is canonical for production behavior. Always validate against Python first.

See [README.md](../../README.md) for detailed setup, runtime checks, and feature list.

---

## 📋 Codebase Inspection Protocol

Before modifying any part of the codebase, inspect the existing implementation:

1. **Identify all affected files**
   - Frontend: `templates/*.html`, `views/*.ejs`, `styles.css`, `script.js`
   - Backend: `server.py`, `server.js`, routes, data models
   - Data: `data/*.json`, database schema (if PostgreSQL is used)
   - Admin: `admin/templates/*.html`, admin routes

2. **Find existing patterns**
   - Search for similar implementations (e.g., how is cart managed? how is search implemented?)
   - Reuse existing patterns unless there is a strong reason to change
   - Check if the feature is already partially implemented

3. **Run and test existing behavior**
   - Start the Python app: `python server.py` → `http://localhost:8000`
   - Manually test the flow or page you will modify
   - Document the current behavior before making changes
   - Verify what works and what's missing

4. **Check for hidden dependencies**
   - Database relationships (e.g., `Product.categoryId` → `Category.id`)
   - Session/auth requirements
   - Image upload directories and constraints
   - API contracts used by frontend or mobile clients
   - CSS class dependencies (modifying styles.css affects multiple pages)

5. **Document findings**
   - Note what exists, what's broken, what's missing
   - Identify the smallest change that solves the problem
   - Check for side effects or breaking changes before coding

---

## Running the App

### Python (primary, port 8000)
```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python server.py
```

### Node (secondary, port 8001)
```bash
npm install
npm run start:node
```

### Runtime checks (use when debugging)
```bash
# Which runtime is serving port 8000?
lsof -i :8000

# Quick storefront check
curl -i http://localhost:8000/
```

For detailed setup, see [README.md](../../README.md).

---

## Customization Files

### Core Instructions
- **[Repository Conventions](./instructions/ecommerce-platform-conventions.instructions.md)**  
  Hybrid stack governance, pattern reuse, PostgreSQL/JSON fallback, secret handling, backward compatibility.

### Skills (Specialized Workflows)
- **[vithi-ecommerce-delivery](./skills/vithi-ecommerce-delivery/SKILL.md)**  
  Full feature delivery workflow: SRS reading, implementation, validation, quality gates, completion tracking.

### Agents (Autonomous Teams)
- **[eCommerce Platform Architect](./agents/ecommerce-platform-architect.agent.md)**  
  Full-stack work: architecture, frontend/backend, API, database, DevOps, security, testing, monitoring.

### Repository Memory
- **[Runtime Notes](../..//memories/repo/runtime-notes.md)** *(in workspace memory)*  
  Technical details: test patterns, dependency versions, session architecture, admin CRUD behavior.

---

## Current Work & SRS Documents

Ongoing feature development is tracked in **SRS documents** and **LastStatus.md**:

- [Product Listing & Detail Page SRS](../../productListingDetailFrontSRS.md) — Storefront product pages (Phase 1 in progress)
- [Admin Category Management SRS](../../categoryManageAdminSRS.md) — Admin panel category CRUD
- [LastStatus.md](../../LastStatus.md) — Latest completed task, files modified, known issues, exact next step

**Before starting work:** Read the relevant SRS file and [LastStatus.md](../../LastStatus.md) to understand current scope and blockers.

---

## Key Project Facts

### Architecture & Data
- **User auth:** Session cookies (in-memory `sessions` dict in Python, Express middleware in Node)
- **Data models:** Users, Orders, Products, Categories, Brands, Reviews, Subscribers
- **Persistence:** Relational (`Product.categoryId` → `Category.id`, etc.)
- **Historical snapshots:** Orders preserve product/price snapshots at purchase time
- **Admin audit fields:** `createdAt`, `modifiedAt`, `createdBy`, `modifiedBy`

### Frontend & UX
- **CSS system:** Single `styles.css` with CSS variables (`--green-900`, `--gold`, `--muted`, etc.)
- **Template reuse:** Partials for header/footer; base templates for layout
- **Responsive:** Mobile-first, tested on mobile/tablet/desktop
- **Images:** Lazy loading, responsive sizes, WebP where applicable
- **SEO metadata:** Dynamic title, description, keywords, canonical, Open Graph, JSON-LD structured data

### Admin Features
- **Category CRUD:** Full admin panel with status toggle, image upload, SEO fields, ordering
- **Brand CRUD:** GST number, contact info, audit fields, status control
- **Product CRUD:** Stock, pricing, tax, media, SEO, related products
- **Search & filter:** Category-level search via query param `q`; ranking respects online/published status

### Security & Validation
- **Input validation:** Email, phone, GSTIN, website URL, password strength
- **Authorization:** Admin-only routes protected; user-only cart/wishlist/order operations
- **Image uploads:** Type/extension/size validation; stored in `assets/` subdirs
- **Secrets:** Environment variables only (`DATABASE_URL`, `ADMIN_PASSWORD`, `ADMIN_USERNAME`, `PORT`, `SITE_URL`)

### Production & Performance
- **Health checks:** Sitemap, robots.txt, 404/500 error pages
- **Logging:** HTTP requests, database operations (to stdout; no file log yet)
- **Caching:** Pagination, recently viewed, product recommendations
- **Fallback:** JSON files used if PostgreSQL unavailable (critical for dev/staging)

---

## 🏗️ Architecture Principles

Every change must adhere to these non-negotiable principles:

### API-First
- Routes return structured JSON responses for all operations (not just HTML)
- Frontend consumes JSON endpoints; templates render on server or client
- Admin operations use RESTful conventions (`GET /products`, `POST /products`, `PUT /products/:id`, `DELETE /products/:id`)
- Mobile clients will reuse these APIs in the future; design for that from day one

### Mobile-Responsive
- **Mobile-first CSS:** Base styles target mobile; media queries enhance for tablet/desktop
- **Touch-friendly:** Buttons and inputs are ≥44px; spacing is generous on small screens
- **Performance:** Lazy load images, minimize critical rendering path, use semantic HTML
- **Test on device:** Don't rely on browser dev tools alone; test on real mobile hardware or emulator

### SEO-Friendly
- **Dynamic metadata:** Every page has unique `<title>`, `<meta name="description">`, canonical URL
- **Structured data:** Product pages include JSON-LD `Product` schema; category pages include `BreadcrumbList`
- **URL structure:** Slugs are human-readable (`/product/turmeric-powder`, not `/product/123`)
- **Redirects:** 301 for permanent changes; 404 for removed content
- **Robots & sitemap:** Maintained at root; exclude admin/dev paths

### Secure
- **Input validation:** Every user-controlled input (form, query param, file) is validated
- **Authorization:** Admin routes check session; user routes check ownership
- **Secrets:** Never hardcode credentials; use environment variables only
- **XSS protection:** Template engines auto-escape; user content sanitized before storage
- **CSRF tokens:** Form submissions include CSRF protection where needed
- **File uploads:** Validate MIME type, extension, and size before storing

### Maintainable
- **DRY (Don't Repeat Yourself):** Reuse templates, CSS classes, utility functions
- **Single responsibility:** Each route/function has one clear purpose
- **Explicit over implicit:** Variable names are clear; logic is easy to follow
- **Backward compatible:** Breaking changes require explicit SRS approval and documentation
- **Well-tested:** Every new feature includes tests; no feature is "complete" without passing tests

---

## 🧪 Testing & Completion Requirements

**⚠️ No feature is complete without testing. Do not claim completion if any gate is skipped.**

### Mandatory Testing Before "Complete"

| Test Type | What to Verify | Example |
|-----------|------------------|---------|
| **Happy Path** | User-facing flow works end-to-end | "I can add a product to cart and checkout" |
| **Error Handling** | Invalid input/empty states are handled gracefully | "Empty search returns 'no results'; submitting without email shows validation error" |
| **Edge Cases** | Boundary conditions work correctly | "Out-of-stock product disables 'Add to Cart'; category with no products shows empty state" |
| **Regression** | Existing flows still work | "After adding new search filter, old category pages still load; cart still works" |
| **Platform Parity** | If both Python + Node exist, both behave consistently | Test Python first (primary); verify Node does not break |
| **Mobile Responsive** | UI is usable on mobile/tablet/desktop | Test on actual device or responsive emulator (not just browser dev tools) |
| **SEO** | Metadata is correct and indexable | Dynamic title/description appear in page source; canonical URL is set |
| **Authorization** | Unauthorized users cannot access restricted features | Non-admin cannot access `/admin/*`; users cannot edit other users' orders |
| **Data Integrity** | No broken relationships; no orphaned records | Deleting a category doesn't break products; order preserves snapshot data |
| **Performance** | Page loads quickly; no N+1 queries | Pagination works; large product lists don't cause timeouts |

### How to Test

1. **Manual testing (minimum)**
   - Use browser developer tools to inspect network requests and HTML
   - Test on mobile phone or emulator
   - Walk through all user flows in the task/SRS

2. **Automated testing (if applicable)**
   - Run existing test suite: `npm test` (Node tests) or `pytest tests/` (Python tests, if added)
   - Add new tests for new logic
   - Verify all tests pass before claiming completion

3. **Integration testing**
   - Test the feature with the database (PostgreSQL if available; JSON fallback otherwise)
   - Test with realistic data (not just minimal examples)
   - Test with empty/missing data (edge cases)

4. **Runtime checks**
   ```bash
   # Verify Python is serving port 8000
   lsof -i :8000
   
   # Check logs for errors
   curl -i http://localhost:8000/
   
   # Validate specific endpoint
   curl -i http://localhost:8000/product/my-product-slug
   ```

---

## 📊 Quality Gates & Validation Checklist

Use these gates for every meaningful feature or fix:

- ✅ **Functional:** Happy path works for target feature
- ✅ **Validation:** Invalid input and empty states handled
- ✅ **Authorization:** Unauthorized access blocked (admin ops)
- ✅ **Data integrity:** No broken relationships; existing flows unchanged
- ✅ **SEO:** Metadata, URL/slug behavior correct
- ✅ **Responsive UI:** Mobile/tablet/desktop acceptable
- ✅ **Error handling:** API/UI errors visible and non-breaking
- ✅ **Backward compatibility:** Existing major flows operate
- ✅ **Tests:** Relevant tests run; new tests added if needed

See [vithi-ecommerce-delivery SKILL](./skills/vithi-ecommerce-delivery/SKILL.md) for detailed delivery sequence and decision logic.

---

## Common Patterns & Where to Find Them

| Pattern | Location |
|---------|----------|
| Admin category form | `admin/templates/categories.html`, `server.py` route `/admin/categories` |
| Product detail page | `templates/product.html`, `server.py` route `/product/<slug>` |
| Cart operations | `server.py` routes `/cart/*`, session `carts` dict |
| Category search | `templates/category.html` query param `q` |
| Admin CRUD deletion | `server.py` checks for linked products before delete |
| Image upload | `server.py` validates extension/size in `/admin/categories` POST |
| Metadata/SEO | Python template context: `meta_title`, `og_image`, `structured_data_json` |
| Session management | `server.py` `sessions` dict, `admin_sessions` dict |

---

## Workflow: When to Use Each Skill/Agent

### 👤 **You are building a feature**
Use the **[vithi-ecommerce-delivery](./skills/vithi-ecommerce-delivery/SKILL.md)** skill:
- Read SRS and requirements first
- Identify affected layers (frontend, backend, API, database, auth, SEO, media)
- Implement modular changes using existing patterns
- Run quality gates; update LastStatus.md

### 🏗️ **You are refactoring, deploying, or planning architecture**
Use the **[eCommerce Platform Architect](./agents/ecommerce-platform-architect.agent.md)** agent:
- Analyze dependencies and risks
- Inspect existing codebase before changing
- Implement coordinated changes across layers
- Validate with focused tests and operational checks
- Update deployment and monitoring docs

### 📝 **You are updating code, templates, or config**
Follow **[Repository Conventions](./instructions/ecommerce-platform-conventions.instructions.md)**:
- Preserve Python as source of truth
- Reuse existing CSS/template patterns
- Keep JSON/PostgreSQL fallback paths intact
- Store secrets in environment variables only
- Keep README.md and server startup aligned

---

## 📝 LastStatus.md Update Requirements

**After every meaningful coding session, update [LastStatus.md](../../LastStatus.md) with:**

| Field | What to Include |
|-------|-----------------|
| **Date and Time** | When the session started and ended |
| **Current Branch** | Which branch you were working on (e.g., `main`, `feature/product-detail`) |
| **Latest Completed Task** | Brief 1-2 sentence summary of what was delivered |
| **Files Created** | List of new files added (e.g., `templates/product-not-found.html`) |
| **Files Modified** | List of files changed with brief note of what changed (e.g., `server.py: added /product-not-found route`) |
| **Database Migrations** | Any schema changes, new tables, migrations run (e.g., `ALTER TABLE products ADD COLUMN stock_quantity INT;`) |
| **APIs Added or Changed** | New/modified routes and their contracts (e.g., `POST /api/products returns {id, name, price}`) |
| **Tests Performed** | What was tested and on which runtime(s) (e.g., "Tested product detail page on Python; verified cart add works; mobile responsive tested on iPhone") |
| **Known Issues** | Any bugs, regressions, or incomplete work (e.g., "Quantity selector UI pending; image zoom not yet implemented") |
| **Pending Tasks** | What's next (e.g., "Implement Product Not Found page; add star distribution to reviews") |
| **Exact Recommended Next Step** | Very specific, actionable next task (e.g., "Create /product-not-found.html template and wire into 404 handler in server.py") |

**Format example:**
```markdown
## Date and Time
- 2026-07-10 10:00 – 2026-07-10 14:30

## Current Branch
- main

## Latest Completed Task
- Implemented Product Detail page with stock-aware cart, quantity support, and dynamic recommendations per SRS.

## Files Created
- None (modified existing templates)

## Files Modified
- server.py: added /product/<slug> route, product recommendation logic
- templates/product.html: added breadcrumb, pricing breakdown, stock status
- styles.css: added product card and recommendation section styles

## Database Migrations
- None

## APIs Added or Changed
- GET /product/<slug> now returns { product, recommendations, reviews }

## Tests Performed
- Manual: Tested product detail, cart add/remove on Python (port 8000)
- Mobile: Verified responsive layout on mobile emulator
- Regression: Verified category page and home page still work

## Known Issues
- Quantity selector uses plain <input type="number"> (no +/- buttons yet)
- Product image gallery has no zoom feature
- Related products ranking is basic (not yet sales-weighted)

## Pending Tasks
- Implement +/- quantity buttons
- Add image zoom on click
- Improve product recommendation ranking based on sales history

## Exact Recommended Next Step
1. Create Product Not Found template (/product-not-found.html)
2. Update /product/<slug> route to return 404 with template if product not found
3. Test 404 behavior and verify SEO noindex tag is present
```

---

## Debugging & Troubleshooting

### "Feature works in Node but not Python"
→ Python is source of truth. Test Python first. File a gap and prioritize Python implementation.

### "Port 8000 already in use"
→ Run `lsof -i :8000` to find running process. Either kill it or start Python on a different port: `PORT=8001 python server.py`

### "Users/orders not persisting"
→ Check if PostgreSQL is running. Run `curl http://localhost:8000/` and look for DB error messages in logs. JSON fallback will activate if DB is unavailable.

### "Admin image upload fails"
→ Check file type (must be `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`). Max size is 5 MB. Ensure `assets/` subdirs exist.

### "Search is empty on category page"
→ Verify `q` query param is being POSTed to category slug route. Check Python `process_category_query()` implementation in `server.py`.

### "Tests failing"
→ Run Python tests separately from Node. Node tests use `npm test` and validate `server.js`. Python currently relies on manual testing or future pytest suite.

---

## Files to Explore First

1. **[README.md](../../README.md)** — Project overview, runtime setup, features
2. **[LastStatus.md](../../LastStatus.md)** — What was last built, what's next
3. **[server.py](../../server.py)** — Primary backend, routes, auth, data models
4. **[templates/base.html](../../templates/base.html)** — Layout template with SEO metadata injection
5. **[styles.css](../../styles.css)** — CSS system and responsive design
6. **[requirements.txt](../../requirements.txt)** — Python dependencies
7. **[package.json](../../package.json)** — Node scripts and Express config

---

## Environment Variables

Set these before running `python server.py` or `npm run start:node`:

```bash
# Database (optional; JSON fallback if not set)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/vithi

# Admin credentials (defaults to admin/admin if not set)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin

# Server
PORT=8000
SITE_URL=http://localhost:8000

# Optional: image upload size limit (bytes, default 5MB)
MAX_IMAGE_SIZE_BYTES=5242880
```

---

## Next Steps to Get Oriented

**Follow these steps IN ORDER for every new task:**

1. ✅ **Read this file** (you are here) — Understand project overview and principles
2. → **Read [LastStatus.md](../../LastStatus.md)** — What was last done, what's next, known issues
3. → **Read all relevant SRS documents**
   - [productListingDetailFrontSRS.md](../../productListingDetailFrontSRS.md) — for storefront features
   - [categoryManageAdminSRS.md](../../categoryManageAdminSRS.md) — for admin features
4. → **Run the Python app** — `python server.py` → `http://localhost:8000`
5. → **Inspect the codebase** — Find existing implementations, identify affected files
6. → **Follow [vithi-ecommerce-delivery SKILL](./skills/vithi-ecommerce-delivery/SKILL.md)** — Implementation workflow
7. → **Test thoroughly** — Happy path, error handling, regression, mobile, SEO, authorization
8. → **Update [LastStatus.md](../../LastStatus.md)** — Document what you completed, tested, and the next step

---

## Questions or Gaps?

- **For project architecture/decisions:** See [Repository Conventions](./instructions/ecommerce-platform-conventions.instructions.md)
- **For SRS/requirements clarification:** Check [productListingDetailFrontSRS.md](../../productListingDetailFrontSRS.md) or [categoryManageAdminSRS.md](../../categoryManageAdminSRS.md)
- **For runtime/deployment issues:** See [Runtime Notes](../..//memories/repo/runtime-notes.md) or ask during debugging
- **For feature delivery workflow:** See [vithi-ecommerce-delivery SKILL](./skills/vithi-ecommerce-delivery/SKILL.md)

Happy building! 🌱
