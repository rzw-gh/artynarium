from seller.models import TicketReply
from django.db.models import Q
from shop.models import SellerOrder


def ticket(request):
    if request.user.is_authenticated and request.user.seller:
        user_unread_messages_count = TicketReply.objects.filter(
            Q(ticket__user=request.user) | Q(ticket__to=request.user), user_status='UnRead').count()
        return {"user_unread_messages_count": user_unread_messages_count}
    else:
        return {}


def seller_orders(request):
    if request.user.is_authenticated and request.user.seller:
        seller_order_notif = SellerOrder.objects.filter(seller=request.user, order__status="Preparing", notif=True).count()
        return {"seller_order_notif": seller_order_notif}
    else:
        return {}
