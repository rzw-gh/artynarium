from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.shortcuts import render

from config.utils import persian_numbers_converter
from shop import models
from datetime import datetime
from config.jalali import Gregorian


@staff_member_required()
def orders(request):
    orders = models.Order.objects.all()
    paginator = Paginator(orders, 12)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    context = {"orders": orders}
    return render(request, 'artynarium_admin/orders/orders.html', context)


@staff_member_required()
def order_detail(request, id):
    now = datetime.now()
    order = models.Order.objects.get(id=id)

    time_to_str = "{},{},{}".format(now.year, now.month, now.day)
    time_to_tuple = Gregorian(time_to_str).persian_tuple()
    time = f"{persian_numbers_converter(str(time_to_tuple[0]))}/{persian_numbers_converter(str(time_to_tuple[1]))}/{persian_numbers_converter(str(time_to_tuple[2]))}"

    context = {
        "order": order,
        "time": time, "orderid": persian_numbers_converter(str(order.orderid)),
        "receiver": f"{order.first_name} {order.last_name}",
        "state": f"{order.state} - {order.city}",
        "zipcode": persian_numbers_converter(str(order.zipcode)),
        "address": f"{order.city} - {order.address}",
        "phone": persian_numbers_converter(str(order.phone)),
        "website": "ARTYNARIUM.COM"
    }
    return render(request, 'artynarium_admin/orders/order_detail.html', context)
