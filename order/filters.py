from django_filters import rest_framework as filters

from order.models import Order


class OrderFilter(filters.FilterSet):
    customer = filters.CharFilter(field_name='customer', lookup_expr='icontains')
    amount = filters.RangeFilter(field_name='amount')
    price = filters.RangeFilter(field_name='price')
    date_created = filters.DateTimeFromToRangeFilter(field_name='date_created')
    user__first_name = filters.CharFilter(field_name='user__first_name', lookup_expr='icontains')
    user__last_name = filters.CharFilter(field_name='user__last_name', lookup_expr='icontains')

    class Meta:
        model = Order
        fields = ['id', 'customer', 'amount', 'price', 'deleted', 'date_created']
