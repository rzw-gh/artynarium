from . import models
from seller import models as seller_model
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from users.models import User
from django.db.models import Q


def cat(request):
    return {"cat": models.Category.objects.all(), "recat": models.Category.objects.filter(parent__isnull=True)}


def wishlist(request):
    if request.user.is_authenticated:
        wishlist_count = models.Wishlist.objects.filter(user=request.user).count()
        return {"wishlist_count": wishlist_count}
    else:
        return {}


def cart(request):
    if request.user.is_authenticated:
        cart_item = models.Cart.objects.filter(user=request.user, out_of_stock=False)
        total = 0
        for t in cart_item:
            if t.product.variant == 'None':
                total += t.amount
            else:
                total += t.varamount
        return {
            "cart_item": cart_item.count(),
            "cart_object": cart_item,
            "cart_object_show_case": cart_item[:3],
            "total_cart_dropdown": total,
        }
    else:
        return {}


def account_notification(request):
    if request.user.is_authenticated:
        account_notification = 0
        account_notification += models.Order.objects.filter(Q(status='Payment') | Q(status='LackOfInventory'), user=request.user).count()
        if request.user.seller:
            account_notification += seller_model.TicketReply.objects.filter(Q(ticket__user=request.user) | Q(ticket__to=request.user), user_status='UnRead').count()
            account_notification += models.SellerOrder.objects.filter(seller=request.user, order__status="Preparing").count()
        return {"account_notification": account_notification}
    else:
        return {}


def pending_pay(request):
    if request.user.is_authenticated:
        pending_pay = models.Order.objects.filter(Q(status='Payment') | Q(status='LackOfInventory'), user=request.user).count()
        return {'pending_pay': pending_pay}
    else:
        return {}


def history_count(request):
    if request.user.is_authenticated and request.user.seller:
        history_count = seller_model.Withdraw.objects.filter(user=request.user).count()
        return {'history_count': history_count}
    else:
        return {}


def viewed_recently(request):
    if request.user.is_authenticated:
        ct = ContentType.objects.get_for_model(models.Product)
        vr1 = models.ObjectViewed.objects.order_by('-timestamp').filter(content_type=ct, user=request.user)[:50]
        try:
            vr_queryset = models.ObjectViewed.objects.none()
            vr_values = vr1.values()
            vr_values_dict = {}
            for ins in vr_values:
                object_id = []
                for keys in vr_values_dict.keys():
                    object_id.append(int(keys.split("-", 1)[1]))
                if ins['object_id'] in object_id:
                    target = ''
                    for key, value in vr_values_dict.items():
                        if int(key.split("-", 1)[1]) == ins['object_id']:
                            target = key
                    if ins['timestamp'] > vr_values_dict[target]:
                        del vr_values_dict[target]
                        vr_values_dict[str(ins['id']) + '-' + str(ins['object_id'])] = ins['timestamp']
                elif not ins['object_id'] in object_id:
                    vr_values_dict[str(ins['id']) + '-' + str(ins['object_id'])] = ins['timestamp']
            for id in vr_values_dict.keys():
                vr_queryset |= models.ObjectViewed.objects.filter(id=int(id[:id.index("-")]))
        except:
            vr_queryset = None
        return {'vr': vr_queryset[:15]}
    else:
        return {}


def balance(request):
    if request.user.is_authenticated and request.user.seller:
        user = get_object_or_404(User, id=request.user.id)
        balance = user.balance
        return {'balance': balance}
    else:
        return {}
