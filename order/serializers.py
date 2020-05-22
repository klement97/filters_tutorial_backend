from django.contrib.auth.models import User
from rest_framework.serializers import ModelSerializer

from order.models import Order


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name']


class OrderSerializer(ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Order
        fields = ['id', 'customer', 'amount', 'price', 'notes', 'deleted', 'date_created', 'date_last_updated', 'user']
