# Использование `django_workers`

Приложение `django_workers` подключается к Django проекту и обрабатывает очередь задач.

## Постановка задачи

Нужно организовать отправку клиентам уведомлений о заказах. Отправку уведомлений будет выполнять Telegram бот. В случае, если было предпринято 3 неудачных попытки отправить уведомление, нужно прекратить дальнейшие попытки отправить это уведомление.

## Django проект

Предположим, у нас есть Django проект `workers_tutorial` следующей структуры:

```bash
.
├── README.md
├── db.sqlite3
├── manage.py
├── requirements.txt
└── workers_tutorial
    ├── __init__.py
    ├── asgi.py
    ├── settings.py
    ├── urls.py
    └── wsgi.py
```

Для работы используйте виртуальное окружение, про виртуальное окружение можно почитать [здесь](https://docs.python.org/3/library/venv.html#module-venv).

Запустите сервер:

```bash
python manage.py runserver
```

## Подключение `django_workers`

В будущем планируется поставлять `django_workers` как библиотеку. Сейчас можно скопировать приложение в виде каталога. Скопируйте каталог `django_workers` в корень проекта

```bash
.
├── README.md
├── db.sqlite3
├── django_workers
├── manage.py
├── requirements.txt
└── workers_tutorial
```

Подключите приложение `django_workers` в `INSTALLED_APPS` файла `workers_tutorial/settings.py`:

```python
INSTALLED_APPS = [
    ...
    'django_workers',
]
```

В том же файле подключите логирование:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django_workers': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
    },
}
```

## Прикладной код

Прикладной код описывает очередь уведомлений и логику ее обработки. Добавьте в проект приложение `notifications`. Для этого выполните команду:

```bash
python manage.py startapp notifications
```

Подключите приложение `django_workers` в `INSTALLED_APPS` файла `workers_tutorial/settings.py`:

```python
INSTALLED_APPS = [
    ...
    'notifications',
]
```

В файле `notifications/models.py` опишите модель "Уведомление о заказе"

```python
from django.db import models


class OrderNotification(models.Model):
    order_number = models.CharField("Номер заказа", max_length=8)
    tg_user_id = models.BigIntegerField("ID пользователя в Telegram")
    processed = models.BooleanField("Обработано")
    failed_attempts_number = models.PositiveSmallIntegerField(
        verbose_name="Число неудачных попыток",
        default=0,
    )

    class Meta:
        verbose_name = "Уведомление о заказе"
        verbose_name_plural = "Уведомления о заказах"

    def __str__(self):
        return f"Уведомление о заказе {self.order_number}\
            клиенту {self.tg_user_id}"
```

Как видите, объект "Уведомление о заказе" хранит номер заказа, идентификатор пользователя в Telegram, факт того, обработано уведомление или нет, а также число неудачных попыток отправить уведомление.
В файле `notifications/admin.py` опишите регистрацию "Уведомления о заказе" в админке:

```bash
rom django.contrib import admin
from .models import OrderNotification


@admin.register(OrderNotification)
class OrderNotification(admin.ModelAdmin):
    list_display = [
        "id",
        "order_number",
        "tg_user_id",
        "processed",
        "failed_attempts_number",
    ]
    readonly_fields = ["id"]
```

Регистрация в админке позволит интерактивно создавать очередь уведомлений, которую должно обработать приложение `django_workers`. Наш сценарий простой, на практике возможны более сложные сценарии. Например, менеджер создает заказы, при этом очередь уведомлений заполняется автоматически, а `django_workers` обрабатывает очередь.

Создайте и выполните миграцию:

```bash
python manage.py makemigrations
python manage.py migrate
```

Перейдите в [админку](http://127.0.0.1:8000/admin/) и заполните одно или несколько уведомлений о заказах. В каждом уведомлении нужно заполнить номер заказа и ID пользователя в Telegram. Узнать ID пользователя в Telegram можно у специального бота - [@userinfobot](https://t.me/userinfobot).

### Инициализация бота

Обратитесь к [@BotFather](https://t.me/BotFather) и создайте бота. Токен бота сохраните в файле `.env` в корне проекта:

```bash
TG_BOT_TOKEN=replace_me
```

Чтобы читать переменные из файла `.env`, установите environs:

```bash
pip install environs
```

В файле `workers_tutorial/settings.py` будет определяться значение переменной `TG_BOT_TOKEN`:

```python
from environs import Env

env = Env()
env.read_env()

TG_BOT_TOKEN = env.str("TG_BOT_TOKEN")
```

*Примечание*: чтобы бот мог отправлять сообщения пользователю, пользователь должен инициализировать диалог с ботом, то есть в диалоге с ботом нажать "Start".

Для отправки ботом сообщения будем использовать библиотеку httpx, установите ее:

```bash
pip install httpx
```

### Задайте логику обработки очереди уведомлений

Добавьте файл `notifications/task_queues.py` и опишите в нем логику обработки очереди уведомлений:

```python
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
        return queryset.exclude(failed_attempts_number__gte=3)

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
```

Разберем вышеописанный код. Мы создали класс `NotificationQueue`, который унаследован от предоставляемого приложением `django_workers` абстрактного класса `AbstractTaskQueue`. При этом необходимо описать следующие обязательные функции:

- функция `get_pending_tasks_queryset` отвечает за получение уведомлений, которые нужно обработать;
- функция `exclude_cycled_failed_tasks` описывает логику исключения зацикленных задач, в нашем случае - исключаем задачи, по которым было предпринято 3 и более неудачных попыток отправить уведомление;
- функция `handle_task` отвечает за обработку задачи, в нашем случае - за отправку сообщения ботом;
- функция `process_task_error` отвечает за обработку исключения, в нашем случае увеличиваем счетчик числа неудачных попыток;

В конце создается объект `task_queue` - экземпляр класса `NotificationQueue`.

## Запуск

Запустите обработку очереди задач командой:

```bash
python manage.py run_worker notifications.task_queues.task_queue -v 3
```

где

- `run_worker` - имя команды приложения `django_workers`, отвечающей за обработку очереди задач;
- `notifications.task_queues.task_queue` - позиционный параметр, который содержит путь к тому самому объекту `task_queue`, который был создан в [предыдущем шаге](#задайте-логику-обработки-очереди-уведомлений);
- `-v` - параметр, отвечающий за многословность, то есть за вывод debug-сообщений;

Если все было сделано правильно, то после запуска команды бот начнет присылать уведомления о заказах.

Подробную справку по команде `run_worker` можно увидеть, если ввести:

```bash
python manage.py run_worker --help
```
