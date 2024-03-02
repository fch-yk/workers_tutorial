from abc import ABC, abstractmethod

from django.db import models

from .exceptions import TaskError


class AbstractTaskQueue(ABC):
    task_id_field_name = 'pk'

    @abstractmethod
    def get_pending_tasks_queryset(self) -> models.QuerySet:
        ...

    @abstractmethod
    def exclude_cycled_failed_tasks(
        self,
        queryset: models.QuerySet,
    ) -> models.QuerySet:
        ...

    @abstractmethod
    def handle_task(self, queryset_item: models.Model):
        ...

    @abstractmethod
    def process_task_error(self, queryset_item: models.Model, error: TaskError) -> None:
        ...
