from __future__ import annotations

import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)
_scheduler_started = False


def start_freesc_scheduler() -> None:
    global _scheduler_started
    if _scheduler_started:
        return
    if not getattr(settings, 'FREESC_RUN_SCHEDULER', False):
        return
    if os.environ.get('RUN_MAIN') == 'false':
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        from django_apscheduler.jobstores import DjangoJobStore
    except ImportError:
        logger.warning('django-apscheduler не установлен — автосинхронизация релизов отключена.')
        return

    from landing.services.freesc_sync import run_scheduled_sync

    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    scheduler.add_jobstore(DjangoJobStore(), 'default')

    interval_days = getattr(settings, 'FREESC_SYNC_CHECK_INTERVAL_HOURS', 6)
    scheduler.add_job(
        _scheduled_sync_job,
        trigger=IntervalTrigger(hours=interval_days),
        id='freesc_release_sync',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler_started = True
    logger.info('Планировщик синхронизации ИТС запущен (проверка каждые %s ч).', interval_days)


def _scheduled_sync_job() -> None:
    from landing.services.freesc_sync import run_scheduled_sync

    try:
        log = run_scheduled_sync(force=False)
        if log:
            logger.info('Синхронизация ИТС завершена: %s', log.message)
        else:
            logger.debug('Синхронизация ИТС пока не требуется.')
    except Exception:
        logger.exception('Ошибка автосинхронизации релизов с ИТС')
