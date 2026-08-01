# Deployment Guide

## Environments

| Env | Settings module | Database |
|-----|-----------------|----------|
| Local | `config.settings.local` | SQLite (default) |
| Production | `config.settings.production` | Supabase PostgreSQL (`DATABASE_URL`) |

## Production checklist

1. Create a Supabase project and copy the **pooler** `DATABASE_URL`
2. Set strong `SECRET_KEY`, `ALLOWED_HOSTS`, `DEBUG=False`
3. Set `REDIS_URL` (recommended) for shared smart cache across workers
4. Run `migrate`, `createsuperuser`, `collectstatic`
5. Deploy Django (Gunicorn) on Railway / Render / Fly / VPS
6. Put the domain on **Cloudflare** (proxied DNS, Full strict SSL)
7. Optional: `CLOUDFLARE_ZONE_ID` + `CLOUDFLARE_API_TOKEN` for purge-on-write

Step-by-step: [`docs/go-live-supabase-cloudflare.md`](go-live-supabase-cloudflare.md).
