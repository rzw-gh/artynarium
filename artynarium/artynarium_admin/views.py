from datetime import datetime, timedelta
from django.db.models import Sum, Q
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from shop import models
from seller import models as seller_model
from users.models import User


@staff_member_required()
def home(request):
    last_week = datetime.today() - timedelta(days=7)
    last_month = datetime.today() - timedelta(days=30)
    month_products = models.Product.objects.filter(create_time__gte=last_month)
    life_time_products = models.Product.objects.all()
    month_visits = 0
    month_sells = 0
    total_sells = 0
    top_selling_products = models.Product.objects.all().order_by('-sold')[:20]
    total_customers = User.objects.all().count()
    total_orders = models.Order.objects.all().count()
    for product in month_products:
        month_visits += product.views
        month_sells += product.sold
    for product in life_time_products:
        total_sells += product.sold
    month_sold = models.SellerOrderItem.objects.filter(create_at__gte=last_month,
                                                    seller_order__order__status="Delivered")
    month_income = 0
    for sold in month_sold:
        month_income += sold.item_pursuant
    month_comment = models.Comment.objects.filter(create_at__gte=last_month).count()
    latest_comments = models.Comment.objects.filter(status="Allowed").order_by("-create_at")[:5]
    latest_tickets = seller_model.Ticket.objects.all().order_by("-create_at")[:5]
    latest_wishlists = models.Wishlist.objects.all().order_by("-added_date")[:6]
    users_count = User.objects.all().count()
    weekly_top_sellers = User.objects.filter(seller=True,
                                            seller_order_items__seller_order__order__status="Delivered",
                                            seller_order_items__seller_order__order__delivered_at__gte=last_week) \
        .annotate(total=Sum('seller_order_items__item_total')).order_by('total')
    weekly_top_buyers = User.objects.filter(Q(user_order__status="Preparing") | Q(user_order__status="OnShipping") | Q(user_order__status="Delivered"))
    context = {
        "month_visits": month_visits,
        "month_sells": month_sells,
        "total_sells": total_sells,
        "total_customers": total_customers,
        "top_selling_products": top_selling_products,
        "total_orders": total_orders,
        "month_income": month_income,
        "month_comment": month_comment,
        "latest_comments": latest_comments,
        "latest_tickets": latest_tickets,
        "latest_wishlists": latest_wishlists,
        "users_count": users_count,
        "weekly_top_sellers": weekly_top_sellers,
        "weekly_top_buyers": weekly_top_buyers
    }
    return render(request, 'artynarium_admin/home.html', context)
