from django.db.models import Avg

from . import scheduler
from blog.models import Post
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.urls import reverse
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,
                              redirect, render)
from django.template.loader import render_to_string
from seller import models as seller_model
from users.forms import UserAddress
from users.models import User, SellerBalance
from zeep import Client
from . import models
from .signals import object_viewed_signal
from kavenegar import *

try:
    import json
except ImportError:
    import simplejson as json
from config import sms_configs
from config import payment_configs

sms_api_key = sms_configs.sms_api_key
sms_sender = sms_configs.sms_sender

MERCHANT = payment_configs.MERCHANT
client = payment_configs.client
CallbackURL = payment_configs.CallbackURL


def is_valid_queryparam(param):
    return param != '' and param is not None


def home(request):
    test = models.Product.objects.annotate()

    topslider = models.Product.objects.slider().filter(status='Active')
    featured = models.Product.objects.featured().filter(status='Active')
    special = models.Product.objects.special().filter(status='Active')
    latest = models.Product.objects.filter(status='Active').order_by('-create_time')[:12]
    blog = Post.objects.order_by('-create_time')[:8]
    categ = models.Category.objects.filter(parent__isnull=True).order_by('-create_time')[:3]
    most_viewed = models.Product.objects.filter(status='Active').order_by('-views')[:10]
    most_viewed_cat_0 = None
    if categ:
        most_viewed_cat_0 = models.Product.objects.filter(category__id=categ[0].id, status='Active').order_by('-views')[
                            :10]
    most_viewed_cat_1 = None
    if categ.count() > 1:
        most_viewed_cat_1 = models.Product.objects.filter(category__id=categ[1].id, status='Active').order_by('-views')[
                            :10]
    most_viewed_cat_2 = None
    if categ.count() > 2:
        most_viewed_cat_2 = models.Product.objects.filter(category__id=categ[2].id, status='Active').order_by('-views')[
                            :10]

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
            vr_queryset = vr_queryset[:15]
        except:
            vr_queryset = None
    else:
        vr_queryset = None

    context = {
        'topslider': topslider,
        'featured': featured,
        'special': special,
        'latest': latest,
        'most_viewed': most_viewed,
        'most_viewed_cat_0': most_viewed_cat_0,
        'most_viewed_cat_1': most_viewed_cat_1,
        'most_viewed_cat_2': most_viewed_cat_2,
        'blog': blog,
        'categ': categ,
        'vr': vr_queryset,
        "instagram_profile_name": "spacex"
    }

    if request.user.is_authenticated:
        context.update({})

    return render(request, 'shop/home.html', context)


def shop(request):
    qs = models.Product.objects.filter(status='Active')
    brand = models.Brand.objects.filter(pbrand__in=qs).distinct()
    maincat = models.Category.objects.filter(parent__isnull=True).distinct()

    qs1 = None
    qs2 = None
    qs3 = None

    search = request.GET.get('search')
    Art = request.GET.get('Art')
    Material = request.GET.get('Material')
    Tool = request.GET.get('Tool')
    View = request.GET.get('View')
    Date = request.GET.get('Date')
    Cat = request.GET.get('Cat')
    Brand = request.GET.get('Brand')

    if is_valid_queryparam(search):
        qs = qs.filter(name__icontains=search).distinct()

    if is_valid_queryparam(Art):
        qs1 = qs.filter(product_type='Art').distinct()

    if is_valid_queryparam(Material):
        qs2 = qs.filter(product_type='Material').distinct()

    if is_valid_queryparam(Tool):
        qs3 = qs.filter(product_type='Tool').distinct()

    if qs1 is not None:
        if qs2 is not None:
            qs = qs1 | qs2
            if qs3 is not None:
                qs = qs | qs3
        elif qs3 is not None:
            qs = qs1 | qs3
        else:
            qs = qs1
    elif qs2 is not None:
        if qs3 is not None:
            qs = qs2 | qs3
        else:
            qs = qs2
    elif qs3 is not None:
        qs = qs3
    else:
        qs = qs

    if is_valid_queryparam(Cat):
        qs = qs.filter(category__id=Cat).distinct()

    if is_valid_queryparam(Brand):
        qs = qs.filter(brand__id=Brand).distinct()

    if is_valid_queryparam(View):
        qs = qs.order_by('-views')

    if Date == '2':
        qs = qs.order_by('create_time')

    elif Date == '1':
        qs = qs.order_by('-create_time')

    qs_count = qs.count()

    paginator = Paginator(qs, 12)
    page = request.GET.get('page')
    qs = paginator.get_page(page)

    current_cat = request.GET.get('Cat')
    if current_cat:
        current_cat = models.Category.objects.get(id=current_cat)

    current_brand = request.GET.get('Brand')
    if current_brand:
        current_brand = models.Brand.objects.get(id=current_brand)

    context = {
        'products': qs,
        'products_count': qs_count,
        'maincat': maincat,
        'brand': brand,
        'current_cat': current_cat,
        'current_brand': current_brand,
        'full_path': request.build_absolute_uri(),
        'search': search,
    }
    return render(request, 'shop/shop.html', context)


def featured(request):
    qs = models.Product.objects.featured().filter(status='Active')
    brand = models.Brand.objects.filter(pbrand__in=qs).distinct()
    maincat = models.Category.objects.filter(parent__isnull=True, catproduct__in=qs).distinct()

    qs1 = None
    qs2 = None
    qs3 = None

    search = request.GET.get('search')
    Art = request.GET.get('Art')
    Material = request.GET.get('Material')
    Tool = request.GET.get('Tool')
    View = request.GET.get('View')
    Date = request.GET.get('Date')
    Cat = request.GET.get('Cat')
    Brand = request.GET.get('Brand')

    if is_valid_queryparam(search):
        qs = qs.filter(name__icontains=search).distinct()

    if is_valid_queryparam(Art):
        qs1 = qs.filter(product_type='Art').distinct()

    if is_valid_queryparam(Material):
        qs2 = qs.filter(product_type='Material').distinct()

    if is_valid_queryparam(Tool):
        qs3 = qs.filter(product_type='Tool').distinct()

    if qs1 is not None:
        if qs2 is not None:
            qs = qs1 | qs2
            if qs3 is not None:
                qs = qs | qs3
        elif qs3 is not None:
            qs = qs1 | qs3
        else:
            qs = qs1
    elif qs2 is not None:
        if qs3 is not None:
            qs = qs2 | qs3
        else:
            qs = qs2
    elif qs3 is not None:
        qs = qs3
    else:
        qs = qs

    if is_valid_queryparam(Cat):
        qs = qs.filter(category__id=Cat).distinct()

    if is_valid_queryparam(Brand):
        qs = qs.filter(brand__id=Brand).distinct()

    if is_valid_queryparam(View):
        qs = qs.order_by('-views')

    if Date == '2':
        qs = qs.order_by('create_time')

    elif Date == '1':
        qs = qs.order_by('-create_time')

    qs_count = qs.count()

    paginator = Paginator(qs, 12)
    page = request.GET.get('page')
    qs = paginator.get_page(page)

    current_cat = request.GET.get('Cat')
    if current_cat:
        current_cat = models.Category.objects.get(id=current_cat)

    current_brand = request.GET.get('Brand')
    if current_brand:
        current_brand = models.Brand.objects.get(id=current_brand)

    context = {
        'products': qs,
        'products_count': qs_count,
        'maincat': maincat,
        'brand': brand,
        'current_cat': current_cat,
        'current_brand': current_brand,
        'full_path': request.build_absolute_uri(),
        'search': search,
    }
    return render(request, 'shop/featured.html', context)


def special(request):
    qs = models.Product.objects.special().filter(status='Active')
    brand = models.Brand.objects.filter(pbrand__in=qs).distinct()
    maincat = models.Category.objects.filter(parent__isnull=True, catproduct__in=qs).distinct()
    qs1 = None
    qs2 = None
    qs3 = None

    search = request.GET.get('search')
    Art = request.GET.get('Art')
    Material = request.GET.get('Material')
    Tool = request.GET.get('Tool')
    View = request.GET.get('View')
    Date = request.GET.get('Date')
    Cat = request.GET.get('Cat')
    Brand = request.GET.get('Brand')

    if is_valid_queryparam(search):
        qs = qs.filter(name__icontains=search).distinct()

    if is_valid_queryparam(Art):
        qs1 = qs.filter(product_type='Art').distinct()

    if is_valid_queryparam(Material):
        qs2 = qs.filter(product_type='Material').distinct()

    if is_valid_queryparam(Tool):
        qs3 = qs.filter(product_type='Tool').distinct()

    if qs1 is not None:
        if qs2 is not None:
            qs = qs1 | qs2
            if qs3 is not None:
                qs = qs | qs3
        elif qs3 is not None:
            qs = qs1 | qs3
        else:
            qs = qs1
    elif qs2 is not None:
        if qs3 is not None:
            qs = qs2 | qs3
        else:
            qs = qs2
    elif qs3 is not None:
        qs = qs3
    else:
        qs = qs

    if is_valid_queryparam(Cat):
        qs = qs.filter(category__id=Cat).distinct()

    if is_valid_queryparam(Brand):
        qs = qs.filter(brand__id=Brand).distinct()

    if is_valid_queryparam(View):
        qs = qs.order_by('-views')

    if Date == '2':
        qs = qs.order_by('create_time')

    elif Date == '1':
        qs = qs.order_by('-create_time')

    qs_count = qs.count()

    current_cat = request.GET.get('Cat')
    if current_cat:
        current_cat = models.Category.objects.get(id=current_cat)

    current_brand = request.GET.get('Brand')
    if current_brand:
        current_brand = models.Brand.objects.get(id=current_brand)

    paginator = Paginator(qs, 12)
    page = request.GET.get('page')
    qs = paginator.get_page(page)

    context = {
        'products': qs,
        'products_count': qs_count,
        'maincat': maincat,
        'brand': brand,
        'current_cat': current_cat,
        'current_brand': current_brand,
        'full_path': request.build_absolute_uri(),
        'search': search,
    }
    return render(request, 'shop/special.html', context)


def search(request):
    if request.method == 'POST':
        form = models.SearchForm(request.POST)
        if form.is_valid():
            autos = form.cleaned_data['autos']
            # catid = form.cleaned_data['catid']
            # if catid == 0:
            #     products = models.Product.objects.filter(name__icontains=autos, status='Active')
            #     count = products.count()
            # else:
            products = models.Product.objects.filter(
                name__contains=autos, status='Active')  # category_id=catid
            count = products.count()

            paginator = Paginator(products, 12)
            page = request.GET.get('page')
            products = paginator.get_page(page)
            category = models.Category.objects.all()
            context = {
                'products': products,
                'count': count,
                'query': autos,
                'category': category,
            }
            return render(request, 'shop/search.html', context)
    return HttpResponseRedirect('/')


def autocomplete(request):
    if 'term' in request.GET:
        qs = models.Product.objects.filter(
            name__icontains=request.GET.get('term'), status='Active')[:5]
        names = list()
        for product in qs:
            names.append(product.name)
        return JsonResponse(names, safe=False)
    return redirect('/')


def product(request, id, slug):
    url = request.META.get('HTTP_REFERER')

    # check cart variant
    delete_cart_id = []
    for item in models.Cart.objects.filter(user_id=request.user.id):
        if models.Product.objects.get(id=item.product.id).variant == 'None' and item.variant:
            delete_cart_id.append(item.id)
    if len(delete_cart_id) > 0:
        models.Cart.objects.filter(id__in=delete_cart_id).delete()
        return redirect(url)

    if models.Product.objects.get(id=id).status != 'Draft' or models.Product.objects.get(id=id).status != 'Disabled':
        context = {}
        query = request.GET.get('q')
        product = get_object_or_404(models.Product, pk=id)
        if product.multi_seller:
            other_sellers = models.Product.objects.filter(name=product.name).exclude(id=product.id)[:2]
            context.update({'other_sellers': other_sellers})
        precat = product.category.all().get_ancestors(include_self=True)
        if request.user.is_authenticated:
            if product:
                object_viewed_signal.send(
                    product, instance=product, request=request)  # product viewed
        product.views += 1
        product.save()
        images = models.Images.objects.filter(product_id=id).order_by('id')[:4]
        related_products = models.Product.objects.filter(category__id=precat.last().id, status='Active').exclude(
            id=id).order_by('id')[:10]
        comments = models.Comment.objects.filter(product_id=id, status='Allowed', parent=None)
        next_product = models.Product.objects.filter(category__id=precat.last().id, id__gt=product.id,
                                                     status='Active').order_by('id').first()
        prev_product = models.Product.objects.filter(category__id=precat.last().id, id__lt=product.id,
                                                     status='Active').order_by('-id').first()
        store_amount_is_empty = False
        if product.store_amount == 0:
            store_amount_is_empty = True
        context.update({
            'product': product,
            'related_products': related_products,
            'store_amount_is_empty': store_amount_is_empty,
            'precat': precat,
            'images': images,
            'comments': comments,
            'next_product': next_product,
            'prev_product': prev_product,
            'full_path': request.build_absolute_uri(),
        })
        if product.variant != "None":  # Product have variants
            if request.method == 'POST':  # if we select color
                variant_id = request.POST.get('variantid')
                # selected product by click color radio
                variant = models.Variants.objects.get(id=variant_id)
                colors = models.Variants.objects.filter(
                    product_id=id, size_id=variant.size_id)

                sizes = models.Variants.objects.filter(product_id=id)
                try:
                    sizes_queryset = models.Variants.objects.none()
                    sizes_values = sizes.values()
                    sizes_values_dict = {}
                    for ins in sizes_values:
                        if not int(ins['size_id']) in sizes_values_dict.values():
                            sizes_values_dict[str(ins['id'])] = int(ins['size_id'])
                    for id_key in sizes_values_dict.keys():
                        sizes_queryset |= models.Variants.objects.filter(id=int(id_key))
                    sizes = sizes_queryset
                except:
                    sizes = sizes

                query += variant.title + 'Size:' + str(
                    variant.size) + 'Color:' + str(variant.color)
            else:
                variants = models.Variants.objects.filter(product_id=id)
                colors = models.Variants.objects.filter(
                    product_id=id, size_id=variants[0].size_id)

                sizes = models.Variants.objects.filter(product_id=id)
                try:
                    sizes_queryset = models.Variants.objects.none()
                    sizes_values = sizes.values()
                    sizes_values_dict = {}
                    for ins in sizes_values:
                        if not int(ins['size_id']) in sizes_values_dict.values():
                            sizes_values_dict[str(ins['id'])] = int(ins['size_id'])
                    for id_key in sizes_values_dict.keys():
                        sizes_queryset |= models.Variants.objects.filter(id=int(id_key))
                    sizes = sizes_queryset
                except:
                    sizes = sizes

                variant = models.Variants.objects.get(id=variants[0].id)
            variant_store_amount_is_empty = False
            if variant.quantity == 0:
                variant_store_amount_is_empty = True
            context.update({
                'sizes': sizes,
                'colors': colors,
                'variant': variant,
                'variant_store_amount_is_empty': variant_store_amount_is_empty,
                'query': query
            })
        # check if item is in the cart
        in_cart = False
        context.update({'in_cart': in_cart})
        if models.Cart.objects.filter(product_id=id, user_id=request.user.id, out_of_stock=False).exists():
            in_cart = True  # The product is in the cart
            context.update({'in_cart': in_cart})
            cart_limit = models.CartLimit.objects.get(product_id=id, user_id=request.user.id)

            if cart_limit.first_purchase_store_amount_limit != product.purchase_store_amount_limit:
                diff = product.purchase_store_amount_limit - cart_limit.first_purchase_store_amount_limit
                cart_limit.first_purchase_store_amount_limit = product.purchase_store_amount_limit
                cart_limit.purchase_store_amount_limit += diff
                cart_limit.save()

            if cart_limit.first_purchase_amount_limit != product.purchase_amount_limit:
                diff = product.purchase_amount_limit - cart_limit.first_purchase_amount_limit
                cart_limit.first_purchase_amount_limit = product.purchase_amount_limit
                cart_limit.purchase_amount_limit += diff
                cart_limit.save()

            cart_limit_purchase_amount_limit = 0 if cart_limit.purchase_amount_limit < 0 else cart_limit.purchase_amount_limit
            cart_limit_purchase_store_amount_limit = 0 if cart_limit.purchase_store_amount_limit < 0 else cart_limit.purchase_store_amount_limit
            context.update({
                'cart_limit': cart_limit,
                'cart_limit_purchase_amount_limit': cart_limit_purchase_amount_limit,
                'cart_limit_purchase_store_amount_limit': cart_limit_purchase_store_amount_limit
            })
    else:
        raise Http404
    return render(request, 'shop/product.html', context)


def ajaxcolor(request):
    data = {}
    if request.POST.get('action') == 'post':
        size_id = request.POST.get('size')
        productid = request.POST.get('productid')
        colors = models.Variants.objects.filter(
            product_id=productid, size_id=size_id)
        context = {
            'size_id': size_id,
            'productid': productid,
            'colors': colors,
        }
        data = {'rendered_table': render_to_string(
            'shop/color_list.html', context=context)}
        return JsonResponse(data)
    return JsonResponse(data)


@login_required
def addcomment(request, id):
    product = models.Product.objects.get(id=id)
    user_order_items = models.OrderItem.objects.filter(product=product, order__status='Delivered', out_of_stock=False)
    url = request.META.get('HTTP_REFERER')  # get last url
    if request.method == 'POST':
        form = models.CommentForm(request.POST)
        parent_obj = None
        if form.is_valid():
            try:
                parent_id = int(request.POST.get("parent_id"))
            except:
                parent_id = None
            if parent_id:
                parent_qs = models.Comment.objects.filter(id=parent_id)
                if parent_qs.exists() and parent_qs.count() == 1:
                    parent_obj = parent_qs[0]

            data = models.Comment()
            data.subject = form.cleaned_data['subject']
            data.comment = form.cleaned_data['comment']
            data.rate = form.cleaned_data['rate']
            data.ip = request.META.get('REMOTE_ADDR')
            data.product_id = id
            current_user = request.user
            data.user_id = current_user.id
            data.parent = parent_obj
            if user_order_items.exists():
                data.buyer = True
            data.save()

            seller_acc = User.objects.get(id=product.user.id)
            if user_order_items.exists():
                reviews = models.Comment.objects.filter(
                    product_id=product.id, status='Allowed', parent=None, buyer=True).aggregate(
                    users_rate=Avg('rate'))
                avg = 0
                if reviews["users_rate"] is not None:
                    avg = float(reviews["users_rate"]) * 100 / 5
                    seller_acc.users_rate = avg
            reviews = models.Comment.objects.filter(product_id=product.id, status='Allowed', parent=None).aggregate(
                rate=Avg('rate'))
            avg = 0
            if reviews["rate"] is not None:
                avg = float(reviews["rate"]) * 100 / 5
                seller_acc.rate = avg
            seller_acc.save()
            messages.success(request, "با تشکر. نظر شما ارسال شد")
            return HttpResponseRedirect(url)

    return HttpResponseRedirect(url)


@login_required
def comment_upvote(request, id):
    url = request.META.get('HTTP_REFERER')  # get last url
    if models.CommentUpVote.objects.filter(comment__id=id, user=request.user).exists():
        data = models.Comment.objects.get(id=id)
        data.helpful -= 1
        data.save()
        models.CommentUpVote.objects.get(comment__id=id).delete()
        if request.is_ajax:
            json_data = {'likecount': data.helpful}
            return JsonResponse(json_data)
    else:
        data = models.Comment.objects.get(id=id)
        data.helpful += 1
        data.save()
        user = models.CommentUpVote()
        user.comment_id = id
        user.user = request.user
        user.upVoted = True
        user.save()
        if request.is_ajax:
            json_data = {'likecount': data.helpful}
            return JsonResponse(json_data)
    return HttpResponseRedirect(url)


def cat(request):
    cate = models.Category.objects.filter(parent__isnull=True)
    context = {'cate': cate}
    return render(request, 'shop/cat.html', context)


def category(request, id, slug):
    catchild = models.Category.objects.get(id=id, slug=slug).get_descendants(include_self=False)
    catdata = models.Category.objects.get(id=id, slug=slug)
    qs = catdata.catproduct.all()

    color = models.Variants.objects.filter(product__in=qs, color__isnull=False)
    try:
        sizes_queryset = models.Variants.objects.none()
        sizes_values = color.values()
        sizes_values_dict = {}
        for ins in sizes_values:
            if not int(ins['color_id']) in sizes_values_dict.values():
                sizes_values_dict[str(ins['id'])] = int(ins['color_id'])
        for id_key in sizes_values_dict.keys():
            sizes_queryset |= models.Variants.objects.filter(id=int(id_key))
        color = sizes_queryset
    except:
        color = color

    size = models.Variants.objects.filter(product_id=id)
    try:
        sizes_queryset = models.Variants.objects.none()
        sizes_values = size.values()
        sizes_values_dict = {}
        for ins in sizes_values:
            if not int(ins['size_id']) in sizes_values_dict.values():
                sizes_values_dict[str(ins['id'])] = int(ins['size_id'])
        for id_key in sizes_values_dict.keys():
            sizes_queryset |= models.Variants.objects.filter(id=int(id_key))
        size = sizes_queryset
    except:
        size = size

    brand = models.Brand.objects.filter(pbrand__in=qs).distinct()

    qs1 = None
    qs2 = None
    qs3 = None

    search = request.GET.get('search')
    Art = request.GET.get('Art')
    Material = request.GET.get('Material')
    Tool = request.GET.get('Tool')
    View = request.GET.get('View')
    Date = request.GET.get('Date')

    selected_color = request.GET.get('selected_color')
    if selected_color:
        selected_color = models.Color.objects.get(id=int(selected_color))

    selected_size = request.GET.get('selected_size')
    if selected_size:
        selected_size = models.Size.objects.get(id=int(selected_size))

    selected_brand = request.GET.get('selected_brand')
    if selected_brand:
        selected_brand = models.Brand.objects.get(id=int(selected_brand))

    if is_valid_queryparam(search):
        qs = qs.filter(name__icontains=search).distinct()

    if is_valid_queryparam(Art):
        qs1 = qs.filter(product_type='Art').distinct()

    if is_valid_queryparam(Material):
        qs2 = qs.filter(product_type='Material').distinct()

    if is_valid_queryparam(Tool):
        qs3 = qs.filter(product_type='Tool').distinct()

    if qs1 is not None:
        if qs2 is not None:
            qs = qs1 | qs2
            if qs3 is not None:
                qs = qs | qs3
        elif qs3 is not None:
            qs = qs1 | qs3
        else:
            qs = qs1
    elif qs2 is not None:
        if qs3 is not None:
            qs = qs2 | qs3
        else:
            qs = qs2
    elif qs3 is not None:
        qs = qs3
    else:
        qs = qs

    if is_valid_queryparam(selected_brand):
        qs = qs.filter(brand__id=selected_brand.id).distinct()

    if is_valid_queryparam(selected_color):
        qs = qs.filter(vars__color__id=selected_color.id).distinct()

    if is_valid_queryparam(selected_size):
        qs = qs.filter(vars__size=selected_size).distinct()

    if is_valid_queryparam(View):
        qs = qs.order_by('-views')

    if Date == '2':
        qs = qs.order_by('create_time')

    elif Date == '1':
        qs = qs.order_by('-create_time')

    qs_count = qs.count()

    paginator = Paginator(qs, 12)
    page = request.GET.get('page')
    qs = paginator.get_page(page)

    context = {
        'catdata': catdata,
        'catchild': catchild,
        'products': qs,
        'products_count': qs_count,
        'color': color,
        'size': size,
        'selected_size': selected_size,
        'selected_color': selected_color,
        'selected_brand': selected_brand,
        'brand': brand,
        'full_path': request.build_absolute_uri(),
        'search': search,
    }
    return render(request, 'shop/category.html', context)


@login_required
def wishlist(request):
    wishlist = models.Wishlist.objects.filter(
        user=request.user).order_by('-added_date')
    paginator = Paginator(wishlist, 12)
    page = request.GET.get('page')
    wishlist = paginator.get_page(page)
    return render(request, 'shop/wishlist.html', {'wishlist': wishlist})


@login_required
def wishlist_add_remove(request, id, slug):
    product = get_object_or_404(models.Product, id=id)
    wished = models.Wishlist.objects.filter(user=request.user, wished_item=product)
    if wished:
        wished.delete()
        messages.success(request, 'ایتم از لیست علاقه مندی شما حذف شد')
        return redirect('shop:product', id=id, slug=slug)
    else:
        try:
            wished_list = models.Wishlist.objects.create(wished_item=product, user=request.user)
            messages.success(request, 'ایتم به لیست علاقه مندی شما اضافه شد')
        except:
            messages.warning(
                request, "ایتم هم اکنون در لیست علاقه مندی شما میباشد")
        return redirect('shop:product', id=id, slug=slug)


@login_required
def account_security(request):
    return render(request, 'shop/account_security.html')


@login_required()
def my_orders(request):
    order_qs = models.Order.objects.filter(user=request.user).order_by('-create_at')
    paginator = Paginator(order_qs, 8)
    page = request.GET.get('page')
    order_qs = paginator.get_page(page)
    return render(request, 'shop/my_orders.html', {"order": order_qs})


@login_required()
def my_order_detail(request, id):
    order = get_object_or_404(models.Order, id=id, user=request.user)
    order_item = models.OrderItem.objects.filter(order_id=id, user=request.user, out_of_stock=False)
    context = {
        'order': order,
        'order_item': order_item,
    }
    return render(request, 'shop/my_order_detail.html', context)


@login_required()
def edit_address(request):
    url = request.META.get('HTTP_REFERER')
    if request.method == 'POST':
        if 'address_submit' in request.POST:
            form = UserAddress(request.POST, instance=request.user)
            if form.is_valid():
                form.first_name = form.cleaned_data['first_name']
                form.last_name = form.cleaned_data['last_name']
                form.state = form.cleaned_data['state']
                form.city = form.cleaned_data['city']
                form.address = form.cleaned_data['address']
                form.zipcode = form.cleaned_data['zipcode']
                form.phone_number = form.cleaned_data['phone_number']
                form.save()
                messages.success(request, 'حساب شما با موفقیت به روز رسانی شد')
                return redirect(url)
            else:
                messages.warning(request, form.errors)
        elif 'payback_submit' in request.POST:
            user_obj = User.objects.get(id=request.user.id)
            if user_obj.activate_payback:
                if len(request.POST.get('card_number')) == 16:
                    user_obj.card_number = request.POST.get('card_number')
                    user_obj.save()
                    messages.success(request, 'شماره كارت شما با موفقيت ثبت شد')
                    return redirect(url)
                else:
                    messages.warning(request, 'شماره كارت بايد 16 رقمي باشد')
            else:
                messages.warning(request, 'درخواست غير مجاز')
    return render(request, 'shop/edit_address.html')


def contact(request):
    if request.user.is_authenticated:
        data = {'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'phone_number': request.user.phone_number,
                'email': request.user.email
                }
        if request.method == 'POST':
            form = models.ContactForm(request.POST)
            if form.is_valid():
                data = models.Contact()
                data.first_name = form.cleaned_data['first_name']
                data.last_name = form.cleaned_data['last_name']
                data.phone_number = form.cleaned_data['phone_number']
                data.email = form.cleaned_data['email']
                data.ip = request.META.get('REMOTE_ADDR')
                data.subject = form.cleaned_data['subject']
                data.text = form.cleaned_data['text']
                data.save()
                messages.success(
                    request,
                    'با تشکر از شما. به زودی از طریق ایمیل و یا شماره همراهی که وارد کردید با شما تماس گرفته خواهد شد')
                return redirect('shop:contact')
            else:
                messages.success(request, form.errors)
        else:
            form = models.ContactForm(initial=data)

        return render(request, 'shop/contact.html', {'form': form})
    else:
        if request.method == 'POST':
            form = models.ContactForm(request.POST)
            if form.is_valid():
                data = models.Contact()
                data.first_name = form.cleaned_data['first_name']
                data.last_name = form.cleaned_data['last_name']
                data.phone_number = form.cleaned_data['phone_number']
                data.email = form.cleaned_data['email']
                data.ip = request.META.get('REMOTE_ADDR')
                data.subject = form.cleaned_data['subject']
                data.text = form.cleaned_data['text']
                data.save()
                form = models.ContactForm()
                messages.success(
                    request,
                    'با تشکر از شما. به زودی از طریق ایمیل و یا شماره همراهی که وارد کردید با شما تماس گرفته خواهد شد')
                return redirect('shop:contact')
            else:
                messages.success(request, form.errors)
        else:
            form = models.ContactForm()

        return render(request, 'shop/contact.html', {'form': form})


def entry_not_found(request, exception, template_name='error/404.html'):
    return render(request, template_name)


def instagram(request):
    return render(request, 'shop/instagram.html', {"instagram_profile_name": "spacex"})


@login_required
def cart(request):
    url = request.META.get('HTTP_REFERER')
    context = {}

    # check cart variant
    delete_cart_id = []
    for item in models.Cart.objects.filter(user_id=request.user.id):
        if models.Product.objects.get(id=item.product.id).variant == 'None' and item.variant:
            delete_cart_id.append(item.id)
    if len(delete_cart_id) > 0:
        models.Cart.objects.filter(id__in=delete_cart_id).delete()
        return redirect(url)

    # check inventory
    reorder_products_info_list = []  # cart ID, lack, requested
    for item in models.Cart.objects.filter(user_id=request.user.id, out_of_stock=False):
        reorder_products_info = []
        product = models.Product.objects.get(id=item.product.id)
        cart_limit = models.CartLimit.objects.get(product_id=product.id, user_id=request.user.id)

        if cart_limit.first_purchase_store_amount_limit != product.purchase_store_amount_limit:
            diff = product.purchase_store_amount_limit - cart_limit.first_purchase_store_amount_limit
            cart_limit.first_purchase_store_amount_limit = product.purchase_store_amount_limit
            cart_limit.purchase_store_amount_limit += diff
            cart_limit.save()

        if cart_limit.first_purchase_amount_limit != product.purchase_amount_limit:
            diff = product.purchase_amount_limit - cart_limit.first_purchase_amount_limit
            cart_limit.first_purchase_amount_limit = product.purchase_amount_limit
            cart_limit.purchase_amount_limit += diff
            cart_limit.save()

        purchase_store_amount_limit = cart_limit.purchase_store_amount_limit
        purchase_amount_limit = cart_limit.purchase_amount_limit

        if item.variant:
            variant = models.Variants.objects.get(id=item.variant.id)
            if item.from_store_amount and (variant.quantity < item.quantity or purchase_store_amount_limit < 0):
                lack = 0
                if variant.quantity < item.quantity:
                    lack += item.quantity - variant.quantity
                if purchase_store_amount_limit < 0:
                    lack += purchase_store_amount_limit * -1
                    cart_limit.purchase_store_amount_limit = 0
                    cart_limit.save()

                reorder_products_info.append(item.id)
                reorder_products_info.append(lack)
                reorder_products_info.append(item.quantity)
            elif item.from_amount and (variant.seller_quantity < item.quantity or purchase_amount_limit < 0):
                lack = 0
                if variant.seller_quantity < item.quantity:
                    lack += item.quantity - variant.seller_quantity
                if purchase_amount_limit < 0:
                    lack += purchase_amount_limit * -1
                    cart_limit.purchase_amount_limit = 0
                    cart_limit.save()

                reorder_products_info.append(item.id)
                reorder_products_info.append(lack)
                reorder_products_info.append(item.quantity)
        else:
            if item.from_store_amount and (product.store_amount < item.quantity or purchase_store_amount_limit < 0):
                lack = 0
                if product.store_amount < item.quantity:
                    lack += item.quantity - product.store_amount
                if purchase_store_amount_limit < 0:
                    lack += purchase_store_amount_limit * -1
                    cart_limit.purchase_store_amount_limit = 0
                    cart_limit.save()

                reorder_products_info.append(item.id)
                reorder_products_info.append(lack)
                reorder_products_info.append(item.quantity)
            elif item.from_amount and (product.amount < item.quantity or purchase_amount_limit < 0):
                lack = 0
                if product.amount < item.quantity:
                    lack += item.quantity - product.amount
                if purchase_amount_limit < 0:
                    lack += purchase_amount_limit * -1
                    cart_limit.purchase_amount_limit = 0
                    cart_limit.save()

                reorder_products_info.append(item.id)
                reorder_products_info.append(lack)
                reorder_products_info.append(item.quantity)
        if len(reorder_products_info) > 0:
            reorder_products_info_list.append(reorder_products_info)

    if len(reorder_products_info_list) > 0:  # decrease cart quantity
        context.update({'reorder': 1})
        for order_item in reorder_products_info_list:
            cart_ins = models.Cart.objects.get(id=order_item[0])
            cart_ins.quantity = order_item[2] - order_item[1]
            if cart_ins.quantity <= 0:
                cart_ins.quantity = 0
                cart_ins.out_of_stock = True
                cart_limit_relation = models.CartLimit.objects.get(product=cart_ins.product, user=request.user)
                cart_limit_relation.cart.remove(cart_ins)
                if cart_limit_relation.cart.all().count() == 0:
                    cart_limit_relation.delete()
            cart_ins.save()

    total_cost = 0
    cart = models.Cart.objects.filter(user_id=request.user.id).order_by('-create_at')
    for t in cart:
        if t.product.variant == 'None':
            total_cost += t.amount
        else:
            total_cost += t.varamount
    context.update({
        'cart': cart,
        'total_cost': total_cost,
    })
    return render(request, 'shop/cart.html', context)


@login_required
def ajax_cart_amount(request, id):
    type = request.GET.get('type')

    # check limit
    cart = get_object_or_404(models.Cart, id=id, user=request.user.id, out_of_stock=False)
    product = models.Product.objects.get(id=cart.product.id)
    cart_limit = models.CartLimit.objects.get(product_id=product.id, user_id=request.user.id)

    if cart_limit.first_purchase_store_amount_limit != product.purchase_store_amount_limit:
        diff = product.purchase_store_amount_limit - cart_limit.first_purchase_store_amount_limit
        cart_limit.first_purchase_store_amount_limit = product.purchase_store_amount_limit
        cart_limit.purchase_store_amount_limit += diff
        cart_limit.save()

    if cart_limit.first_purchase_amount_limit != product.purchase_amount_limit:
        diff = product.purchase_amount_limit - cart_limit.first_purchase_amount_limit
        cart_limit.first_purchase_amount_limit = product.purchase_amount_limit
        cart_limit.purchase_amount_limit += diff
        cart_limit.save()

    purchase_store_amount_limit = cart_limit.purchase_store_amount_limit
    purchase_amount_limit = cart_limit.purchase_amount_limit

    if cart.variant:
        variant = models.Variants.objects.get(id=cart.variant.id)
        if cart.from_store_amount:
            if (variant.quantity - cart_limit.total_variant_quantity) >= purchase_store_amount_limit:
                max_increment = purchase_store_amount_limit
            else:
                max_increment = variant.quantity - cart_limit.total_variant_quantity
        elif cart.from_amount:
            if (variant.seller_quantity - cart_limit.total_variant_seller_quantity) >= purchase_amount_limit:
                max_increment = purchase_amount_limit
            else:
                max_increment = variant.seller_quantity - cart_limit.total_variant_seller_quantity
    else:
        if cart.from_store_amount:
            if (product.store_amount - cart_limit.total_product_store_amount) >= purchase_store_amount_limit:
                max_increment = purchase_store_amount_limit
            else:
                max_increment = product.store_amount - cart_limit.total_product_store_amount
        elif cart.from_amount:
            if (product.amount - cart_limit.total_product_amount) >= purchase_amount_limit:
                max_increment = purchase_amount_limit
            else:
                max_increment = product.amount - cart_limit.total_product_amount
    data = {}
    if max_increment < 0:
        data.update({'reload': '1'})
    else:
        if max_increment > 0 and type == 'increment':
            current_quantity = cart.quantity
            cart.quantity += 1
            cart.save()

            total_cost = 0
            cart_loop = models.Cart.objects.filter(user_id=request.user.id)
            for t in cart_loop:
                if t.product.variant == 'None':
                    total_cost += t.amount
                else:
                    total_cost += t.varamount

            data.update({
                'updated_quantity': current_quantity + 1,
                'updated_total_cost': total_cost,
                'updated_product_total_cost': cart.varamount if product.variant != 'None' else cart.amount
            })

            if cart_limit.store_amount_type:
                cart_limit.purchase_store_amount_limit -= 1
            else:
                cart_limit.purchase_amount_limit -= 1
            cart_limit.save()
        elif type == 'decrement' and cart.quantity > 1:
            current_quantity = cart.quantity
            cart.quantity -= 1
            cart.save()
            data.update({'updated_quantity': current_quantity - 1})

            total_cost = 0
            cart_loop = models.Cart.objects.filter(user_id=request.user.id, out_of_stock=False)
            for t in cart_loop:
                if t.product.variant == 'None':
                    total_cost += t.amount
                else:
                    total_cost += t.varamount

            data.update({
                'updated_total_cost': total_cost,
                'updated_product_total_cost': cart.varamount if product.variant != 'None' else cart.amount
            })
            if cart_limit.store_amount_type:
                cart_limit.purchase_store_amount_limit += 1
            else:
                cart_limit.purchase_amount_limit += 1
            cart_limit.save()
        elif max_increment == 0 and type == 'increment':
            data.update({'limit_reached': '1'})

    return JsonResponse(data)


@login_required
def out_of_stock_reorder(request, id):
    cart = get_object_or_404(models.Cart, id=id, user=request.user)
    try:
        cart_limit_relation = models.CartLimit.objects.get(product=cart.product, user=request.user)
        cart_limit_relation.cart.remove(cart)
        if cart_limit_relation.cart.all().count() == 0:
            cart_limit_relation.delete()
    except:
        pass
    cart.delete()
    return redirect("shop:product", id=cart.product.id, slug=cart.product.slug)


@login_required
def addtocart(request, id):
    url = request.META.get('HTTP_REFERER')  # get last url

    # check cart variant
    delete_cart_id = []
    for item in models.Cart.objects.filter(user_id=request.user.id):
        if models.Product.objects.get(id=item.product.id).variant == 'None' and item.variant:
            delete_cart_id.append(item.id)
    if len(delete_cart_id) > 0:
        models.Cart.objects.filter(id__in=delete_cart_id).delete()
        return redirect(url)

    current_user = request.user
    product = models.Product.objects.get(pk=id)

    if product.status == 'Disabled':
        messages.warning(request, 'سفارش گيري اين محصول متوقف شده است')
        return HttpResponseRedirect(url)
    elif product.status == 'Draft':
        messages.warning(request, 'محصول در حالت پيش نويس است!')
    elif product.status == 'Create-On-Review' or product.status == 'Edit-On-Review' or product.wrong_variant_seller_quantity:
        messages.warning(request, 'محصول در حالت به روز رساني است!')
        return HttpResponseRedirect(url)
    elif product.status == 'Active' and not product.lack_in_gallery and not product.wrong_variant_seller_quantity:
        # check if item is in the cart
        variant_id = request.POST.get('variantid')
        if product.variant != 'None':
            models.Cart.objects.filter(variant_id=variant_id, user_id=current_user.id, out_of_stock=True).delete()
            if models.Cart.objects.filter(variant_id=variant_id, user_id=current_user.id).exists():
                control = 1  # The product is in the cart
            else:
                control = 0  # The product is not in the cart
                if models.Cart.objects.filter(product_id=id, user_id=current_user.id):
                    control = 2  # new variant
        else:
            models.Cart.objects.filter(product_id=id, user_id=current_user.id, out_of_stock=True).delete()
            if models.Cart.objects.filter(product_id=id, user_id=current_user.id).exists():
                control = 1  # The product is in the cart
            else:
                control = 0  # The product is not in the cart
        if request.method == 'POST':
            form = models.CartForm(request.POST)
            if form.is_valid():
                if control == 1:  # Update  Cart
                    # check limits
                    cart = get_object_or_404(models.Cart, product_id=id, user=request.user.id, out_of_stock=False)
                    cart_limit = models.CartLimit.objects.get(product_id=id, user_id=request.user.id)

                    if cart_limit.first_purchase_store_amount_limit != product.purchase_store_amount_limit:
                        diff = product.purchase_store_amount_limit - cart_limit.first_purchase_store_amount_limit
                        cart_limit.first_purchase_store_amount_limit = product.purchase_store_amount_limit
                        cart_limit.purchase_store_amount_limit += diff
                        cart_limit.save()

                    if cart_limit.first_purchase_amount_limit != product.purchase_amount_limit:
                        diff = product.purchase_amount_limit - cart_limit.first_purchase_amount_limit
                        cart_limit.first_purchase_amount_limit = product.purchase_amount_limit
                        cart_limit.purchase_amount_limit += diff
                        cart_limit.save()

                    purchase_amount_limit = cart_limit.purchase_amount_limit
                    purchase_store_amount_limit = cart_limit.purchase_store_amount_limit

                    if cart.variant:
                        variant = models.Variants.objects.get(id=cart.variant.id)
                        if variant.quantity == 0:
                            if (variant.seller_quantity - cart_limit.total_variant_seller_quantity) >= purchase_amount_limit:
                                max_increment = purchase_amount_limit
                            else:
                                max_increment = variant.seller_quantity - cart_limit.total_variant_seller_quantity
                        else:
                            if (variant.quantity - cart_limit.total_variant_quantity) >= purchase_store_amount_limit:
                                max_increment = purchase_store_amount_limit
                            else:
                                max_increment = variant.quantity - cart_limit.total_variant_quantity
                    else:
                        if product.store_amount == 0:
                            if (product.amount - cart_limit.total_product_amount) >= purchase_amount_limit:
                                max_increment = purchase_amount_limit
                            else:
                                max_increment = product.amount - cart_limit.total_product_amount
                        else:
                            if (product.store_amount - cart_limit.total_product_store_amount) >= purchase_store_amount_limit:
                                max_increment = purchase_store_amount_limit
                            else:
                                max_increment = product.store_amount - cart_limit.total_product_store_amount

                    if max_increment >= form.cleaned_data['quantity']:
                        # update cart
                        if product.variant != 'None':
                            data = models.Cart.objects.get(product_id=id, variant_id=variant_id, user_id=current_user.id)
                        else:
                            data = models.Cart.objects.get(product_id=id, user_id=current_user.id)
                        data.quantity += form.cleaned_data['quantity']
                        data.save()

                        # update Cart Limit
                        cart_limit = models.CartLimit.objects.get(product_id=id, user_id=current_user.id)
                        if cart_limit.store_amount_type:
                            cart_limit.purchase_store_amount_limit -= form.cleaned_data['quantity']
                        else:
                            cart_limit.purchase_amount_limit -= form.cleaned_data['quantity']
                        cart_limit.save()
                    elif max_increment < 0:
                        return redirect("shop:cart")
                    else:
                        return redirect(url)

                # Insert to Cart
                elif control == 0 or control == 2:
                    max_increment = 0
                    # check limits
                    if control == 2:
                        cart = get_object_or_404(models.Cart, product_id=id, user=request.user.id, out_of_stock=False)
                        cart_limit = models.CartLimit.objects.get(product_id=id, user_id=request.user.id)

                        if cart_limit.first_purchase_store_amount_limit != product.purchase_store_amount_limit:
                            diff = product.purchase_store_amount_limit - cart_limit.first_purchase_store_amount_limit
                            cart_limit.first_purchase_store_amount_limit = product.purchase_store_amount_limit
                            cart_limit.purchase_store_amount_limit += diff
                            cart_limit.save()

                        if cart_limit.first_purchase_amount_limit != product.purchase_amount_limit:
                            diff = product.purchase_amount_limit - cart_limit.first_purchase_amount_limit
                            cart_limit.first_purchase_amount_limit = product.purchase_amount_limit
                            cart_limit.purchase_amount_limit += diff
                            cart_limit.save()

                        purchase_store_amount_limit = cart_limit.purchase_store_amount_limit
                        purchase_amount_limit = cart_limit.purchase_amount_limit

                        if cart.variant:
                            variant = models.Variants.objects.get(id=cart.variant.id)
                            if variant.quantity == 0:
                                if (
                                        variant.seller_quantity - cart_limit.total_variant_seller_quantity) >= purchase_amount_limit:
                                    max_increment = purchase_amount_limit
                                else:
                                    max_increment = variant.seller_quantity - cart_limit.total_variant_seller_quantity
                            else:
                                if (
                                        variant.quantity - cart_limit.total_variant_quantity) >= purchase_store_amount_limit:
                                    max_increment = purchase_store_amount_limit
                                else:
                                    max_increment = variant.quantity - cart_limit.total_variant_quantity
                        else:
                            if product.store_amount == 0:
                                if (product.amount - cart_limit.total_product_amount) >= purchase_amount_limit:
                                    max_increment = purchase_amount_limit
                                else:
                                    max_increment = product.amount - cart_limit.total_product_amount
                            else:
                                if (
                                        product.store_amount - cart_limit.total_product_store_amount) >= purchase_store_amount_limit:
                                    max_increment = purchase_store_amount_limit
                                else:
                                    max_increment = product.store_amount - cart_limit.total_product_store_amount

                    elif control == 0:
                        if product.variant != 'None':
                            variant = models.Variants.objects.get(id=variant_id)
                            if variant.quantity == 0:
                                if variant.seller_quantity >= product.purchase_amount_limit:
                                    max_increment = product.purchase_amount_limit
                                else:
                                    max_increment = variant.seller_quantity
                            else:
                                if variant.quantity >= product.purchase_store_amount_limit:
                                    max_increment = product.purchase_store_amount_limit
                                else:
                                    max_increment = variant.quantity
                        else:
                            if product.store_amount == 0:
                                if product.amount >= product.purchase_amount_limit:
                                    max_increment = product.purchase_amount_limit
                                else:
                                    max_increment = product.amount
                            else:
                                if product.store_amount >= product.purchase_store_amount_limit:
                                    max_increment = product.purchase_store_amount_limit
                                else:
                                    max_increment = product.store_amount

                    if max_increment >= form.cleaned_data['quantity']:
                        # Create Cart
                        data = models.Cart()
                        data.user_id = current_user.id
                        data.product_id = id
                        data.variant_id = variant_id
                        data.quantity = form.cleaned_data['quantity']
                        if product.store_amount == 0 and product.amount > 0:
                            data.from_amount = True
                            data.from_store_amount = False
                        data.save()
                        # scheduler.delete_cart_job(data.id)

                        if control == 0:
                            # Create Cart Limit
                            cart_limit = models.CartLimit()
                            cart_limit.user_id = current_user.id
                            cart_limit.product_id = id
                            cart_limit.purchase_store_amount_limit = 0
                            cart_limit.first_purchase_store_amount_limit = product.purchase_store_amount_limit
                            cart_limit.first_purchase_amount_limit = product.purchase_amount_limit

                            if product.store_amount > 0:
                                cart_limit.purchase_store_amount_limit = product.purchase_store_amount_limit - form.cleaned_data['quantity']
                                cart_limit.purchase_amount_limit = 0
                            if product.amount > 0 and product.store_amount == 0:
                                cart_limit.purchase_amount_limit = product.purchase_amount_limit - form.cleaned_data['quantity']
                                cart_limit.store_amount = 0
                                cart_limit.store_amount_type = False
                            cart_limit.save()
                            cart_limit.cart.add(data)
                        elif control == 2:
                            # update Cart Limit
                            cart_limit = models.CartLimit.objects.get(product_id=id, user_id=current_user.id)
                            cart_limit.cart.add(data)
                            if cart_limit.store_amount_type:
                                cart_limit.purchase_store_amount_limit -= form.cleaned_data['quantity']
                            else:
                                cart_limit.purchase_amount_limit -= form.cleaned_data['quantity']
                            cart_limit.save()
                    elif max_increment < 0 and control == 2:
                        return redirect("shop:cart")
                    else:
                        return redirect(url)

                # # Decrease from Product
                # if product.store_amount > 0:
                #     product.store_amount -= form.cleaned_data['quantity']
                #     product.save()
                # elif product.store_amount == 0 and product.amount > 0:
                #     product.amount -= form.cleaned_data['quantity']
                #     product.save()

                # # Decrease from Product Variant
                # if product.variant != 'None':
                #     var_instant = models.Variants.objects.get(product=product, id=variant_id)
                #     if product.store_amount > 0:
                #         var_instant.quantity -= form.cleaned_data['quantity']
                #         var_instant.save()
                #     elif product.store_amount == 0 and product.amount > 0:
                #         var_instant.seller_quantity -= form.cleaned_data['quantity']
                #         var_instant.save()

            messages.success(request, "ایتم با موفقیت به سبد خرید شما اضافه شد")
            return HttpResponseRedirect(url)


@login_required
def delitem(request, id):
    cart = get_object_or_404(models.Cart, id=id, user=request.user)
    try:
        cart_limit_relation = models.CartLimit.objects.get(product=cart.product, user=request.user)
        cart_limit_relation.cart.remove(cart)
        if cart_limit_relation.cart.all().count() == 0:
            cart_limit_relation.delete()
    except:
        pass
    cart.delete()
    # product = models.Product.objects.get(id=cart.product.id)
    # if cart.from_store_amount:
    #     product.store_amount += cart.quantity
    #     product.save()
    # if cart.from_amount:
    #     product.amount += cart.quantity
    #     product.save()
    # if cart.variant:
    #     variant = models.Variants.objects.get(id=cart.variant.id)
    #     if cart.from_store_amount:
    #         variant.quantity += cart.quantity
    #         variant.save()
    #     if cart.from_amount:
    #         variant.seller_quantity += cart.quantity
    #         variant.save()

    # scheduler = get_object_or_404(models.SchedulerJobs, cart_id=id)
    # scheduler.status = 'Completed'
    # scheduler.save()
    return redirect('shop:cart')


@login_required
def cancel_order(request, id):
    url = request.META.get('HTTP_REFERER')  # get last url
    order = models.Order.objects.get(id=id)
    if order.status == 'Payment' or order.status == 'LackOfInventory' or order.status == 'Bank':
        if order.decreased_products_amount:
            order_items = models.OrderItem.objects.filter(user=request.user, order=order, out_of_stock=False)
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
            order.decreased_products_amount = False
        order.status = 'Canceled'
        order.save()
        userCouponUsage = models.UserCouponUsage.objects.filter(user=order.user, coupon=order.coupon)
        if userCouponUsage.exists():
            userCouponUsage = models.UserCouponUsage.objects.get(user=order.user, coupon=order.coupon)
            userCouponUsage.used = False
            userCouponUsage.save()
            coupon = models.Coupon.objects.get(code=order.coupon.code)
            coupon.usage_count -= 1
            coupon.save()
        # if models.SchedulerJobs.objects.filter(order_id=order.orderid).exists():
        #     job_obj = models.SchedulerJobs.objects.get(order_id=order.orderid)
        #     job_obj.status = 'Completed'
        #     job_obj.save()
    return redirect(url)


@login_required()
def checkout(request):
    current_user = request.user
    url = request.META.get('HTTP_REFERER')

    # check cart variant
    delete_cart_id = []
    for item in models.Cart.objects.filter(user_id=request.user.id):
        if models.Product.objects.get(id=item.product.id).variant == 'None' and item.variant:
            delete_cart_id.append(item.id)
    if len(delete_cart_id) > 0:
        models.Cart.objects.filter(id__in=delete_cart_id).delete()
        return redirect(url)

    cart = models.Cart.objects.filter(user_id=current_user.id, out_of_stock=False)

    # check inventory
    if cart.count() > 0:
        reorder = False
        for item in cart:
            product = models.Product.objects.get(id=item.product.id)
            cart_limit = models.CartLimit.objects.get(product_id=product.id, user_id=request.user.id)

            if cart_limit.first_purchase_store_amount_limit != product.purchase_store_amount_limit:
                diff = product.purchase_store_amount_limit - cart_limit.first_purchase_store_amount_limit
                cart_limit.first_purchase_store_amount_limit = product.purchase_store_amount_limit
                cart_limit.purchase_store_amount_limit += diff
                cart_limit.save()

            if cart_limit.first_purchase_amount_limit != product.purchase_amount_limit:
                diff = product.purchase_amount_limit - cart_limit.first_purchase_amount_limit
                cart_limit.first_purchase_amount_limit = product.purchase_amount_limit
                cart_limit.purchase_amount_limit += diff
                cart_limit.save()

            purchase_store_amount_limit = cart_limit.purchase_store_amount_limit
            purchase_amount_limit = cart_limit.purchase_amount_limit

            if item.variant:
                variant = models.Variants.objects.get(id=item.variant.id)
                if item.from_store_amount and (variant.quantity < item.quantity or purchase_store_amount_limit < 0):
                    reorder = True
                    break
                elif item.from_amount and (variant.seller_quantity < item.quantity or purchase_amount_limit < 0):
                    reorder = True
                    break
            else:
                if item.from_store_amount and (product.store_amount < item.quantity or purchase_store_amount_limit < 0):
                    reorder = True
                    break
                elif item.from_amount and (product.amount < item.quantity or purchase_amount_limit < 0):
                    reorder = True
                    break

        if reorder:
            return redirect('shop:cart')

        context = {}
        itemstotal = 0
        for p in cart:
            if p.product.variant == 'None':
                itemstotal += int(p.product.price) * p.quantity
            else:
                itemstotal += int(p.variant.price) * p.quantity
        totalcost = 0
        totalcost += itemstotal

        if request.method == 'POST':
            form = models.OrderForm(request.POST, instance=current_user)
            if form.is_valid():

                # Create Order
                data = models.Order()
                if request.POST.get("coupon"):
                    data.coupon = models.Coupon.objects.get(code__exact=request.POST.get("coupon"))
                data.first_name = current_user.first_name
                data.last_name = current_user.last_name
                data.phone = current_user.phone_number
                data.email = current_user.email
                data.user_id = current_user.id
                data.total = itemstotal
                data.ip = request.META.get('REMOTE_ADDR')
                data.address = form.cleaned_data['address']
                data.zipcode = form.cleaned_data['zipcode']
                data.note = form.cleaned_data['note']
                data.state = form.cleaned_data['state']
                data.city = form.cleaned_data['city']
                data.shipping_method = 'Express'
                data.status = 'Payment'
                data.totalcost = totalcost + 15000
                data.save()

                if request.POST.get("coupon"):
                    coupon = models.Coupon.objects.filter(code__exact=request.POST.get("coupon"))
                    if coupon.exists():
                        if coupon[0].active:
                            userCouponUsage = models.UserCouponUsage.objects.filter(user=current_user,
                                                                                    coupon__code__exact=request.POST.get(
                                                                                        "coupon"))
                            if userCouponUsage.exists():
                                userCouponUsage = models.UserCouponUsage.objects.get(user=current_user,
                                                                                     coupon__code__exact=request.POST.get(
                                                                                         "coupon"))
                                if userCouponUsage.used:
                                    pass
                                else:
                                    userCouponUsage.used = True
                                    userCouponUsage.order_id = data.id
                                    userCouponUsage.save()
                                    current_coupon = models.Coupon.objects.get(code__exact=request.POST.get("coupon"))
                                    current_coupon.usage_count += 1
                                    current_coupon.save()
                                    data.coupon = models.Coupon.objects.get(code__exact=request.POST.get("coupon"))
                                    if data.total <= models.Coupon.objects.get(code__exact=request.POST.get("coupon")).amount:
                                        data.totalcost -= data.total
                                    else:
                                        data.totalcost -= models.Coupon.objects.get(code__exact=request.POST.get("coupon")).amount
                                    data.save()
                            else:
                                newUserCouponUsage = models.UserCouponUsage()
                                newUserCouponUsage.user = current_user
                                newUserCouponUsage.used = True
                                newUserCouponUsage.coupon = models.Coupon.objects.get(
                                    code__exact=request.POST.get("coupon"))
                                newUserCouponUsage.order_id = data.id
                                newUserCouponUsage.save()
                                current_coupon = models.Coupon.objects.get(code__exact=request.POST.get("coupon"))
                                current_coupon.usage_count += 1
                                current_coupon.save()
                                data.coupon = models.Coupon.objects.get(code__exact=request.POST.get("coupon"))
                                if data.total <= models.Coupon.objects.get(code__exact=request.POST.get("coupon")).amount:
                                    data.totalcost -= data.total
                                else:
                                    data.totalcost -= models.Coupon.objects.get(code__exact=request.POST.get("coupon")).amount
                                data.save()

                order_delay = 0

                # create OrderItem
                for p in cart:
                    if p.from_amount:
                        order_delay += 1
                    item = models.OrderItem()
                    item.order_id = data.id
                    item.product_id = p.product_id
                    item.user_id = current_user.id
                    item.quantity = p.quantity
                    if p.product.variant == 'None':
                        item.price = p.product.price
                        item.amount = p.amount
                    else:
                        item.amount = p.varamount
                        item.price = p.variant.price
                    item.variant_id = p.variant_id
                    item.from_store_amount = p.from_store_amount
                    item.from_amount = p.from_amount
                    item.save()

                if order_delay > 0:
                    order_update = models.Order.objects.get(id=data.id)
                    order_update.delay = True
                    order_update.save()

                order_obj = models.Order.objects.filter(id=data.id)
                context.update({'order': order_obj})

                # Delete Cart & Cart Limits
                cart_list = models.Cart.objects.filter(user_id=current_user.id, out_of_stock=False)
                for cart in cart_list:
                    try:
                        models.CartLimit.objects.get(product=cart.product, user_id=request.user.id).delete()
                    except:
                        pass
                cart_list.delete()
                # scheduler.delete_order_job(models.Order.objects.get(id=data.id).orderid)
                return redirect('shop:order', data.id)
            else:
                messages.warning(request, form.errors)
                return redirect(url)

        context.update({'cart': cart,
                        'total': itemstotal,
                        'totalcost': totalcost,
                        'form': models.OrderForm(instance=request.user),
                        'profile': request.user})
        return render(request, 'shop/checkout.html', context)
    else:
        return redirect('shop:home')


@login_required
def validate_coupon(request):
    coupon = request.GET.get('coupon', None)
    coupon_amount = models.Coupon.objects.get(code__exact=coupon).amount
    data = {
        'coupon_exists_check': models.Coupon.objects.filter(code__exact=coupon).exists()
    }
    cart = models.Cart.objects.filter(user_id=request.user.id, out_of_stock=False)
    itemstotal = 0
    for p in cart:
        if p.product.variant == 'None':
            itemstotal += int(p.product.price) * p.quantity
        else:
            itemstotal += int(p.variant.price) * p.quantity

    if data['coupon_exists_check']:
        if models.Coupon.objects.get(code__exact=coupon).active:
            data['coupon_valid'] = True
            userCouponUsage = models.UserCouponUsage.objects.filter(user=request.user, coupon__code__exact=coupon)
            if userCouponUsage.exists():
                if userCouponUsage[0].used:
                    data['coupon_used_already'] = True
                    data['coupon_used_already_msg'] = 'شما يكبار از اين كوپن استفاده كرده ايد'
                else:
                    data['coupon_used'] = True
                    data['coupon_used_msg'] = 'كوپن با موفقیت اعمال شد'
                    data['coupon_amount'] = coupon_amount
                    data['total_after_coupon'] = itemstotal - coupon_amount
                    if coupon_amount >= itemstotal:
                        data['total_after_coupon'] = 0
                        data['coupon_amount'] = itemstotal
            else:
                data['coupon_used'] = True
                data['coupon_used_msg'] = 'كوپن با موفقیت اعمال شد'
                newUserCouponUsage = models.UserCouponUsage()
                newUserCouponUsage.user = request.user
                newUserCouponUsage.coupon = models.Coupon.objects.get(code__exact=coupon)
                newUserCouponUsage.save()
                data['coupon_amount'] = coupon_amount
                data['total_after_coupon'] = itemstotal - coupon_amount
                if coupon_amount >= itemstotal:
                    data['total_after_coupon'] = 0
                    data['coupon_amount'] = itemstotal
        else:
            data['coupon_expired'] = True
            data['coupon_expired_msg'] = 'مهلت استفاده از كوپن به اتمام رسيده است'
    else:
        data['coupon_does_not_exists_msg'] = 'كوپن معتبر نميباشد'
    return JsonResponse(data)


@login_required()
def order(request, id):
    order = get_object_or_404(models.Order, id=id, user=request.user.id)
    order_items = models.OrderItem.objects.filter(order=order, user_id=request.user.id)
    context = {'order': order, 'order_items_count': order_items.count(), 'order_items': order_items}
    if order.status == 'Bank':
        # Increase Product & Variant
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
    # check inventory
    if order.status == 'Payment' or order.status == 'LackOfInventory':
        reorder_products_info_list = []  # order_item ID, lack, requested
        for item in order_items:
            reorder_products_info = []
            product = models.Product.objects.get(id=item.product.id)
            if item.variant:
                variant = models.Variants.objects.get(id=item.variant.id)
                if item.from_store_amount and variant.quantity < item.quantity:
                    reorder_products_info.append(item.id)
                    reorder_products_info.append(item.quantity - variant.quantity)
                    reorder_products_info.append(item.quantity)
                elif item.from_amount and variant.seller_quantity < item.quantity:
                    reorder_products_info.append(item.id)
                    reorder_products_info.append(item.quantity - variant.seller_quantity)
                    reorder_products_info.append(item.quantity)
            else:
                if item.from_store_amount and product.store_amount < item.quantity :
                    reorder_products_info.append(item.id)
                    reorder_products_info.append(item.quantity - product.store_amount)
                    reorder_products_info.append(item.quantity)
                elif item.from_amount and product.amount < item.quantity:
                    reorder_products_info.append(item.id)
                    reorder_products_info.append(item.quantity - product.amount)
                    reorder_products_info.append(item.quantity)

            if len(reorder_products_info) > 0:
                reorder_products_info_list.append(reorder_products_info)

        if len(reorder_products_info_list) > 0:
            order.status = 'Payment'
            order.save()

            # decrease OrderItems quantity
            order_item_id_list = []
            for order_item in reorder_products_info_list:
                order_item_id_list.append(order_item[0])
                order_item_ins = models.OrderItem.objects.get(id=order_item[0])
                order_item_ins.quantity = order_item[2] - order_item[1]
                order_item_ins.amount -= order_item[1] * int(order_item_ins.price)
                if order_item_ins.quantity <= 0:
                    order_item_ins.quantity = 0
                    order_item_ins.out_of_stock = True
                order_item_ins.save()

                order.total -= int(order_item_ins.price) * order_item[1]
                order.totalcost -= int(order_item_ins.price) * order_item[1]
                order.save()

            order = get_object_or_404(models.Order, id=id, user=request.user.id)
            order_items = models.OrderItem.objects.filter(order=order, user_id=request.user.id)

            order.delay = False
            for order_item in order_items:
                if order_item.from_amount and order_item.quantity != 0:
                    order.delay = True
            order.save()

            if order.total == 0:
                order.status = 'Canceled'
                order.save()
                context.update({'order_canceled': '1'})

                user_coupon_usage = models.UserCouponUsage.objects.filter(user=order.user, coupon=order.coupon)
                if user_coupon_usage.exists():
                    user_coupon_usage = models.UserCouponUsage.objects.get(user=order.user, coupon=order.coupon)
                    user_coupon_usage.used = False
                    user_coupon_usage.save()
                    coupon = models.Coupon.objects.get(code=order.coupon.code)
                    coupon.usage_count -= 1
                    coupon.save()

            reorder_products_query = models.OrderItem.objects.filter(id__in=order_item_id_list, user_id=request.user.id, order=order)
            context.update({
                'reorder_products_info_list': reorder_products_info_list,
                'reorder_products_query': reorder_products_query,
                'order_items': models.OrderItem.objects.filter(order=order, user_id=request.user.id)
            })
    return render(request, 'shop/order.html', context)


@login_required
def del_order_item(request, id):
    url = request.META.get('HTTP_REFERER')
    order_item = get_object_or_404(models.OrderItem, id=id, user=request.user)
    order = models.Order.objects.get(id=order_item.order.id)
    if order_item.order.status == 'LackOfInventory':
        order.totalcost -= order_item.amount
        order.total -= order_item.amount
        order.save()
        return redirect('shop:order', id=order.id)
    return redirect(url)


@login_required()
def pay(request, id):
    order = get_object_or_404(models.Order, id=id, user=request.user)
    order_items = models.OrderItem.objects.filter(user=request.user, order_id=id, out_of_stock=False)
    if order.status == 'Bank':
        # Increase Product & Variant
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
    if order.status == 'Payment' or order.status == 'LackOfInventory':
        description = f'{"شماره سفارش : "} {order.orderid}'
        mobile = str(request.user.phone_number)
        email = str(request.user.email)
        amount = int(order.totalcost)
        result = client.service.PaymentRequest(MERCHANT, amount, description, email, mobile, CallbackURL)
        if result.Status == 100 and len(result.Authority) == 36:
            # check inventory
            reorder_products = False
            for item in order_items:
                product = models.Product.objects.get(id=item.product.id)
                if item.variant:
                    variant = models.Variants.objects.get(id=item.variant.id)
                    if item.from_store_amount and variant.quantity < item.quantity:
                        reorder_products = True
                        break
                    elif item.from_amount and variant.seller_quantity < item.quantity:
                        reorder_products = True
                        break
                else:
                    if item.from_store_amount and product.store_amount < item.quantity:
                        reorder_products = True
                        break
                    elif item.from_amount and product.amount < item.quantity:
                        reorder_products = True
                        break
            if not reorder_products:
                # update_or_create invoice
                order_items_arr = []
                for item in order_items:
                    order_items_arr.append(item)
                models.Invoice.objects.update_or_create(
                    order=order, authority=result.Authority,
                    defaults={'order': order, 'order_items': order_items_arr, 'authority': result.Authority},
                )
                if not order.decreased_products_amount:
                    # Decrease from Product & Variant
                    for item in order_items:
                        product = models.Product.objects.get(id=item.product.id)
                        if item.from_store_amount:
                            product.store_amount -= item.quantity
                            product.save()
                        if item.from_amount:
                            product.amount -= item.quantity
                            product.save()
                        if item.variant:
                            variant = models.Variants.objects.get(id=item.variant.id)
                            if item.from_store_amount:
                                variant.quantity -= item.quantity
                                variant.save()
                            if item.from_amount:
                                variant.seller_quantity -= item.quantity
                                variant.save()

                order.status = 'Bank'
                order.decreased_products_amount = True
                order.save()

                return redirect('https://www.zarinpal.com/pg/StartPay/' + str(result.Authority))
            elif reorder_products:
                if order.decreased_products_amount:
                    order_items = models.OrderItem.objects.filter(user=request.user, order=order, out_of_stock=False)
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
                    order.decreased_products_amount = False
                order.status = 'LackOfInventory'
                order.save()
                return redirect('shop:order', id)
        else:
            return HttpResponse('Error' + str(result.Status))
    else:
        return HttpResponse('عملیات غیر مجاز')


@login_required()
def callback(request):
    # viewed recently
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
                vr_queryset |= models.ObjectViewed.objects.filter(id=int(id[:id.index("-")]), user_id=request.user.id)
                vr_queryset = vr_queryset[:15]
        except:
            vr_queryset = None
    else:
        vr_queryset = None
    if request.GET.get('Status') == 'OK':
        authority = request.GET.get('Authority')
        invoice = get_object_or_404(models.Invoice, authority=authority)
        order = get_object_or_404(models.Order, id=invoice.order.id, user=request.user)
        amount = int(order.totalcost)
        order_items = models.OrderItem.objects.filter(order=order)
        for item in order_items:
            if item.out_of_stock:
                item.delete()
        order_items = models.OrderItem.objects.filter(order=order)

        result = client.service.PaymentVerification(MERCHANT, authority, amount)
        if result.Status == 100 and order.status == 'Bank':  # If Payment Was Successful
            order.status = 'Preparing'
            order.save()

            sellers = []
            for item in order_items:
                if item.product.user_id not in sellers:
                    sellers.append(item.product.user_id)

            # create SellerOrder & SellerOrderItem
            for seller_id in sellers:
                seller_order = models.SellerOrder()
                seller_order.seller_id = seller_id
                seller_order.order_id = order.id
                seller_order.save()

                # create SellerOrderItem
                for p in order_items:
                    if p.product.user_id == seller_order.seller_id:
                        seller_order_item = models.SellerOrderItem()
                        seller_order_item.seller_id = seller_order.seller_id
                        seller_order_item.seller_order_id = seller_order.id
                        seller_order_item.product_id = p.product_id
                        seller_order_item.quantity = p.quantity
                        if p.product.variant == 'None':
                            seller_order_item.price = p.product.price
                        else:
                            seller_order_item.price = p.variant.price
                        seller_order_item.variant_id = p.variant_id
                        seller_order_item.from_store_amount = p.from_store_amount
                        seller_order_item.from_amount = p.from_amount

                        if p.product.variant == 'None':
                            seller_order.order_total += int(p.product.price) * p.quantity
                            seller_order.order_pursuant += int(p.product.price * p.quantity * (p.product.pursuant / 100))
                            seller_order.order_profit = seller_order.order_total - seller_order.order_pursuant
                            seller_order.save()

                            seller_order_item.item_total = int(p.product.price) * p.quantity
                            seller_order_item.item_pursuant = int(p.product.price * p.quantity * (p.product.pursuant / 100))
                            seller_order_item.item_profit = seller_order_item.item_total - seller_order_item.item_pursuant
                            seller_order_item.save()
                        else:
                            seller_order.order_total += int(p.variant.price) * p.quantity
                            seller_order.order_pursuant += int(p.variant.price * p.quantity * (p.product.pursuant / 100))
                            seller_order.order_profit = seller_order.order_total - seller_order.order_pursuant
                            seller_order.save()

                            seller_order_item.item_total = int(p.variant.price) * p.quantity
                            seller_order_item.item_pursuant = int(p.variant.price * p.quantity * (p.product.pursuant / 100))
                            seller_order_item.item_profit = seller_order.order_total - seller_order.order_pursuant
                            seller_order_item.save()

                # notify seller if he/she required to send products to inventory
                if models.SellerOrderItem.objects.filter(from_amount=True, seller_order_id=seller_order.id).exists():
                    seller_order.send = True
                    seller_order.save()

            # customer sms
            sms = models.Sms()
            sms.user_id = order.user_id
            sms.order_id = order.id
            sms.category = "Customer"
            new_line = '\n'

            try:
                api = KavenegarAPI(sms_api_key)
                track_url = "https://artynarium.com" + reverse("shop:my_order_detail", args=[str(order.id)])
                params = {
                    'sender': sms_sender,
                    'receptor': str(order.user.phone_number),
                    'message': f'{str(order.first_name)}{"عزيز سفارش شما به شماره "}{order.orderid}{" با موفقيت ثبت شد"}{new_line}{"پیگیری سفارش: "}{track_url}'
                }
                response = api.sms_send(params)
                response = response[0]
                sms.message_id = response['messageid']
                sms.message_content = response['message']
                sms.message_status = response['status']
                sms.message_sender = response['sender']
                sms.message_receptor = response['receptor']
                sms.message_data = response['date']
                sms.message_cost = response['cost']
                sms.save()
            except APIException as e:
                sms.message_api_exception = str(e)
                sms.message_status = False
                sms.save()
            except HTTPException as e:
                sms.message_http_exception = str(e)
                sms.message_status = False
                sms.save()
            # customer sms end

            # seller(s) sms
            seller_orders = models.SellerOrder.objects.filter(order_id=order.id)
            for so in seller_orders:
                from_amount = 0
                seller_order_items = models.SellerOrderItem.objects.filter(seller_order_id=so.id)
                for i in seller_order_items:
                    if i.from_amount:
                        from_amount += 1

                sms = models.Sms()
                sms.user_id = so.seller_id
                sms.seller_order_id = so.id
                sms.category = "Seller"

                track_url = "https://artynarium.com" + reverse("seller:order_detail", args=[str(so.order.orderid)])
                if from_amount > 0:
                    message = f'{"فروشنده عزیز سفارش جدیدی به شماره سفارش "}{so.order.orderid}{"دریافت کردید. لطفا محصولاتی را که سفارش آنها از نزد فروشنده میباشد را در بازه زمانی تعهد ارسال خود به انبار فروشگاه ارسال کنید."}{new_line}{"مشاهده سفارش: "}{track_url}'
                else:
                    message = f'{"فروشنده عزیز سفارش جدیدی به شماره سفارش "}{so.order.orderid}{" دریافت کردید"}{new_line}{"مشاهده سفارش: "}{track_url}'

                try:
                    api = KavenegarAPI(sms_api_key)
                    params = {
                        'sender': sms_sender,
                        'receptor': str(so.seller.phone_number),
                        'message': message
                    }
                    response = api.sms_send(params)
                    response = response[0]
                    sms.message_id = response['messageid']
                    sms.message_content = response['message']
                    sms.message_status = response['status']
                    sms.message_sender = response['sender']
                    sms.message_receptor = response['receptor']
                    sms.message_data = response['date']
                    sms.message_cost = response['cost']
                    sms.save()
                except APIException as e:
                    sms.message_api_exception = str(e)
                    sms.message_status = False
                    sms.save()
                except HTTPException as e:
                    sms.message_http_exception = str(e)
                    sms.message_status = False
                    sms.save()
            # seller(s) sms end

            # Increase Sold Count
            for p in order_items:
                product = models.Product.objects.get(id=p.product.id)
                product.sold += p.quantity
                product.save()

            # increase seller balance after applying pursuant
            for i in order_items:
                item_cost = 0
                if i.product.variant == 'None':
                    item_cost += int(i.product.price) * i.quantity
                else:
                    item_cost += int(i.variant.price) * i.quantity

                item_pursuant = 0
                if i.product.variant == 'None':
                    item_pursuant += int(i.product.price * i.quantity * (i.product.pursuant / 100))
                else:
                    item_pursuant += int(i.variant.price * i.quantity * (i.product.pursuant / 100))

                user_data = User.objects.get(id=i.product.user.id)
                user_data.balance += item_cost - item_pursuant
                user_data.save()

                seller_balance = SellerBalance()
                seller_balance.user_id = i.product.user.id
                seller_balance.amount = item_cost - item_pursuant
                seller_balance.order_id = i.order.id
                seller_balance.order_item_id = i.id
                seller_balance.save()

                product_data = models.Product.objects.get(id=i.product.id)
                product_data.profit += item_cost - item_pursuant  # profit of an item
                product_data.save()

            return render(request, 'shop/callback.html', {'invoice': invoice, 'vr': vr_queryset, 'order': order})
        else:
            return HttpResponse('Error' + str(result.Status))
    elif request.GET.get('Status') == 'NOK':
        authority = request.GET.get('Authority')
        invoice = get_object_or_404(models.Invoice, authority=authority)
        order = models.Order.objects.get(id=invoice.order.id)
        order_items = models.OrderItem.objects.filter(user=request.user, order=order, out_of_stock=False)

        # Increase Product & Variant
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
        order.decreased_products_amount = False
        return render(request, 'shop/callback_error_canceled.html', {'order': order, 'vr': vr_queryset})
    else:
        authority = request.GET.get('Authority')
        invoice = get_object_or_404(models.Invoice, authority=authority)
        order = models.Order.objects.get(id=invoice.order.id)
        order_items = models.OrderItem.objects.filter(user=request.user, order=order, out_of_stock=False)

        # Increase Product & Variant
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
        order.decreased_products_amount = False
        return render(request, 'shop/callback_error.html', {'order': order, 'vr': vr_queryset})


@login_required()
def last_payments(request):
    context = {}
    if request.user.seller:
        history = seller_model.Withdraw.objects.filter(payed=True).order_by('create_time')[:50]
        paginator = Paginator(history, 12)
        page = request.GET.get('page')
        history = paginator.get_page(page)
        context.update({'history': history})
    else:
        context.update({'not_allowed': 'شما قابليت فروشندگي نداريد!'})
    return render(request, 'shop/last_payments.html', context)


def error404(request, exception):
    return render(request, 'shop/error/404.html', status=404)
