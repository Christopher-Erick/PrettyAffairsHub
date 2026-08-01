#!/usr/bin/env bash
# Used by Render as the Build Command.
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
