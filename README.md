# Pretty Affairs Hub

Luxury beauty & cosmetics e-commerce platform built with Django.

**Brand:** Pretty Affairs Hub  
**Tagline:** Your One Stop Beauty Destination

## Stack

- Django 6 + PostgreSQL (SQLite for local by default)
- HTML / CSS design system / progressive JavaScript
- WhiteNoise for static files
- Cloudflare-ready deployment path

## Quick start

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # or: cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/

## Project layout

```
apps/
  core/       shared middleware, context processors
  catalog/    products, shop (Phase 2+)
  content/    homepage & CMS pages
  accounts/   customers (Phase 4)
config/       Django settings (local / production)
templates/    design system templates
static/       css, js, brand assets
docs/         architecture & guides
```

## Documentation

See `docs/` for architecture, deployment, security, and development guides.

## Current milestone

Phase 0 foundation + Phase 1 design system and homepage shell are in place.  
Next: Phase 2 catalog (products, categories, collections, admin).
