"""
Celery 앱 설정 모듈.

Redis를 브로커(메시지 큐)이자 결과 저장소로 사용한다.
워커는 app.worker 패키지에서 태스크를 자동 검색(autodiscover)한다.
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "youtube_qa",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,  # 태스크 시작 상태 추적 활성화
    task_acks_late=True,  # 태스크 완료 후 ACK (워커 비정상 종료 시 재시도 보장)
    worker_prefetch_multiplier=1,  # 한 번에 하나의 태스크만 가져옴 (긴 작업에 적합)
)

# app.worker 패키지에서 @celery_app.task 데코레이터가 붙은 태스크를 자동 검색
celery_app.autodiscover_tasks(["app.worker"])
