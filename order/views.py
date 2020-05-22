from filters_tutorial_back.common.api_views import CustomListAPIView
from order.filters import OrderFilter
from order.models import Order
from order.serializers import OrderSerializer


class OrderListCreateAPIView(CustomListAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    filterset_class = OrderFilter
    ordering_fields = ['id', 'customer', 'amount', 'price', 'date_created', 'user__first_name', 'user__last_name', 'deleted']

    def get_filterset(self, request, queryset, view):
        pass
