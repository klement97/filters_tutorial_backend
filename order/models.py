from django.contrib.auth.models import User
from django.db import models


class Order(models.Model):
    class Meta:
        verbose_name = 'order'
        verbose_name_plural = 'orders'
        db_table = 'sc_order'
        ordering = ['-id']

    user = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name='orders', default=1)
    customer = models.CharField(max_length=255)
    amount = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField()

    deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_last_updated = models.DateTimeField(auto_now=True)
