# Firebase + Cloudflare Migration Plan

Practical phased path for Pretty Affairs Hub (current: Django 6 + SQLite/Postgres + WhiteNoise + local media).

**Do not rip out Django in one rewrite.** Keep Django admin and the existing storefront until Firebase credentials, Cloudflare account wiring, and a product-management story are real.

## Why the site feels slow today (addressed in code + hosting)

| Cause | Immediate Django wins | Hosting / CDN wins |
|-------|----------------------|--------------------|
| N+1 on product cards (`primary_image`, stock, variants) | Prefetch-aware model properties + `select_related` / `Prefetch` | — |
| Shop discovery loop (query per category) | Single batched sample load + short LocMem cache | Cloudflare HTML cache for anonymous shop later |
| Unoptimized / full-size media over `runserver` | `loading=lazy`, `decoding=async`, `sizes` hints | Cloudflare Images or R2 + resizing |
| DEBUG + local SQLite + no CDN | Keep for local only | Production: `DEBUG=False`, Postgres, Cloudflare proxy |
| Google Fonts on every page | Already preconnect | Optional self-host fonts behind Cloudflare |

## Target architecture (phased)

```text
Browser
  → Cloudflare (DNS, TLS, WAF, cache, optional Pages/Workers)
      → Django app host (Railway / Render / Fly / VPS)   [Phases 1–2]
      → OR Workers + Firestore API                       [Phase 3+, optional]
  → Media: local disk → Cloudflare R2 (or Firebase Storage)
  → Data: Postgres (keep) → optional Firestore mirror/cutover
```

### What maps where

| Domain data | Keep in Django/Postgres (recommended Phase 1–2) | Firebase alternative | Cloudflare role |
|-------------|-----------------------------------------------|----------------------|-----------------|
| Products, variants, categories | Yes | Firestore collections `products`, `variants` | Cache product HTML/API |
| Product images | `MEDIA_ROOT` now | Firebase Storage **or** R2 | R2 public bucket + cache |
| Orders, carts, customers | Django models | Firestore + Auth | WAF / bot fight |
| CMS (blog, FAQ, homepage) | Django | Firestore | Cache pages |
| Sessions / auth | Django sessions | Firebase Auth | — |
| Admin / catalogue ops | **Django admin (keep)** | Firebase Console (weak UX) or custom admin | Protect `/admin` |

**Realtime Database** is a poor fit for a product catalogue (relational-ish, filtered lists, admin edits). Prefer **Firestore** if/when leaving SQL. Use Realtime only for live stock counters or live order board if needed later.

## Admin / product management story

Your message cut off at: *“also when wanting to add items or perform admin operations…”*

**Recommended default (now and through Phase 2):** keep **Django admin** at `/admin/` for adding/editing products, images, variants, orders. It already works; do not invent a half-broken Firebase admin rewrite.

| Option | When to use | Notes |
|--------|-------------|-------|
| **A. Keep Django admin** (preferred) | Always, until a full Firebase cutover | Staff log in to Django; importer commands stay as management commands |
| **B. Django admin + API** | If a headless storefront appears | Admin still writes Postgres; Workers/Pages read API |
| **C. Firebase Console** | Only for Storage/Auth tweaks | Not suitable as primary merchandising UI |
| **D. Custom admin on Firestore** | Only after Firestore is source of truth | Build deliberately; do not dual-write half systems |

Until you clarify the cut-off sentence (custom admin UI? staff roles? mobile inventory?), **Option A** remains the plan.

## Phased path

### Phase 0 — Now (done / in progress, no Firebase keys required)

- Performance fixes in Django views/models
- Expand authorized catalogue import
- Env scaffolding for future Firebase/Cloudflare IDs (empty by default)
- Keep images local under `media/products/`

### Phase 1 — Cloudflare in front of Django (highest ROI)

1. Deploy Django + Postgres (`config.settings.production`)
2. Point DNS to Cloudflare (orange-cloud proxy)
3. Enable: Always HTTPS, WAF managed rules, Bot Fight Mode
4. Cache rules: cache `/static/*` aggressively; bypass `/admin/*`, `/cart/*`, `/accounts/*`, `/orders/*`
5. Optional: Cloudflare R2 for media; set Django storage to S3-compatible R2 when credentials exist

**Admin:** unchanged — Django admin behind Cloudflare Access (optional zero-trust email allowlist).

### Phase 2 — Media + CDN hardening

1. Move `ProductImage` / variant images to **R2** (preferred with Cloudflare) or **Firebase Storage**
2. Serve via custom domain `media.prettyaffairshub.com`
3. Add image resizing (Cloudflare Images or on-upload thumbnails)
4. Keep Django ORM as source of truth

### Phase 3 — Optional Firebase data (only with real project credentials)

Scaffolding env vars (see `.env.example`):

- `FIREBASE_PROJECT_ID`
- `FIREBASE_STORAGE_BUCKET`
- Service account JSON path (never commit)

Possible uses without rewriting the shop:

1. **Auth only** — Firebase Auth for customers; Django still owns orders
2. **Storage only** — images in Firebase Storage; product rows stay in Postgres
3. **Firestore mirror** — nightly export of published products for a future headless front

**Do not** dual-write production catalogue to Firestore until sync, admin, and rollback are defined.

### Phase 4 — Headless cutover (optional, large project)

Only if you explicitly want SPA/Pages + Firestore:

1. Cloudflare Pages front-end
2. Workers API reading Firestore
3. Replace Django storefront routes
4. Rebuild admin (custom) or keep a Django “ops” service writing to Firestore via Admin SDK

This is a greenfield-sized effort; treat as a separate initiative.

## What we will not do without credentials

- Invent fake Firebase API keys or commit service accounts
- Switch production traffic to Firestore while SQLite/local media still power the shop
- Replace Django admin with an incomplete console workflow

## Suggested next decisions for you

1. Prefer **Cloudflare R2** or **Firebase Storage** for images?
2. Is the cut-off admin request about **staff Django admin**, a **simpler merchandiser UI**, or **mobile stock updates**?
3. Confirm production host (Railway / Render / VPS) for Phase 1.
