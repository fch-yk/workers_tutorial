from django.db import models


class OrderNotification(models.Model):
    order_number = models.CharField("Номер заказа", max_length=8)
    tg_user_id = models.BigIntegerField("ID пользователя в Telegram")
    processed = models.BooleanField("Обработано")
    failed = models.BooleanField("Завершено с ошибкой")

    class Meta:
        verbose_name = "Уведомление о заказе"
        verbose_name_plural = "Уведомления о заказах"

    def __str__(self):
        return f"Уведомление о заказе {self.order_number}\
            клиенту {self.tg_user_id}"
