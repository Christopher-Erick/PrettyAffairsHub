# Go live — Supabase + Cloudflare

Pretty Affairs Hub stays a Django app. **Supabase** is the managed PostgreSQL
database. **Cloudflare** sits in front for DNS, TLS, WAF, and edge HTML/static
caching. Firebase is out of scope.

```text
Browser
  → Cloudflare edge (cache public pages + static assets)
      → App host (Railway / Render / Fly / VPS running Django/Gunicorn)
          → Supabase Postgres (data)
          → Redis / Upstash (smart app cache, recommended)
          → Media: disk now → Cloudflare R2 later
```

## What already works in the codebase

| Piece | Behaviour |
|-------|-----------|
| Supabase DB | Set `DATABASE_URL` or `SUPABASE_DB_URL` (pooler URI). Production settings refuse SQLite. |
| Smart cache | Home, shop rails, filters, product lists/details cache until a catalogue **write**. |
| Write invalidation | Saving/deleting products, categories, images, variants bumps cache version. |
| Cloudflare headers | Anonymous GET on `/`, `/shop/…` get long `s-maxage` for the edge. Cart/admin/auth stay private. |
| Edge purge | Optional: set `CLOUDFLARE_ZONE_ID` + `CLOUDFLARE_API_TOKEN` to purge after writes. |

Local default remains SQLite + LocMem so you can develop offline.

---

## Checklist to make the site live

### 1. Supabase project

1. Create a project at [supabase.com](https://supabase.com).
2. **Settings → Database → Connection string → URI**  
   Prefer the **Transaction pooler** (port `6543`).
3. Put it in production env as:

```env
DATABASE_URL=postgresql://postgres.PROJECT:PASSWORD@HOST:6543/postgres
POSTGRES_SSLMODE=require
SUPABASE_URL=https://PROJECT.supabase.co
```

4. From your machine (or the host), with production settings:

```bash
export DJANGO_SETTINGS_MODULE=config.settings.production
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

5. Upload media (product images) to the host `MEDIA_ROOT`, or later to R2.

### 2. Redis (recommended for multi-worker hosts)

LocMem does not share cache across Gunicorn workers. Use Upstash Redis or Redis on the host:

```env
REDIS_URL=rediss://default:PASSWORD@HOST:6379
```

### 3. App host (Django)

Pick one: **Railway**, **Render**, **Fly.io**, or a VPS.

Set at least:

```env
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
SECRET_KEY=…long random…
ALLOWED_HOSTS=prettyaffairshub.com,www.prettyaffairshub.com
DATABASE_URL=…from Supabase…
REDIS_URL=…optional but recommended…
CSRF_TRUSTED_ORIGINS=https://prettyaffairshub.com,https://www.prettyaffairshub.com
```

Start with Gunicorn, e.g. `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`.

Serve media via the host or Cloudflare R2 (Phase 2).

### 4. Cloudflare

1. Add the domain to Cloudflare; point nameservers as instructed.
2. Create an **A/CNAME** to your app host; turn the orange cloud **on** (proxied).
3. SSL/TLS mode: **Full (strict)**.
4. Always Use HTTPS: on.
5. Caching:
   - Cache Rules: cache everything under `/static/` aggressively.
   - Honour origin `Cache-Control` / `CDN-Cache-Control` for HTML (already set by middleware).
6. Optional purge API:
   - Create an API token with Zone → Cache Purge.
   - Set `CLOUDFLARE_ZONE_ID` and `CLOUDFLARE_API_TOKEN` on the app.

### 5. Smoke test

1. Open the site over HTTPS via the Cloudflare URL.
2. Load home + shop twice — second load should be fast (edge + app cache).
3. Add a product in `/admin/` — listings should refresh (cache invalidated).
4. Cart, checkout, and admin must **not** be publicly cached.

### 6. Later (optional)

- Move product images to **Cloudflare R2** (S3-compatible storage).
- Cloudflare Images / resizing for thumbnails.
- Cloudflare Access in front of `/admin/`.

---

## Honest limits

- Cart, checkout, accounts, and admin always hit the app (and usually the DB). That is correct.
- “Database only when new data is added” applies to **catalogue browsing** (home, shop, PDP). Writes and personalised sessions still use the database.
- True edge HTML caching needs Cloudflare in front of a live host; local `runserver` only exercises the Django smart cache.
