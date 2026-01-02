release: python ./manage.py migrate
# Set `--timeout-graceful-shutdown` to shorter than the 30 second limit imposed by Heroku restarts
web: uvicorn --ws websockets-sansio --host 0.0.0.0 --port $PORT --workers $WEB_CONCURRENCY --timeout-graceful-shutdown 25 geoinsight.asgi:application
worker: REMAP_SIGTERM=SIGQUIT celery --app geoinsight.celery worker --loglevel INFO --without-heartbeat
