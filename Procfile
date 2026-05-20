web: python manage.py migrate && python manage.py collectstatic --noinput && gunicorn bloom_finance.wsgi --bind 0.0.0.0:$PORT --log-file -
