import httpx
from django.conf import settings
from django.db import models

from django_workers import AbstractTaskQueue, TaskError
from .models import OrderNotification


class NotificationQueue(AbstractTaskQueue):

    def get_pending_tasks_queryset(self) -> models.QuerySet:
        return OrderNotification.objects.filter(processed=False)

    def exclude_cycled_failed_tasks(
        self,
        queryset: models.QuerySet,
    ) -> models.QuerySet:
        return queryset.exclude(failed_attempts_number__gt=3)

    def handle_task(self, queryset_item: OrderNotification):
        tg_bot_token = settings.TG_BOT_TOKEN
        url = f'https://api.telegram.org/bot{tg_bot_token}/sendMessage'
        payload = {
            'chat_id': queryset_item.tg_user_id,
            'text': f'Сформирован заказ номер {queryset_item.order_number}'
        }
        response = httpx.post(url, params=payload)
        response.raise_for_status()
        queryset_item.processed = True
        queryset_item.save()

    def process_task_error(
        self, queryset_item: OrderNotification, error: TaskError
    ) -> None:
        queryset_item.failed_attempts_number += 1
        queryset_item.save()


task_queue = NotificationQueue()
