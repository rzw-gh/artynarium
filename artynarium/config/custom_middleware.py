from datetime import datetime, timedelta
import pytz
import time
from shop import models


def check_orders(get_response):
    # One-time configuration and initialization.

    def middleware(request):
        # Code to be executed for each request before the view (and later middleware) are called.

        request.start_time = time.time()

        time_threshold = datetime.now(pytz.timezone('Asia/Tehran')) - timedelta(minutes=1)
        unpaid_orders = models.Order.objects.filter(status='Bank', update_at__lte=time_threshold)
        for order in unpaid_orders:
            # Increase Product & Variant
            order_items = models.OrderItem.objects.filter(user=request.user, order=order)
            for item in order_items:
                product = models.Product.objects.get(id=item.product.id)
                if item.from_store_amount:
                    product.store_amount += item.quantity
                    product.save()
                if item.from_amount:
                    product.amount += item.quantity
                    product.save()
                if item.variant:
                    variant = models.Variants.objects.get(id=item.variant.id)
                    if item.from_store_amount:
                        variant.quantity += item.quantity
                        variant.save()
                    if item.from_amount:
                        variant.seller_quantity += item.quantity
                        variant.save()
            order.status = 'Payment'
            order.decreased_products_amount = False
            order.save()

        response = get_response(request)
        # Code to be executed for each request/response after the view is called.

        response_time = int((time.time() - request.start_time) * 1000)

        return response

    return middleware
