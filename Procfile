web: poetry run flask db upgrade || echo "DB migration failed" && poetry run gunicorn -b 0.0.0.0:5000 "app:create_app()"
