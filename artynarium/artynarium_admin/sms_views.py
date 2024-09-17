from datetime import datetime, timedelta
from django.db.models import Sum, Q
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect

from shop import models
from seller import models as seller_model
from users.models import User
from kavenegar import *

try:
    import json
except ImportError:
    import simplejson as json
from config import sms_configs

sms_api_key = sms_configs.sms_api_key
sms_sender = sms_configs.sms_sender


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


@staff_member_required()
def customer_sms_manager(request):
    orders = models.Order.objects.filter(status="Preparing")
    paginator = Paginator(orders, 12)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    context = {"orders": orders}
    return render(request, 'artynarium_admin/sms/customer_sms_manager.html', context)


@staff_member_required()
def customer_sms_manager_detail(request, id):
    url = request.META.get('HTTP_REFERER')
    sms = models.Sms.objects.filter(order_id=id, category="Customer").order_by("-create_at")
    order = models.Order.objects.get(id=id)
    if request.method == 'POST':
        form = models.SmsForm(request.POST)
        if form.is_valid():

            sms = models.Sms()
            sms.user_id = order.user_id
            sms.order_id = id
            sms.category = "Customer"

            try:
                api = KavenegarAPI(sms_api_key)
                params = {
                    'sender': sms_sender,
                    'receptor': str(order.user.phone_number),
                    'message': str(form.cleaned_data['message_content'])
                }
                response = api.sms_send(params)
                print(response)
                response = response[0]
                sms.message_id = response['messageid']
                sms.message_content = form.cleaned_data['message_content']
                sms.message_status = True if response['status'] == 1 else False
                sms.message_sender = response['sender']
                sms.message_receptor = response['receptor']
                sms.message_data = response['date']
                sms.message_cost = response['cost']
            except APIException as e:
                print(str(e))
                sms.message_api_exception = str(e)
                sms.message_status = False
                sms.save()
            except HTTPException as e:
                print(str(e))
                sms.message_http_exception = str(e)
                sms.message_status = False
                sms.save()
            sms.save()
            messages.success(request, 'پيامك با موفقيت ارسال شد') if sms.message_status else messages.warning(request,
                                                                                                           'ارسال پيامك با خطا مواجه شد')
            return redirect(url)

    context = {"sms": sms, "order": order}
    return render(request, 'artynarium_admin/sms/customer_sms_manager_detail.html', context)


@staff_member_required()
def seller_sms_manager(request):
    seller_order = models.SellerOrder.objects.filter(order__status="Preparing")
    paginator = Paginator(seller_order, 12)
    page = request.GET.get('page')
    seller_order = paginator.get_page(page)
    context = {"seller_order": seller_order}
    return render(request, 'artynarium_admin/sms/seller_sms_manager.html', context)


@staff_member_required()
def seller_sms_manager_detail(request, id):
    url = request.META.get('HTTP_REFERER')
    sms = models.Sms.objects.filter(seller_order_id=id, category="Seller").order_by("-create_at")
    seller_order = models.SellerOrder.objects.get(id=id)
    if request.method == 'POST':
        form = models.SmsForm(request.POST)
        if form.is_valid():

            sms = models.Sms()
            sms.user_id = seller_order.seller_id
            sms.seller_order_id = id
            sms.category = "Seller"

            try:
                api = KavenegarAPI(sms_api_key)
                params = {
                    'sender': sms_sender,
                    'receptor': str(seller_order.seller.phone_number),
                    'message': str(form.cleaned_data['message_content'])
                }
                response = api.sms_send(params)
                response = response[0]
                sms.message_id = response['messageid']
                sms.message_content = form.cleaned_data['message_content']
                sms.message_status = True if response['status'] == 1 else False
                sms.message_sender = response['sender']
                sms.message_receptor = response['receptor']
                sms.message_data = response['date']
                sms.message_cost = response['cost']
            except APIException as e:
                print(str(e))
                sms.message_api_exception = str(e)
                sms.message_status = False
                sms.save()
            except HTTPException as e:
                print(str(e))
                sms.message_http_exception = str(e)
                sms.message_status = False
                sms.save()
            sms.save()
            messages.success(request, 'پيامك با موفقيت ارسال شد') if sms.message_status else messages.warning(request,
                                                                                                              'ارسال پيامك با خطا مواجه شد')
            return redirect(url)
    context = {"sms": sms}
    return render(request, 'artynarium_admin/sms/seller_sms_manager_detail.html', context)


@staff_member_required()
def seller_request_sms_manager(request):
    seller_request = User.objects.filter(request_seller=True, seller=False)
    paginator = Paginator(seller_request, 12)
    page = request.GET.get('page')
    seller_request = paginator.get_page(page)
    context = {"seller_request": seller_request}
    return render(request, 'artynarium_admin/sms/seller_request_sms_manager.html', context)


@staff_member_required()
def seller_request_sms_manager_detail(request, id):
    url = request.META.get('HTTP_REFERER')
    sms = models.Sms.objects.filter(category="Seller_Request").order_by("-create_at")
    seller_request = User.objects.get(id=id)
    if request.method == 'POST':
        form = models.SmsForm(request.POST)
        if form.is_valid():

            sms = models.Sms()
            sms.user_id = id
            sms.category = "Seller_Request"

            try:
                api = KavenegarAPI(sms_api_key)
                params = {
                    'sender': sms_sender,
                    'receptor': str(seller_request.phone_number),
                    'message': str(form.cleaned_data['message_content'])
                }
                response = api.sms_send(params)
                response = response[0]
                sms.message_id = response['messageid']
                sms.message_content = form.cleaned_data['message_content']
                sms.message_status = True if response['status'] == 1 else False
                sms.message_sender = response['sender']
                sms.message_receptor = response['receptor']
                sms.message_data = response['date']
                sms.message_cost = response['cost']
            except APIException as e:
                print(str(e))
                sms.message_api_exception = str(e)
                sms.message_status = False
                sms.save()
            except HTTPException as e:
                print(str(e))
                sms.message_http_exception = str(e)
                sms.message_status = False
                sms.save()
            sms.save()
            messages.success(request, 'پيامك با موفقيت ارسال شد') if sms.message_status else messages.warning(request,
                                                                                                              'ارسال پيامك با خطا مواجه شد')
            return redirect(url)
    context = {"sms": sms, "seller_request": seller_request}
    return render(request, 'artynarium_admin/sms/seller_request_sms_manager_detail.html', context)
