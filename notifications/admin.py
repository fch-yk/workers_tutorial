from django.contrib import admin
from .models import OrderNotification


@admin.register(OrderNotification)
class OrderNotification(admin.ModelAdmin):
    list_display = ["id", "order_number", "tg_user_id", "processed", "failed"]
    readonly_fields = ["id"]
