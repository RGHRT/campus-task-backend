from django.conf import settings
from django.db import models


class Task(models.Model):
    class Status(models.TextChoices):
        PENDING = "未完成", "未完成"
        IN_PROGRESS = "进行中", "进行中"
        WAITING_CONFIRM = "待确认", "待确认"
        COMPLETED = "已完成", "已完成"
        CANCELLED = "已取消", "已取消"

    publisher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="published_tasks",
        null=True,
        blank=True,
    )

    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="received_tasks",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=100)

    description = models.TextField()

    reward = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
