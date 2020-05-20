from django_filters import rest_framework as filters

from order.models import Order


class OrderFilter(filters.FilterSet):
    customer = filters.CharFilter(lookup_expr='icontains')
    amount = filters.RangeFilter()
    price = filters.RangeFilter()
    date_created = filters.DateTimeFromToRangeFilter()
    user__first_name = filters.CharFilter(lookup_expr='icontains')
    user__last_name = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Order
        fields = ['id', 'deleted']
