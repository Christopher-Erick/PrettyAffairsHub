# Developer Guide

## Setup

1. Create and activate a virtualenv
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env`
4. `python manage.py migrate`
5. `python manage.py runserver`

## Conventions

- Business logic lives in apps under `apps/`
- Prefer TemplateViews / class-based views early; extract services as complexity grows
- Keep CSS in the design system files — avoid one-off page styles when possible
- Do not commit secrets or `.env`

## Useful commands

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic
```
