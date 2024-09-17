from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from shop import models
from users.forms import SellerRequest, SellerEdit
from users.models import User as seller_account
from . import models as seller_model
from django.db.models import Q, Sum


def is_valid_queryparam(param):
    return param != '' and param is not None


@login_required()
def validate_product_name(request):
    data = {}
    title = request.GET.get('title', None)
    product = models.Product.objects.filter(name__exact=title)
    if product.exists():
        data.update({'product_exists_check': True})
        if product.user.id == request.user.id:
            data.update({'vendor_owns_product': True})
    return JsonResponse(data)


@login_required()
def product_create(request):
    url = request.META.get('HTTP_REFERER')
    categories = models.Category.objects.filter(parent__isnull=True)
    brand = models.Brand.objects.all()
    context = {
        'categories': categories,
        'brand': brand
    }
    if request.user.seller:
        context.update({'form': models.ProductForm()})
        if request.method == 'POST':
            form = models.ProductForm(request.POST, request.FILES)
            if form.is_valid():
                data = models.Product()
                data.user_id = request.user.id
                data.product_type = form.cleaned_data['product_type']
                product_validation = models.Product.objects.filter(name__exact=form.cleaned_data['name'], user=request.user)
                if product_validation.exists() and product_validation[0].user.id == request.user.id:
                    msg = 'شما در حال حاظر محصولي به اين نام داريد. لطفا عنواني كه وارد كرديد را چك كنيد.'
                    messages.warning(request, msg)
                    return redirect(url)
                data.name = form.cleaned_data['name']
                data.slug = request.POST.get('slug')
                data.brand_id = request.POST.get('brand')
                data.image = form.cleaned_data['image']
                data.banner_image = form.cleaned_data['banner_image']
                data.hover_image = form.cleaned_data['banner_image']
                data.description = form.cleaned_data['description']
                data.price = form.cleaned_data['price']
                data.amount = form.cleaned_data['amount']
                if product_validation.exists() and product_validation[0].user.id != request.user.id:
                    data.multi_seller = True
                data.save()
                for i in range(len(request.POST.getlist('category'))):
                    data.category.add(get_object_or_404(models.Category, id=request.POST.getlist('category')[i]))
                product_categories = models.Category.objects.filter(catproduct__id=data.id)
                for cat in product_categories:
                    if not cat.get_descendants(include_self=False):
                        ancestors = cat.get_ancestors(include_self=True)
                        for ancestor in ancestors:
                            if ancestor not in data.category.all():
                                data.category.add(ancestor)
                return redirect('seller:product_gallery_create_update', data.id, 0)
            else:
                messages.warning(request, form.errors)
                return redirect(url)
    else:
        context.update({'not_allowed': 'شما قابليت فروشندگي نداريد!'})
    return render(request, 'seller/product_create.html', context)


@login_required()
def product_update(request, id):
    if 'amount_msg_read_redirected' in request.session and request.session['amount_msg_read_redirected'] == 1:
        del request.session['amount_msg_read']
    url = request.META.get('HTTP_REFERER')
    product_obj = get_object_or_404(models.Product, id=id, user=request.user)
    categories = models.Category.objects.filter(parent__isnull=True)
    brand = models.Brand.objects.all()
    context = {
        'id': id,
        'categories': categories,
        'brand': brand,
        'product': product_obj,
        'form': models.ProductForm(product_obj)
    }
    if request.user.seller:
        if request.method == 'POST':
            form = models.ProductForm(request.POST, request.FILES, instance=product_obj)
            if form.is_valid():
                data = get_object_or_404(models.Product, id=id, user=request.user)
                data.user_id = request.user.id
                data_status = 0
                data.product_type = form.cleaned_data['product_type']
                if not form.cleaned_data['product_type'] == product_obj.product_type:
                    data_status += 1

                data.name = form.cleaned_data['name']
                if not form.cleaned_data['name'] == product_obj.name:
                    data_status += 1

                data.slug = request.POST.get('slug')
                if not form.cleaned_data['slug'] == product_obj.slug:
                    data_status += 1

                for i in range(len(request.POST.getlist('category'))):
                    if get_object_or_404(models.Category, id=request.POST.getlist('category')[i]) not in product_obj.category.all():
                        data_status += 1
                # if len(request.POST.getlist('category')) < product_obj.category.all().count():
                #     data_status += 1

                if request.POST.get('brand'):
                    data.brand_id = request.POST.get('brand')
                    if not int(request.POST.get('brand')) == product_obj.brand.id:
                        data_status += 1

                if form.cleaned_data['image']:
                    data.image = form.cleaned_data['image']
                    if not form.cleaned_data['image'] == product_obj.image:
                        data_status += 1
                else:
                    data.image = get_object_or_404(models.Product, id=id, user=request.user).image

                if form.cleaned_data['banner_image']:
                    data.banner_image = form.cleaned_data['banner_image']
                    if not form.cleaned_data['banner_image'] == product_obj.banner_image:
                        data_status += 1
                else:
                    data.banner_image = get_object_or_404(models.Product, id=id, user=request.user).banner_image

                if form.cleaned_data['hover_image']:
                    data.hover_image = form.cleaned_data['hover_image']
                    if not form.cleaned_data['hover_image'] == product_obj.hover_image:
                        data_status += 1
                else:
                    data.hover_image = get_object_or_404(models.Product, id=id, user=request.user).hover_image

                data.description = form.cleaned_data['description']
                if not form.cleaned_data['description'] == product_obj.description:
                    data_status += 1

                data.price = form.cleaned_data['price']
                if not form.cleaned_data['price'] == product_obj.price:
                    data_status += 1

                if data_status > 0:
                    data.status = 'Edit-On-Review'

                data.amount = form.cleaned_data['amount']
                if models.Variants.objects.filter(product__id=id).exists():
                    if not form.cleaned_data['amount'] == product_obj.amount:
                        if 'amount_msg_read_redirected' in request.session and request.session['amount_msg_read_redirected'] == 1:
                            del request.session['amount_msg_read_redirected']
                        else:
                            request.session['amount_msg_read'] = 0

                product_validation = models.Product.objects.filter(name__exact=form.cleaned_data['name'])
                if product_validation.exists() and product_validation[0].user.id != request.user.id:
                    data.multi_seller = True
                data.save()

                data.category.clear()
                for i in range(len(request.POST.getlist('category'))):
                    data.category.add(get_object_or_404(models.Category, id=request.POST.getlist('category')[i]))
                product_categories = models.Category.objects.filter(catproduct__id=id)
                for cat in product_categories:
                    if not cat.get_descendants(include_self=False):
                        ancestors = cat.get_ancestors(include_self=True)
                        for ancestor in ancestors:
                            if ancestor not in data.category.all():
                                data.category.add(ancestor)

                if 'amount_msg_read' in request.session and request.session['amount_msg_read'] == 0:
                    request.session['amount_msg_read_redirected'] = 1
                    data.wrong_variant_seller_quantity = True
                    data.save()
                    messages.add_message(request, messages.WARNING, "از آنجايي كه موجودي نزد فروشنده را ويرايش كرديد بايد موجودي گوناگوني ها را نيز تنظيم كنيد")
                    return redirect(url)
                else:
                    if "save_and_continue" in request.POST:
                        messages.add_message(request, messages.SUCCESS, f"{'محصول '}{product_obj}{' با موفقيت ويرايش شد.'}")
                        return redirect(url)
                    elif "save_next" in request.POST:
                        if models.Images.objects.filter(product__id=id).exists():
                            return redirect('seller:product_gallery_create_update', id, 1)
                        return redirect('seller:product_gallery_create_update', id, 0)
            else:
                messages.warning(request, form.errors)
                return redirect(url)
    else:
        context.update({'not_allowed': 'شما قابليت فروشندگي نداريد!'})
    return render(request, 'seller/product_update.html', context)


@login_required()
def product_gallery_create_update(request, id, edit=0):
    url = request.META.get('HTTP_REFERER')
    product = get_object_or_404(models.Product, id=id, user=request.user)
    context = {'product': product, 'edit': edit, 'id': id}
    if edit == 0 and models.Images.objects.filter(product__id=id).exists():
        context.update({'edit': 1})
    if edit == 1 and not models.Images.objects.filter(product__id=id).exists():
        context.update({'edit': 0})
    if request.user.seller:
        if request.method == 'POST':
            if edit == 0:
                form = models.ImagesForm(request.POST, request.FILES)
                if form.is_valid():
                    if len(request.POST.getlist('title')) >= 4:
                        for i in range(len(request.POST.getlist('title'))):
                            data = models.Images()
                            data.product_id = id
                            data.title = request.POST.getlist('title')[i]
                            if request.FILES.getlist('image')[i]:
                                data.image = request.FILES.getlist('image')[i]
                            else:
                                data.image = models.Images.objects.filter(product__id=id)[i]
                            data.save()
                    else:
                        messages.add_message(request, messages.WARNING, "حداقل 4 عدد گالري اضافه كنيد")
                        return redirect(url)
                    if "finish_process" in request.POST:
                        if edit == 1:
                            messages.add_message(request, messages.INFO, f"{'محصول'} {product} {'با موفقيت ويرايش شد و درحال بررسي است'}")
                        elif edit == 0:
                            messages.add_message(request, messages.INFO, f"{'محصول'} {product} {'با موفقيت ساخته شد و درحالت پيش نويس قرار دارد. در اين حالت فقط شما قادر به ديدن و ويرايش آن هستيد. براي ثبت نهايي بر روي ثبت كليك كنيد'}")
                        return redirect('seller:my_products')
                    elif "add_variant" in request.POST:
                        if edit == 1:
                            return redirect('seller:product_variant_create_update', id, 1)
                        return redirect('seller:product_variant_create_update', id, 0)
                else:
                    messages.warning(request, form.errors)
                    return redirect(url)
            if edit == 1:
                form = models.ImagesForm(request.POST, request.FILES)
                if form.is_valid():
                    length = 0
                    if request.POST.getlist('title'):
                        if models.Images.objects.filter(product__id=id).exists():
                            length += len(models.Images.objects.filter(product__id=id))
                        length += len(request.POST.getlist('title'))
                    else:
                        if models.Images.objects.filter(product__id=id).exists():
                            length = len(models.Images.objects.filter(product__id=id))
                    if length >= 4:
                        for i in range(len(request.POST.getlist('current_title'))):
                            changed_img = []
                            current_id = request.POST.getlist('current_id')[i]
                            data = get_object_or_404(models.Images, product__id=id, id=current_id, product__user=request.user)
                            data.title = request.POST.getlist('current_title')[i]
                            if 'current_image'+'_'+current_id in request.FILES:
                                changed_img.append(current_id)
                                data.image = request.FILES.get('current_image'+'_'+current_id)
                            else:
                                data.image = get_object_or_404(models.Images, product__id=id, id=current_id, product__user=request.user).image
                            data.save()

                            for i in changed_img:
                                img_obj = get_object_or_404(models.Images, id=i, product__user=request.user)
                                variant_obj = get_object_or_404(models.Variants, image_id=i, product__user=request.user)
                                variant_obj.image_id = img_obj.id
                                variant_obj.save()

                        if request.POST.getlist('title') and request.FILES.getlist('image'):
                            for i in range(len(request.POST.getlist('title'))):
                                data = models.Images()
                                data.product_id = id
                                data.title = request.POST.getlist('title')[i]
                                data.image = request.FILES.getlist('image')[i]
                                data.save()

                        product_update_obj = get_object_or_404(models.Product, id=id, user=request.user)
                        product_update_obj.status = 'Edit-On-Review'
                        product_update_obj.save()

                        if "finish_process" in request.POST:
                            if edit == 1:
                                messages.add_message(request, messages.INFO,
                                                     f"{'محصول'} {product} {'با موفقيت ويرايش شد و درحال بررسي است'}")
                            elif edit == 0:
                                messages.add_message(request, messages.INFO,
                                                     f"{'محصول'} {product} {'با موفقيت ساخته شد و درحالت پيش نويس قرار دارد. در اين حالت فقط شما قادر به ديدن و ويرايش آن هستيد. براي ثبت نهايي بر روي ثبت كليك كنيد'}")
                            return redirect('seller:my_products')
                        elif "add_variant" in request.POST:
                            if edit == 1:
                                return redirect('seller:product_variant_create_update', id, 1)
                            return redirect('seller:product_variant_create_update', id, 0)
                    else:
                        messages.add_message(request, messages.WARNING, "حداقل 4 عدد گالري اضافه كنيد")
                        return redirect(url)
                else:
                    messages.warning(request, form.errors)
                    return redirect(url)
    else:
        context.update({'not_allowed': 'شما قابليت فروشندگي نداريد!'})
    return render(request, 'seller/product_gallery_create_update.html', context)


@login_required()
def product_variant_create_update(request, id, edit=0):
    url = request.META.get('HTTP_REFERER')
    product = get_object_or_404(models.Product, id=id, user=request.user)
    colors = models.Color.objects.all()
    sizes = models.Size.objects.all()
    context = {
        'product': product,
        'sizes': sizes,
        'colors': colors,
        'edit': edit,
        'id': id
    }
    if product.wrong_variant_seller_quantity:
        context.update({'wrong_variant_seller_quantity': 'از آنجايي كه موجودي نزد فروشنده را ويرايش كرديد بايد موجودي گوناگوني ها را نيز تنظيم كنيد'})
    if request.user.seller:
        if request.method == 'POST':
            if request.POST['variant_type'] != 'None':
                if edit == 0:
                    form = models.VariantsForm(request.POST)
                    if form.is_valid():
                        amount = 0
                        for i in range(len(request.POST.getlist('title'))):
                            if len(request.POST.getlist('title')) > 1:
                                amount += int(request.POST.getlist('seller_quantity')[i])
                            else:
                                amount += int(request.POST['seller_quantity'])
                        if amount != get_object_or_404(models.Product, id=id, user=request.user).amount:
                            messages.add_message(request, messages.WARNING, f'{"جمع موجودي نزد فروشنده گوناگوني ها بايد با تعداد موجودی نزد فروشنده اوليه محصول برابر باشد. موجودي اوليه: "}{get_object_or_404(models.Product, id=id, user=request.user).amount}')
                            return redirect(url)

                        for i in range(len(request.POST.getlist('title'))):
                            data = models.Variants()
                            data.product_id = id
                            if len(request.POST.getlist('title')) > 1:
                                if not models.Images.objects.filter(id=request.POST.getlist('image_id')[i]).exists():
                                    messages.add_message(request, messages.WARNING, f"{'گالري اي با آيدي '}{request.POST.getlist('image_id')[i]}{' وجود ندارد.'}")
                                    return redirect(url)
                                data.title = request.POST.getlist('title')[i]
                                if request.POST['variant_type'] == 'Size-Color' or request.POST['variant_type'] == 'Color':
                                    data.color_id = request.POST.getlist('color')[i]
                                if request.POST['variant_type'] == 'Size-Color' or request.POST['variant_type'] == 'Size':
                                    data.size_id = request.POST.getlist('size')[i]
                                data.image_id = request.POST.getlist('image_id')[i]
                                data.seller_quantity = request.POST.getlist('seller_quantity')[i]
                                data.price = request.POST.getlist('price')[i]
                            else:
                                if not models.Images.objects.filter(id=request.POST.get('image_id')).exists():
                                    messages.add_message(request, messages.WARNING, f"{'گالري اي با آيدي '}{request.POST.get('image_id')}{' وجود ندارد.'}")
                                    return redirect(url)
                                data.title = request.POST.get('title')
                                if request.POST['variant_type'] == 'Size-Color' or request.POST['variant_type'] == 'Color':
                                    data.color_id = request.POST.get('color')
                                if request.POST['variant_type'] == 'Size-Color' or request.POST['variant_type'] == 'Size':
                                    data.size_id = request.POST.get('size')
                                data.image_id = request.POST.get('image_id')
                                data.seller_quantity = request.POST.get('seller_quantity')
                                data.price = request.POST.get('price')
                            data.save()

                        messages.add_message(request, messages.INFO, f"{'محصول'} {product} {'با موفقيت ساخته شد و درحالت پيش نويس قرار دارد. در اين حالت فقط شما قادر به ديدن و ويرايش آن هستيد. براي ثبت نهايي بر روي ثبت كليك كنيد'}")
                        product.status = 'Draft'
                        product.variant = request.POST['variant_type']
                        product.save()
                        return redirect('seller:my_products')
                    else:
                        messages.warning(request, form.errors)
                        return redirect(url)
                if edit == 1:
                    amount = 0
                    if request.POST.getlist('title'):
                        for i in range(len(request.POST.getlist('title'))):
                            if len(request.POST.getlist('title')) > 1:
                                amount += int(request.POST.getlist('seller_quantity')[i])
                            else:
                                amount += int(request.POST['seller_quantity'])
                    if models.Variants.objects.filter(product__id=id).exists():
                        for i in range(len(request.POST.getlist('current_title'))):
                            if len(request.POST.getlist('current_title')) > 1:
                                amount += int(request.POST.getlist('current_seller_quantity')[i])
                            else:
                                amount += int(request.POST['current_seller_quantity'])
                    if not amount == get_object_or_404(models.Product, id=id, user=request.user).amount:
                        messages.add_message(request, messages.WARNING, f'{"جمع موجودي نزد فروشنده گوناگوني ها بايد با تعداد موجودی نزد فروشنده اوليه محصول برابر باشد. موجودي اوليه: "}{get_object_or_404(models.Product, id=id, user=request.user).amount}')
                        return redirect(url)
                    elif amount == get_object_or_404(models.Product, id=id, user=request.user).amount:
                        if get_object_or_404(models.Product, id=id, user=request.user).wrong_variant_seller_quantity:
                            update_wrong_variant_seller_quantity = get_object_or_404(models.Product, id=id, user=request.user)
                            update_wrong_variant_seller_quantity.wrong_variant_seller_quantity = False
                            update_wrong_variant_seller_quantity.save()

                    edit_review = 0

                    if request.POST.getlist('current_title'):
                        for i in range(len(request.POST.getlist('current_title'))):
                            if len(request.POST.getlist('current_title')) > 1:
                                if not models.Images.objects.filter(id=request.POST.getlist('current_image_id')[i]).exists():
                                    messages.add_message(request, messages.WARNING, f"{'گالري اي با آيدي '}{request.POST.getlist('current_image_id')[i]}{' وجود ندارد.'}")
                                    return redirect(url)
                                data = get_object_or_404(models.Variants, id=int(request.POST.getlist('current_id')[i]), product__user=request.user)

                                data.title = request.POST.getlist('current_title')[i]
                                if request.POST.getlist('current_title')[i] != data.title:
                                    edit_review += 1

                                if request.POST['variant_type'] == 'Size-Color' or request.POST['variant_type'] == 'Color':
                                    if 'current_color' in request.POST:
                                        data.color_id = request.POST.getlist('current_color')[i]
                                    else:
                                        data.color_id = None
                                    if int(request.POST.getlist('current_color')[i]) != data.color.id:
                                        edit_review += 1

                                if request.POST['variant_type'] == 'Size-Color' or request.POST['variant_type'] == 'Size':
                                    if 'current_size' in request.POST:
                                        data.size_id = request.POST.getlist('current_size')[i]
                                    else:
                                        data.size_id = None
                                    if int(request.POST.getlist('current_size')[i]) != data.size.id:
                                        edit_review += 1

                                data.image_id = request.POST.getlist('current_image_id')[i]
                                if int(request.POST.getlist('current_image_id')[i]) != data.image_id:
                                    edit_review += 1

                                data.seller_quantity = request.POST.getlist('current_seller_quantity')[i]

                                data.price = request.POST.getlist('current_price')[i]
                                if int(request.POST.getlist('current_price')[i]) != data.price:
                                    edit_review += 1

                                data.save()
                            else:
                                if not models.Images.objects.filter(id=request.POST.get('current_image_id')).exists():
                                    messages.add_message(request, messages.WARNING, f"{'گالري اي با آيدي '}{request.POST.get('current_image_id')}{' وجود ندارد.'}")
                                    return redirect(url)
                                data = get_object_or_404(models.Variants, id=int(request.POST.get('current_id')), product__user=request.user)
                                data.title = request.POST.get('current_title')
                                if request.POST.get('current_title') != data.title:
                                    edit_review += 1

                                if request.POST['variant_type'] == 'Size-Color' or request.POST['variant_type'] == 'Color':
                                    if 'current_color' in request.POST:
                                        data.color_id = request.POST.get('current_color')
                                    else:
                                        data.color_id = None
                                    if int(request.POST.get('current_color')) != data.color.id:
                                        edit_review += 1

                                if request.POST['variant_type'] == 'Size-Color' or request.POST['variant_type'] == 'Size':
                                    if 'current_size' in request.POST:
                                        data.size_id = request.POST.get('current_size')
                                    else:
                                        data.size_id = None
                                    if int(request.POST.get('current_size')) != data.size.id:
                                        edit_review += 1

                                data.image_id = request.POST.get('current_image_id')
                                if int(request.POST.get('current_image_id')) != int(data.image_id):
                                    edit_review += 1

                                data.seller_quantity = request.POST.get('current_seller_quantity')
                                if int(request.POST.get('current_seller_quantity')) != int(data.seller_quantity):
                                    edit_review += 1

                                data.price = request.POST.get('current_price')
                                if int(request.POST.get('current_price')) != int(data.price):
                                    edit_review += 1

                                data.save()

                    if request.POST.getlist('title'):
                        edit_review += 1
                        for i in range(len(request.POST.getlist('title'))):
                            data = models.Variants()
                            data.product_id = id
                            if len(request.POST.getlist('title')) > 1:
                                if not models.Images.objects.filter(id=request.POST.getlist('image_id')[i]).exists():
                                    messages.add_message(request, messages.WARNING, f"{'گالري اي با آيدي '}{request.POST.getlist('image_id')[i]}{' وجود ندارد.'}")
                                    return redirect(url)
                                data.title = request.POST.getlist('title')[i]
                                if request.POST['variant_type'] == 'Size-Color' or request.POST['variant_type'] == 'Color':
                                    data.color_id = request.POST.getlist('color')[i]
                                if request.POST['variant_type'] == 'Size-Color' or request.POST['variant_type'] == 'Size':
                                    data.size_id = request.POST.getlist('size')[i]
                                data.image_id = request.POST.getlist('image_id')[i]
                                data.seller_quantity = request.POST.getlist('seller_quantity')[i]
                                data.price = request.POST.getlist('price')[i]
                            else:
                                if not models.Images.objects.filter(id=request.POST.get('image_id')).exists():
                                    messages.add_message(request, messages.WARNING, f"{'گالري اي با آيدي '}{request.POST.get('image_id')}{' وجود ندارد.'}")
                                    return redirect(url)
                                data.title = request.POST.get('title')
                                if request.POST['variant_type'] == 'Size-Color' or request.POST['variant_type'] == 'Color':
                                    data.color_id = request.POST.get('color')
                                if request.POST['variant_type'] == 'Size-Color' or request.POST['variant_type'] == 'Size':
                                    data.size_id = request.POST.get('size')
                                data.image_id = request.POST.get('image_id')
                                data.seller_quantity = request.POST.get('seller_quantity')
                                data.price = request.POST.get('price')
                            data.save()

                    product.variant = request.POST['variant_type']
                    product.save()
                    if request.POST['variant_type'] != product.variant:
                        edit_review += 1

                    if edit_review > 0:
                        product = get_object_or_404(models.Product, id=id, user=request.user)
                        if models.Variants.objects.filter(product__id=id).exists():
                            product.status = 'Edit-On-Review'
                        product.save()

                    if edit == 1:
                        if edit_review <= 0:
                            messages.add_message(request, messages.INFO, f"{'محصول'} {product} {'با موفقيت ويرايش شد'}")
                        elif edit_review > 0:
                            messages.add_message(request, messages.INFO, f"{'محصول'} {product} {'با موفقيت ويرايش شد و درحال بررسي است'}")
                    elif edit == 0:
                        messages.add_message(request, messages.INFO, f"{'محصول'} {product} {'با موفقيت ساخته شد و درحالت پيش نويس قرار دارد. در اين حالت فقط شما قادر به ديدن و ويرايش آن هستيد. براي ثبت نهايي بر روي ثبت كليك كنيد'}")
                    return redirect('seller:my_products')
            else:
                messages.warning(request, 'لطفا نوع گوناگوني را مشخص كنيد')
                return redirect(url)
    else:
        context.update({'not_allowed': 'شما قابليت فروشندگي نداريد!'})
    return render(request, 'seller/product_variant_create_update.html', context)


@login_required()
def product_final_submit(request, id):
    url = request.META.get('HTTP_REFERER')
    product = get_object_or_404(models.Product, id=id, user=request.user)
    if not product.lack_in_gallery:
        product.status = 'Create-On-Review'
        product.save()
        messages.success(request, f"{'محصول'} {product} {'با موفقيت ثبت شد. پس از بررسي نتيجه را از طريق پيامك اعلام خواهيم كرد'}")
        return redirect(url)
    else:
        raise Http404


@login_required()
def del_product_gal(request, id):
    url = request.META.get('HTTP_REFERER')
    gal = get_object_or_404(models.Images, id=id, product__user=request.user)
    gal.delete()
    product = get_object_or_404(models.Product, id=gal.product.id, user=request.user)
    gallery_count = models.Images.objects.filter(product_id=product.id).count()
    if gallery_count < 4:
        product.lack_in_gallery = True
        product.save()
    return redirect(url)


@login_required()
def del_product_var(request, id):
    url = request.META.get('HTTP_REFERER')
    var = get_object_or_404(models.Variants, id=id, product__user=request.user)
    var.delete()
    return redirect(url)


def sellers(request):
    qs = seller_account.objects.filter(seller=True, ghost=False, seller_status='true')
    month_top_sold = None
    if models.Product.objects.filter(sold__gt=0).exists() and models.Product.objects.filter(sold__gt=0).count() > 12:
        month_top_sold = qs.annotate(num=Sum('vendor__sold')).order_by('-num').distinct()[:10]
    month_popular_sellers = None
    if qs.filter(users_rate__isnull=False).exists() and qs.filter(users_rate__isnull=False) > 12:
        month_popular_sellers = qs.order_by('-users_rate')[:10]
    month_top_viewed = None
    if models.Product.objects.filter(views__gt=0).exists() and models.Product.objects.filter(views__gt=0).count() > 12:
        month_top_viewed = qs.annotate(num=Sum('vendor__views')).order_by('-num').distinct()[:10]
    new_sellers = None
    if qs.count() > 12:
        new_sellers = qs.order_by('-date_joined')[:10]
    brand = models.Brand.objects.all()
    maincat = models.Category.objects.filter(parent__isnull=True)

    if month_top_sold or month_popular_sellers or month_top_viewed or new_sellers:
        if request.GET:
            default = False
        else:
            default = True
    else:
        default = False

    qs1 = None
    qs2 = None
    qs3 = None

    search = request.GET.get('search')
    Art = request.GET.get('Art')
    Material = request.GET.get('Material')
    Tool = request.GET.get('Tool')
    View = request.GET.get('View')
    Sold = request.GET.get('Sold')
    Satisfaction = request.GET.get('Satisfaction')
    Cat = request.GET.get('Cat')
    Brand = request.GET.get('Brand')

    if is_valid_queryparam(search):
        qs = qs.filter(Q(slug__icontains=search) | Q(seller_title__icontains=search)).distinct()

    if is_valid_queryparam(Art):
        qs1 = qs.filter(vendor__product_type='Art').distinct()

    if is_valid_queryparam(Material):
        qs2 = qs.filter(vendor__product_type='Material').distinct()

    if is_valid_queryparam(Tool):
        qs3 = qs.filter(vendor__product_type='Tool').distinct()

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
        qs = qs.filter(vendor__category__id=Cat).distinct()

    if is_valid_queryparam(Brand):
        qs = qs.filter(vendor__brand__id=Brand).distinct()

    if is_valid_queryparam(View):
        qs = qs.annotate(views_num=Sum('vendor__views')).order_by('-views_num').distinct()

    if is_valid_queryparam(Sold):
        qs = qs.annotate(sold_num=Sum('vendor__sold')).order_by('-sold_num').distinct()

    if is_valid_queryparam(Satisfaction):
        qs = qs.order_by('-users_rate')

    qs_count = qs.count()

    paginator = Paginator(qs, 12)
    page = request.GET.get('page')
    qs = paginator.get_page(page)

    current_cat = None
    if Cat:
        current_cat = get_object_or_404(models.Category, id=Cat)

    current_brand = None
    if Brand:
        current_brand = get_object_or_404(models.Brand, id=Brand)

    context = {
        'sellers_qs': qs,
        'default': default,
        'sellers_count': qs_count,
        'full_path': request.build_absolute_uri(),
        'maincat': maincat,
        'brand': brand,
        'current_cat': current_cat,
        'current_brand': current_brand,
        'month_top_sold': month_top_sold,
        'month_popular_sellers': month_popular_sellers,
        'month_top_viewed': month_top_viewed,
        'new_sellers': new_sellers,
        'search': search,
    }
    return render(request, 'seller/sellers.html', context)


def seller_page(request, slug):
    seller = get_object_or_404(seller_account, slug=slug)
    qs = models.Product.objects.filter(user=seller, status='Active')
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

    current_cat = None
    if is_valid_queryparam(Cat):
        current_cat = get_object_or_404(models.Category, id=Cat)
    current_brand = None
    if is_valid_queryparam(Brand):
        current_brand = get_object_or_404(models.Brand, id=Brand)

    product_type = 0
    art = models.Product.objects.filter(user=seller, product_type='Art', status='Active').exists()
    if art:
        product_type += 1
    material = models.Product.objects.filter(user=seller, product_type='Material', status='Active').exists()
    if material:
        product_type += 1
    tool = models.Product.objects.filter(user=seller, product_type='Tool', status='Active').exists()
    if tool:
        product_type += 1

    context = {
        'products': qs,
        'products_count': qs_count,
        'product_type': product_type,
        'maincat': maincat,
        'brand': brand,
        'current_cat': current_cat,
        'current_brand': current_brand,
        'seller': seller,
        'full_path': request.build_absolute_uri(),
        'art': art,
        'material': material,
        'tool': tool,
        'search': search,
    }
    return render(request, 'seller/seller_page.html', context)


@login_required()
def seller_request(request):
    url = request.META.get('HTTP_REFERER')
    context = {}
    if not request.user.seller:
        if request.method == 'POST':
            form = SellerRequest(request.POST, request.FILES, instance=request.user)
            if form.is_valid():
                data = get_object_or_404(seller_account, id=request.user.id)
                data.seller_title = form.cleaned_data['seller_title']
                data.shaba_number = form.cleaned_data['shaba_number']
                data.national_card_image = form.cleaned_data['national_card_image']
                data.phone_number = form.cleaned_data['phone_number']
                data.slug = form.cleaned_data['slug']
                data.profile_image = form.cleaned_data['profile_image']
                data.commitment_to_send = form.cleaned_data['commitment_to_send']
                data.request_seller = True
                data.save()
                messages.success(request,
                                 'درخواست شما با موفقيت ارسال شد. حداكثر تا 48 ساعت آينده بررسي كرده و نتيجه را اعلام خواهيم كرد')
                return redirect(url)
            else:
                messages.warning(request, form.errors)
    else:
        context.update({'not_allowed': 'شما در حال حاضر فروشنده ميباشيد!'})
    return render(request, 'seller/seller_request.html', context)


@login_required()
def my_products(request):
    context = {}
    if request.user.seller:
        products = models.Product.objects.filter(user=request.user).order_by('-update_time')
        search = request.GET.get('search')
        status = request.GET.get('status')
        time = request.GET.get('time')
        amount = request.GET.get('amount')

        if is_valid_queryparam(search):
            products = products.filter(Q(name__icontains=search) | Q(productid__exact=search)).distinct()

        if is_valid_queryparam(status):
            if status == 'On-Review':
                products = products.filter(Q(status='Create-On-Review') | Q(status='Edit-On-Review')).distinct()
            else:
                products = products.filter(status=f"{status}").distinct()

        if amount == '1':
            products = products.order_by('-sold')

        elif amount == '2':
            products = products.order_by('sold')

        if amount == '3':
            products = products.order_by('-views')

        elif amount == '4':
            products = products.order_by('views')

        if amount == '5':
            products = products.order_by('-store_amount')

        elif amount == '6':
            products = products.order_by('store_amount')

        if time == '1':
            products = products.order_by('-update_time')

        elif time == '2':
            products = products.order_by('update_time')

        if time == '3':
            products = products.order_by('-create_time')

        elif time == '4':
            products = products.order_by('create_time')

        paginator = Paginator(products, 8)
        page = request.GET.get('page')
        products = paginator.get_page(page)
        context.update({'products': products, 'search': search})
    else:
        context.update({'not_allowed': 'شما قابليت فروشندگي نداريد!'})
    return render(request, 'seller/my_products.html', context)


@login_required()
def product_delete(request, id):
    product = get_object_or_404(models.Product, id=id, user=request.user)
    context = {}
    if request.user.seller:
        if product.sold == 0:
            product = get_object_or_404(models.Product, id=id, user=request.user)
            context.update({'product': product})
            if request.method == 'POST':
                product.delete()
                return redirect('seller:my_products')
        else:
            context.update({
                'not_allowed_to_delete': 'از انجايي كه تعدادي از اين محصول به فروش رفته شما قادر به حذف اين محصول نيستيد'})
    else:
        context.update({'not_allowed': 'شما قابليت فروشندگي نداريد!'})
    return render(request, 'seller/product_delete.html', context)


@login_required()
def send_product_to_store(request, id):
    url = request.META.get('HTTP_REFERER')
    context = {}
    if request.user.seller:
        product = get_object_or_404(models.Product, id=id, user=request.user)
        if product.variant != 'None':
            context.update({'variants': models.Variants.objects.filter(product=product)})
        if product.status == 'Active':
            history = seller_model.ProductCharge.objects.filter(product=product)
            paginator = Paginator(history, 12)
            page = request.GET.get('page')
            history = paginator.get_page(page)
            context.update({"product": product, 'history': history})
            if request.method == 'POST':
                form = seller_model.ProductChargeForm(request.POST)
                if product.variant != 'None':
                    product_charge = seller_model.ProductCharge()
                    product_charge.product = product
                    amount = 0
                    for i in range(len(request.POST.getlist('type'))):
                        if len(request.POST.getlist('type')) > 1:
                            if request.POST.getlist('amount')[i]: amount += int(request.POST.getlist('amount')[i])
                        else:
                            amount += int(request.POST.get('amount'))
                    product_charge.amount = amount
                    product_charge.save()

                    for i in range(len(request.POST.getlist('type'))):
                        data = seller_model.ProductChargeVariants()
                        data.product_charge = product_charge
                        if len(request.POST.getlist('type')) > 1:
                            if request.POST.getlist('amount')[i]: data.amount = request.POST.getlist('amount')[i]
                            data.type = request.POST.getlist('type')[i]
                            data.variant_title = get_object_or_404(models.Variants, id=int(request.POST.getlist('var_id')[i]), product__user=request.user)
                        else:
                            data.amount = request.POST.get('amount')
                            data.type = request.POST.get('type')
                            data.variant_title = get_object_or_404(models.Variants, id=int(request.POST.get('var_id')), product__user=request.user)
                        data.save()
                    messages.success(
                        request,
                        'تعداد محصول با موفقيت ذخيره شد. موجودي انبار پس از تحويل و تاييد ادمين افزايش خواهد يافت')
                    return redirect(url)
                else:
                    if form.is_valid():
                        data = seller_model.ProductCharge()
                        data.amount = request.POST['amount']
                        data.type = request.POST['type']
                        data.product = product
                        data.save()
                        messages.success(
                            request,
                            'تعداد محصول با موفقيت ذخيره شد. موجودي انبار پس از تحويل و تاييد ادمين افزايش خواهد يافت')
                        return redirect(url)
                    else:
                        messages.warning(request, form.errors)
                        return redirect(url)
        else:
            context.update({'not_allowed_to_charge': 'شما قادر به شارژ محصولي كه وضعيت آن تاييد شده نميباشيد نيستيد!'})
    else:
        context.update({'not_allowed': 'شما قابليت فروشندگي نداريد!'})
    return render(request, 'seller/send_product_to_store.html', context)


@login_required()
def order(request):
    context = {}
    if request.user.seller:
        seller_order = models.SellerOrder.objects.filter(seller=request.user).order_by('-create_at')
        for order in seller_order:
            if not order.send:
                order.notif = False
                order.save()
        paginator = Paginator(seller_order, 8)
        page = request.GET.get('page')
        seller_order = paginator.get_page(page)
        context.update({'order': seller_order})
    else:
        context.update({'not_allowed': 'شما قابليت فروشندگي نداريد!'})
    return render(request, 'seller/order.html', context)


@login_required()
def order_detail(request, id):
    context = {}
    if request.user.seller:
        order = get_object_or_404(models.SellerOrder, id=id, seller=request.user)
        order_item = models.SellerOrderItem.objects.filter(seller_order_id=id, seller=request.user)
        order_charge = seller_model.OrderCharge.objects.filter(seller=request.user, order=order)
        if order_charge.exists():
            context.update({'order_charge': order_charge[0]})
        context.update({
            'order': order,
            'order_item': order_item,
        })
    else:
        context.update({'not_allowed': 'شما قابليت فروشندگي نداريد!'})
    return render(request, 'seller/order_detail.html', context)


@login_required
def order_charge_list(request, id):
    context = {}
    if request.user.seller:
        order = get_object_or_404(models.SellerOrder, id=id, seller=request.user)
        order_item = models.SellerOrderItem.objects.filter(seller_order_id=order.id, seller=request.user,
                                                           from_amount=True)
        order_charge = seller_model.OrderCharge.objects.filter(seller=request.user, order=order)
        if order_charge.exists():
            context.update({'order_charge': order_charge[0]})
        context.update({'order_item': order_item, 'order': order})
    else:
        context.update({'not_allowed': 'شما قابليت فروشندگي نداريد!'})
    return render(request, 'seller/order_charge.html', context)


@login_required
def order_charge(request, id):
    order = get_object_or_404(models.SellerOrder, id=id, seller=request.user)
    order.notif = False
    order.save()
    order_item = models.SellerOrderItem.objects.filter(seller_order_id=order.id, seller=request.user)

    order_charge_obj = seller_model.OrderCharge()
    order_charge_obj.order_id = id
    order_charge_obj.seller = request.user
    order_charge_obj.seller_order_id = id
    order_charge_obj.save()

    for item in order_item:
        order_charge_item_obj = seller_model.OrderChargeItem()
        order_charge_item_obj.order_charge_id = order_charge_obj.id
        order_charge_item_obj.product_id = item.product.id
        order_charge_item_obj.quantity = item.quantity
        order_charge_item_obj.price = item.price
        order_charge_item_obj.variant = item.variant
        order_charge_item_obj.save()
    messages.success(request, "گزارش ارسال به انبار با موفقیت ثبت شد")
    return redirect('seller:order_charge_list', id)


@login_required()
def faq(request):
    context = {}
    if not request.user.seller:
        context.update({'not_allowed': 'شما قابليت فروشندگي نداريد!'})
    return render(request, 'seller/faq.html', context)


@login_required()
def financial(request):
    url = request.META.get('HTTP_REFERER')
    context = {}
    if request.user.seller:
        history = seller_model.Withdraw.objects.filter(user=request.user).order_by('-create_time')[:5]
        history_count = seller_model.Withdraw.objects.filter(user=request.user).count()
        order = models.SellerOrder.objects.filter(seller=request.user, order__status="Delivered")
        paginator = Paginator(order, 12)
        page = request.GET.get('page')
        order = paginator.get_page(page)
        context.update({'history': history, 'history_count': history_count, 'order': order})
        if request.method == 'POST':
            form = seller_model.WithdrawForm(request.POST)
            if form.is_valid():
                if form.cleaned_data['amount'] >= 10000:
                    if form.cleaned_data['amount'] <= request.user.withdrawable_balance:
                        data = seller_model.Withdraw()
                        data.amount = form.cleaned_data['amount']
                        data.user = request.user
                        data.save()

                        user_data = get_object_or_404(seller_account, id=request.user.id)
                        user_data.balance -= form.cleaned_data['amount']
                        user_data.save()

                        messages.success(request, 'درخواست پرداخت شما با موفقيت ارسال شد. هزينه هاي درخواستي فروشندگان در اخر هر هفته واريز خواهد شد')
                        return redirect(url)
                    else:
                        messages.warning(request, "مقدار هزينه درخواست شده از مقدار موجودي شما بيشتر است!")
                        return redirect(url)
                else:
                    messages.warning(request, "مقدار هزينه درخواست شده از حداقل مقدار برداشت كمتر است!")
                    return redirect(url)
            else:
                messages.warning(request, form.errors)
                return redirect(url)
    else:
        context.update({'not_allowed': 'شما قابليت فروشندگي نداريد!'})
    return render(request, 'seller/financial.html', context)


@login_required()
def transactions(request):
    context = {}
    if request.user.seller:
        history = seller_model.Withdraw.objects.filter(
            user=request.user).order_by('-create_time')
        paginator = Paginator(history, 12)
        page = request.GET.get('page')
        history = paginator.get_page(page)
        context.update({'history': history})
    else:
        context.update({'not_allowed': 'شما قابليت فروشندگي نداريد!'})
    return render(request, 'seller/transactions.html', context)


@login_required()
def edit_seller_info(request):
    url = request.META.get('HTTP_REFERER')
    context = {}
    if request.user.seller:
        if request.method == 'POST':
            form = SellerEdit(request.POST, request.FILES, instance=request.user)
            if form.is_valid():
                form.seller_title = form.cleaned_data['seller_title']
                form.phone_number = form.cleaned_data['phone_number']
                form.slug = form.cleaned_data['slug']
                if request.user.profile_image:
                    form.profile_image = request.user.profile_image
                else:
                    form.profile_image = form.cleaned_data['profile_image']
                form.save()
                messages.success(request, 'اطلاعات با موفقيت به روز رساني شد')
                return redirect(url)
            else:
                messages.warning(request, form.errors)
    else:
        context.update({'not_allowed': 'شما قابليت فروشندگي نداريد!'})
    return render(request, 'seller/edit_seller_info.html', context)


@login_required()
def ghost_mode(request):
    url = request.META.get('HTTP_REFERER')
    context = {}
    if request.user.seller:
        if request.method == 'POST':
            if request.user.ghost:
                user_data = get_object_or_404(seller_account, id=request.user.id)
                user_data.ghost = False
                user_data.save()
                messages.success(request, 'حالت روح با موفقيت غيرفعال شد')
                return redirect(url)
            if not request.user.ghost:
                return redirect('seller:redirect_to_ticket_ghost_mode')
    else:
        context.update({'not_allowed': 'شما قابليت فروشندگي نداريد!'})
    return render(request, 'seller/ghost_mode.html', context)


@login_required
def ticket_list(request):
    url = request.META.get('HTTP_REFERER')
    context = {}
    if request.user.seller:
        ticket = seller_model.Ticket.objects.filter(user=request.user).order_by("-create_at")
        user_unread_count = ticket.filter(reply__user_status='UnRead').count()
        paginator = Paginator(ticket, 8)
        page = request.GET.get('page')
        ticket = paginator.get_page(page)
        context.update({'ticket': ticket, 'user_unread_count': user_unread_count})
        if request.method == 'POST':
            form = seller_model.TicketForm(request.POST, request.FILES)
            if form.is_valid():
                data = seller_model.Ticket()
                data.user_id = request.user.id
                data.category = form.cleaned_data['category']
                data.subject = form.cleaned_data['subject']
                data.text = form.cleaned_data['text']
                data.document = form.cleaned_data['document']
                data.ip = request.META.get('REMOTE_ADDR')
                data.save()
                messages.success(request, "تیکت جديد با موفقيت ارسال شد")
                return redirect(url)
    else:
        context.update({'not_allowed': 'شما قابليت فروشندگي نداريد!'})
    return render(request, 'seller/ticket_list.html', context)


@login_required
def ticket_detail(request, id):
    url = request.META.get('HTTP_REFERER')
    context = {'ticket_id': id}
    if request.user.seller:
        reply = seller_model.TicketReply.objects.filter(Q(ticket__user=request.user) | Q(ticket__to=request.user), ticket__id=id).order_by('-create_at')
        if reply:
            if len(reply) > 1:
                for r in reply:
                    r.user_status = 'Read'
                    r.save()
            else:
                reply.update(user_status='Read')
            paginator = Paginator(reply, 8)
            page = request.GET.get('page')
            reply = paginator.get_page(page)
            context.update({'reply': reply})
        ticket = get_object_or_404(seller_model.Ticket, Q(ticket__user=request.user) | Q(ticket__to=request.user), id=id)
        context.update({'ticket': ticket})
        if ticket.status == 'Open':
            if request.method == 'POST':
                form = seller_model.TicketReplyForm(request.POST, request.FILES)
                if form.is_valid():
                    data = seller_model.TicketReply()
                    data.ticket_id = id
                    data.text = form.cleaned_data['text']
                    data.document = form.cleaned_data['document']
                    data.ip = request.META.get('REMOTE_ADDR')
                    data.user_id = request.user.id
                    parent = None
                    try:
                        parent_id = int(request.POST.get("parent_id"))
                    except:
                        parent_id = None
                    if parent_id:
                        parent_qs = seller_model.TicketReply.objects.filter(Q(ticket__user=request.user) | Q(ticket__to=request.user), id=parent_id)
                        if parent_qs.exists() and parent_qs.count() == 1:
                            parent = parent_qs.first()
                    data.parent = parent
                    data.save()
                    messages.success(request, "پاسخ شما با موفقيت ارسال شد")
                    return redirect(url)
        else:
            context.update({'not_allowed_to_reply': 'اين تيكت بسته شده است. شما قادر به ارسال پاسخ نيستيد'})
    else:
        context.update({'not_allowed': 'شما قابليت فروشندگي نداريد!'})
    return render(request, 'seller/ticket_detail.html', context)


@login_required
def redirect_to_ticket_disable_product(request):
    msg = "با ذكر نام محصول دليل خود را براي غير فعال كردن محصول بيان كنيد"
    messages.add_message(request, messages.INFO, msg)
    return redirect('seller:ticket_list')


@login_required
def redirect_to_ticket_ghost_mode(request):
    msg = "با ايجاد يك تيكت دليل خود را براي فعال سازي حالت روح بيان كنيد"
    messages.add_message(request, messages.INFO, msg)
    return redirect('seller:ticket_list')


@login_required
def redirect_to_ticket_edit_seller_info(request):
    msg = "مواردي كه خواهان ويرايش آنها هستيد را به طور كامل ذكر كنيد"
    messages.add_message(request, messages.INFO, msg)
    return redirect('seller:ticket_list')

