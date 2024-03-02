import logging
from functools import partial
from time import sleep

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db import models
from django.utils import autoreload
from django.utils.module_loading import import_string

from ...task_queues import AbstractTaskQueue
from ...exceptions import TaskError

logger = logging.getLogger('django_workers')


def track_and_run_tasks(  # noqa CCR001
    *,
    task_queue: AbstractTaskQueue,
    reindex_timeout: int,
) -> None:
    logger.info('Tracking for new mailing tasks started.')

    while True:
        with transaction.atomic():
            queryset = task_queue.get_pending_tasks_queryset()
            task: models.Model | None = (
                task_queue.exclude_cycled_failed_tasks(queryset)
                # lock record till processing end
                .select_for_update(skip_locked=True)
                .first()
            )

            if not task:
                logger.debug('Sleeping for %s seconds.', reindex_timeout)
                sleep(reindex_timeout)
                continue

            task_id = getattr(task, task_queue.task_id_field_name)

            logger.info('New task found id=%s', task_id)

            try:
                with TaskError.set_default_task_id(task_id):
                    with TaskError.convert_exceptions('unhandled_exception'):
                        task_queue.handle_task(task)
                        logger.info(
                            'Processed successfully task id=%s', task_id)
            except TaskError as error:
                task_queue.process_task_error(task, error)
                logger.exception('Failed task id=%s', task_id)


class Command(BaseCommand):
    help = 'Run trigger mailing by funnel leads queue.'  # noqa: A003

    def add_arguments(self, parser):
        parser.add_argument(
            '--reindex_timeout',
            type=int,
            default=5,
            help='How ofter database state will be checked for new tasks.',
        )
        parser.add_argument(
            'task_queue_import_path',
            type=str,
            help='Path to import AbstractTaskQueue subclass instance from. E.g. `project.task_queues.queue`.',
        )
        parser.add_argument(
            '--reload',
            help='Reload on code change',
            action='store_true',
        )

    def handle(self, *args, **options):
        verbosity = int(options['verbosity'])

        if verbosity > 1:
            logger.setLevel(logging.DEBUG)

        task_queue = import_string(options['task_queue_import_path'])
        tasks_handler = partial(
            track_and_run_tasks,
            task_queue=task_queue,
            reindex_timeout=options['reindex_timeout'],
        )
        try:
            if options['reload']:
                autoreload.run_with_reloader(tasks_handler)
            tasks_handler()
        except KeyboardInterrupt:
            logger.info('Stopped by KeyboardInterrupt')
