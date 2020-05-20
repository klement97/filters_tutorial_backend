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

    @property
    def qs(self):
        """
        We can set the initial queryset here.
        The 'request' is available under self.
        """
        # It is not guaranteed that a request will be provided to the FilterSet instance.
        # Any code depending on a request should handle the None case.
        request = self.request
        if request is not None:
            pass

        parent = super(OrderFilter, self).qs
        return parent
