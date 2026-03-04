import os
import ssl

from celery import Celery


REDIS_URL = os.getenv("REDIS_URL")

CELERY_BROKER_URL = REDIS_URL or "memory://"
CELERY_RESULT_BACKEND = REDIS_URL or "cache+memory://"

celery = Celery(
    "code_judge",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

if REDIS_URL and REDIS_URL.startswith("rediss://"):
    celery.conf.broker_use_ssl = {
        "ssl_cert_reqs": ssl.CERT_NONE
    }
    celery.conf.redis_backend_use_ssl = {
        "ssl_cert_reqs": ssl.CERT_NONE
    }

celery.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_always_eager=not bool(REDIS_URL),
    task_eager_propagates=True,
)
