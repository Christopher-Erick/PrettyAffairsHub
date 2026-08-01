web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --worker-class gthread --workers 2 --threads 8 --timeout 60 --keep-alive 5 --max-requests 400 --max-requests-jitter 40
