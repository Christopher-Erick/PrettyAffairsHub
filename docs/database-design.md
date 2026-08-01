# Database Design

## Current

| Environment | Engine |
|-------------|--------|
| Local | SQLite (`db.sqlite3`) |
| Production | **Supabase PostgreSQL** via `DATABASE_URL` / `SUPABASE_DB_URL` |

Discrete `POSTGRES_*` vars remain as a fallback when no URL is set and `USE_POSTGRES=True`.

## Caching contract

Catalogue reads (home rails, shop filters, product lists, PDPs) are served from
the smart cache. Saving or deleting catalogue rows bumps the cache version so
the next request rebuilds from Supabase. Cart, checkout, and admin always use
the database.

## Models

Brand, Category, Collection, Product, ProductImage, ProductVariant, cart/order
models, CMS (blog, FAQ, homepage sections), reviews, discounts.
