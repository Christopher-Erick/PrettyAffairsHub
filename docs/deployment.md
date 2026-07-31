# Deployment Guide

## Environments

| Env | Settings module | Database |
|-----|-----------------|----------|
| Local | `config.settings.local` | SQLite (default) |
| Production | `config.settings.production` | PostgreSQL required |

## Production checklist

1. Set strong `SECRET_KEY`
2. Set `ALLOWED_HOSTS` and `DEBUG=False`
3. Configure PostgreSQL credentials
4. Run `collectstatic`
5. Serve behind HTTPS (Cloudflare)
6. Configure email backend
7. Rotate secrets via host env vars — never bake into images

## Cloudflare (free tier)

- Proxy DNS through Cloudflare
- Enable HTTPS / Always Use HTTPS
- Cache static assets aggressively
- Consider R2 for media later

Full phased plan (Firebase data options, admin story, Workers/Pages): see
[`docs/firebase-cloudflare-migration.md`](firebase-cloudflare-migration.md).
