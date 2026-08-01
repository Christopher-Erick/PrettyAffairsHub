#!/usr/bin/env bash
# Used by Render as the Build Command.
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
# Trust content (policies/FAQs) ships via migrations; seed reviews once products exist.
python manage.py seed_storefront_reviews || true
# Pre-fill Redis/app cache so the first shopper after deploy is not a cold miss.
python manage.py warm_cache || true
