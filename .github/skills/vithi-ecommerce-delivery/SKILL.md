---
name: vithi-ecommerce-delivery
description: "Develop, maintain, and review the Vithi Organics Store using API-first architecture, responsive storefront and admin UX, SEO, security, and production-quality testing. Use for feature implementation, bug fixes, refactors, and release readiness in this hybrid Python/Node eCommerce project."
argument-hint: "Task to implement or review in Vithi Organics Store"
user-invocable: true
disable-model-invocation: false
---

# Vithi eCommerce Delivery Workflow

## Outcome
Produce a tested, backward-compatible, production-quality change for Vithi Organics Store while preserving existing working behavior unless requirements explicitly change it.

## Use When
- Building or modifying storefront, admin, API, backend, templates, data handling, SEO, or deployment behavior.
- Implementing features across categories, brands, products, search, wishlist, cart, checkout, orders, reviews, inventory, and admin operations.
- Validating security, responsiveness, and performance for web and future mobile API reuse.

## Source of Truth and Pre-Checks
SRS status: pending from project owner; integrate explicit SRS file paths once provided.

1. Read relevant SRS and requirement documents first.
2. If SRS/requirement files are not discoverable, fall back to `README.md` + `LastStatus.md` + codebase inspection and explicitly note this fallback in the task report.
3. Read `README.md`.
4. Read `LastStatus.md`.
5. Inspect current code, routes, APIs, templates, data files, and dependencies before deciding a feature is missing.
6. Reuse existing architecture and patterns unless there is a strong technical reason to change.
7. Preserve hybrid stack behavior (`server.py`, `server.js`, templates, views, admin, JSON/PostgreSQL paths).

## Delivery Sequence (Default)
1. Restate the task in implementation terms (user flow, API behavior, data impacts, SEO, testing scope).
2. Identify affected layers: frontend, backend, API, database/data files, authentication/authorization, validation, SEO metadata, media handling.
3. Choose the smallest complete change that solves the root cause.
4. Implement using modular code and existing project patterns.
5. Add or adjust API behavior so logic can be reused by future mobile clients.
6. Apply security controls: input validation, sanitization, authorization checks, file upload constraints, secret handling.
7. Validate responsive behavior (mobile, tablet, desktop) where UI is touched.
8. Run focused tests for happy path and failure paths.
9. Verify no regression in existing behavior.
10. Update docs if architecture, API contracts, or behavior changed.
11. Update `LastStatus.md` with full session details.
12. Report what changed, how it was tested, known issues, and exact next step.

## Decision Logic
### A) Requirement conflict
- If documents conflict, follow the most recently approved requirement.
- Explicitly report the conflict and chosen interpretation.

### B) Feature already exists
- If implementation already exists and meets requirements, avoid rewrites.
- Limit work to targeted fixes, gap closure, or tests.

### C) Data model or relationship impact
- Preserve relational principles (Product -> Category ID, Product -> Brand ID).
- Do not silently change schema or duplicate relationship fields unnecessarily.
- Preserve historical order snapshot fields even if product records change later.

### D) Admin operations for categories/brands
- Prevent destructive deletion when products are linked.
- Prefer status-based deactivation for records with dependencies.

### E) SEO-sensitive page changes
- Ensure dynamic title, meta description, meta keywords, canonical URL, Open Graph, and structured data are maintained.

### F) Search changes
- Enforce online-product-only results.
- Keep ranking priority and category-page behavior rules.
- Preserve filters/sorting across pagination.

### G) Stock and purchasing changes
- Auto-derive stock status from inventory.
- Disable Add to Cart when out of stock.

## Quality Gates (Do Not Mark Complete Until Passed)
- Apply these gates pragmatically: run all checks relevant to the scope of the current change, and do not claim completion if any relevant gate is skipped.
- Functional: happy path works for the target feature.
- Validation: invalid input and empty states are handled.
- Authorization: unauthorized access is blocked for admin actions.
- Data integrity: no broken relationships or destructive side effects.
- SEO: required metadata and URL/slug behavior are correct.
- Responsive UI: mobile, tablet, desktop behavior is acceptable.
- Error handling: API and UI errors are visible and non-breaking.
- Backward compatibility: existing major flows still operate.
- Tests: relevant tests run; new tests added or updated when required.

## Domain-Specific Implementation Rules
### Category management
- Support full category fields including ordering, rich text, image, status, SEO fields, and audit fields.
- Block deletion when linked products exist.

### Brand management
- Use Brand ID as relationship key.
- Support legal/contact/status/audit fields.
- Prevent permanent deletion if linked products exist.

### Product management
- Support required product attributes including media, pricing, tax, stock, SEO, and ordering fields.
- Maintain product slug generation and uniqueness rules.
- Allow authorized admin slug override.

### Product and category storefront pages
- Keep breadcrumbs, key metadata, content blocks, and recommendation sections.
- Preserve pagination, sorting, and responsive product grids.

### Cart and checkout
- Cover login/account, address selection, coupon application, summary, payment return handling, confirmations, and order persistence.

## Security and Performance Checklist
- Validate and sanitize all user-controlled input, including rich text.
- Apply XSS, CSRF, injection, and authorization protections.
- Keep secrets in environment variables only.
- Validate uploads by type, extension, and size.
- Apply pagination, optimized queries, caching where appropriate.
- Use responsive/modern images and lazy loading without harming above-the-fold LCP.

## Completion Notes Requirement
Update `LastStatus.md` after meaningful sessions with:
- Date and time
- Current branch
- Latest completed task
- Files created and modified
- Database migrations
- APIs added or changed
- Tests performed
- Known issues
- Pending tasks
- Exact recommended next step

## Output Contract for Each Task
- What was requested
- What was changed
- Why this approach was chosen
- Validation/tests performed
- Remaining risks or known issues
- Recommended next step
