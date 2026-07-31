# Architecture

## Overview

Pretty Affairs Hub is a server-rendered Django e-commerce platform with a modular app layout and a reusable CSS design system.

## Apps

| App | Responsibility |
|-----|----------------|
| `core` | Security headers, site context, shared utilities |
| `catalog` | Products, categories, collections, search/filters |
| `content` | Homepage, blog, FAQs, about, CMS blocks |
| `accounts` | Customers, addresses, wishlist (upcoming) |

Future apps: `cart`, `orders`, `payments`, `discounts`, `reviews`, `marketing`, `inventory`, `search`.

## Settings

- `config.settings.local` — development (default)
- `config.settings.production` — PostgreSQL + secure cookies/HSTS
- Toggle DB with `USE_POSTGRES` / production env vars

## Frontend

Templates under `templates/` compose reusable partials and components.  
Tokens live in `static/css/tokens.css`. Brand logo: `static/img/logo.png`.

## Deployment target

App host (Railway / Render / VPS) + Cloudflare (DNS, TLS, caching, optional R2/Images).
