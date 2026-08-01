# Architecture

## Overview

Pretty Affairs Hub is a server-rendered Django e-commerce platform with a modular app layout and a reusable CSS design system.

## Apps

| App | Responsibility |
|-----|----------------|
| `core` | Security headers, smart cache, Cloudflare edge headers, site context |
| `catalog` | Products, categories, collections, search/filters |
| `content` | Homepage, blog, FAQs, about, CMS blocks |
| `accounts` | Customers, addresses, wishlist |
| `cart` / `orders` / `discounts` / `reviews` | Commerce flows |

## Data & cache

- **Local:** SQLite + LocMem cache
- **Production:** [Supabase PostgreSQL](https://supabase.com) via `DATABASE_URL`
- **Smart cache:** catalogue pages served from cache until a write invalidates (see `apps.core.smart_cache`)
- **Edge:** Cloudflare caches anonymous HTML/static when DNS is proxied

## Settings

- `config.settings.local` — development (default)
- `config.settings.production` — Supabase Postgres + secure cookies/HSTS

## Deployment

App host (Railway / Render / Fly / VPS) + Supabase + Cloudflare.

Full go-live steps: [`docs/go-live-supabase-cloudflare.md`](go-live-supabase-cloudflare.md).
