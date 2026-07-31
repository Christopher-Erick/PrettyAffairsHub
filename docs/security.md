# Security Guide

## Baseline (shipped)

- CSRF middleware enabled
- Secure cookie flags in production
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- Referrer-Policy + Permissions-Policy via custom middleware
- WhiteNoise for safer static serving
- Secrets via environment variables

## Upcoming

- Rate limiting on auth / checkout
- Audit logging for admin and orders
- Dependency scanning in CI
- Strict CSP once third-party scripts are finalized
