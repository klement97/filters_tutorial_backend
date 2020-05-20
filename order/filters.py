from django_filters import rest_framework as filters

from order.models import Order


class OrderFilter(filters.FilterSet):
    customer = filters.CharFilter(lookup_expr='icontains')
    amount = filters.RangeFilter()
    price = filters.RangeFilter()
    date_created = filters.DateTimeFromToRangeFilter()
    user__first_name = filters.CharFilter(lookup_expr='icontains')
    user__last_name = filters.CharFilter(lookup_expr='icontains')
    username = filters.CharFilter(field_name='user__username', method='get_username')

    class Meta:
        model = Order
        fields = ['id', 'deleted', 'username']

    @property
    def qs(self):
        """
        We can set the initial queryset here.
        The 'request' is available under self.
        """
        # It is not guaranteed that a request will be provided to the FilterSet instance.
        # Any code depending on a request should handle the None case.
        request = self.request
        if request is None:
            return Order.objects.none()

        parent = super(OrderFilter, self).qs
        return parent

    def get_username(self, queryset, name, value):
        """
        We can make a more complex filter here.
        @param self            OrderFilter instance
        @param queryset        Initial Queryset
        @param name            Field name
        @param value           Filtered value
        """
        return queryset.filter(**{
            name: value
            })
