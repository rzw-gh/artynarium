from datetime import datetime
from random import randrange

from ckeditor_uploader.fields import RichTextUploadingField
from django import forms
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg
from django.utils import timezone
from django.utils.safestring import mark_safe
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel
from PIL import Image
from .signals import object_viewed_signal
from .utils import get_client_ip
from config.utils import jalali_converter

# def jpublish(self):
#     return jalali_converter(self.publish)


# def save(self):
#     # Opening the uploaded image
#     im = Image.open(self.image)
#
#     output = BytesIO()
#
#     # Resize/modify the image
#     im = im.resize((100, 100))
#
#     # after modifications, save it to the output
#     im.save(output, format='JPEG', quality=90)
#     output.seek(0)
#
#     # change the imagefield value to be the newley modifed image value
#     self.image = InMemoryUploadedFile(output, 'ImageField', "%s.jpg" % self.image.name.split('.')[0], 'image/jpeg',
#                                       sys.getsizeof(output), None)
#
#     super(Report_item, self).save()


User = settings.AUTH_USER_MODEL


def create_id():
    now = datetime.now()
    return f'{now.year}{now.month}{now.day}{now.second}{randrange(100, 999)}'


class ObjectViewed(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True,
                             verbose_name='کاربر')  # User instance instance.id
    ip_address = models.CharField(
        max_length=220, blank=True, null=True, verbose_name='آدرس ای پی')  # IP Field
    # User, Product, Order, Cart, Address
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, blank=True, null=True, verbose_name='نوع')
    object_id = models.PositiveIntegerField(
        verbose_name='ایدی ایتم', blank=True, null=True)  # User id, Product id, Order id,
    content_object = GenericForeignKey(
        'content_type', 'object_id')  # Product instance
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "%s مشاهده شده در %s" % (self.content_object, self.timestamp)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'ایتم های مشاهده شده توسط کاربر'
        verbose_name_plural = 'ایتم های مشاهده شده توسط کاربر'


def object_viewed_receiver(sender, instance, request, *args, **kwargs):
    c_type = ContentType.objects.get_for_model(sender)
    new_view_obj = ObjectViewed.objects.create(
        user=request.user,
        ip_address=get_client_ip(request),
        content_type=c_type,
        object_id=instance.id
    )


object_viewed_signal.connect(object_viewed_receiver)


class Category(MPTTModel):
    parent = TreeForeignKey('self', blank=True, null=True, related_name='children',
                            on_delete=models.CASCADE, verbose_name='زیر دسته')
    title = models.CharField(max_length=50, verbose_name='عنوان')
    icon = models.CharField(
        max_length=30,
        help_text='به وبسایت https://icons8.com/line-awesome مراجعه کنید و کلاس ایکون مورد نظرات را اینجا الصاق کنید',
        verbose_name='ایکون')
    image = models.ImageField(
        upload_to='image/shop/category/%Y/%m/%d', verbose_name='تصویر')
    slug = models.SlugField(null=False, unique=True, verbose_name='اسلاگ')
    important = models.BooleanField(
        default=False,
        help_text='اگر تیک این گزینه فعال باشد، عنوان این دسته بندی در نوبار سایت به صورت پر رنگ نمایش داده خواهد شد',
        verbose_name='مهم')
    create_time = models.DateTimeField(
        auto_now_add=True, verbose_name='زمان ساخت')
    update_time = models.DateTimeField(
        auto_now=True, verbose_name='زمان به روز رسانی')

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-create_time']
        verbose_name = 'دسته بندی'
        verbose_name_plural = 'دسته بندی ها'

    class MPTTMeta:
        order_insertion_by = ['title']

    def __str__(self):  # __str__ method elaborated later in
        # post.  use __unicode__ in place of
        full_path = [self.title]
        k = self.parent
        while k is not None:
            full_path.append(k.title)
            k = k.parent
        return ' / '.join(full_path[::-1])

    def get_children(self):
        return self.get_descendants(include_self=False)

    def has_child(self):
        if self.get_descendants(include_self=False):
            return True
        return False


class Brand(models.Model):
    title = models.CharField(max_length=50, verbose_name='نام برند')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'برند'
        verbose_name_plural = 'برند ها'


class SearchForm(forms.Form):
    autos = forms.CharField(max_length=100)
    # catid = forms.IntegerField()


class ProductManager(models.Manager):
    def slider(self):
        return self.filter(slider=True)

    def featured(self):
        return self.filter(featured=True)

    def special(self):
        return self.filter(special=True)


class Product(models.Model):
    VARIANTS = (
        ('None', 'بدون گوناگونی'),
        ('Size', 'اندازه'),
        ('Color', 'رنگ'),
        ('Size-Color', 'رنگ-اندازه'),
    )
    TYPES = (
        ('Art', 'هنر'),
        ('Material', 'مواد اوليه'),
        ('Tool', 'ابزار'),
    )
    STATUS = (
        ('Active', 'تاييد شده'),
        ('Draft', 'پيش نويس'),
        ('Create-On-Review', 'در حال بررسي'),
        ('Edit-On-Review', 'در حال بررسي ويرايش'),
        ('Disabled', 'غيرفعال'),
    )
    multi_seller = models.BooleanField(default=False, verbose_name="چندين فروشنده")
    status = models.CharField(max_length=16, choices=STATUS, default='Draft', verbose_name='وضعيت محصول')
    lack_in_gallery = models.BooleanField(default=False, verbose_name='كمبود گالري')
    wrong_variant_seller_quantity = models.BooleanField(default=False, verbose_name='عدم تطباق موجودي نزد فروشنده گوناگوني')
    productid = models.CharField(max_length=13, default=create_id, editable=False, verbose_name='ایدی محصول')
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1, verbose_name='فروشنده', related_name='vendor')
    product_type = models.CharField(max_length=8, choices=TYPES, default='Art', verbose_name='نوع محصول')
    category = models.ManyToManyField(Category, related_name='catproduct', verbose_name='دسته بندی')
    brand = models.ForeignKey(
        Brand, related_name='pbrand', on_delete=models.CASCADE, verbose_name='برند',
        null=True, blank=True, help_text='فیلد اختیاری')
    name = models.CharField(max_length=150, verbose_name='عنوان')
    image = models.ImageField(
        upload_to='image/shop/product/%Y/%m/%d',
        help_text='از تصویری در سایز 1200 در 1200 استفاده کنید', verbose_name='تصویر')
    slug = models.SlugField(null=False, unique=True, allow_unicode=True, verbose_name='اسلاگ')
    views = models.IntegerField(
        default=0, editable=False, verbose_name='بازدید')
    create_time = models.DateTimeField(
        auto_now_add=True, verbose_name='زمان ساخت')
    update_time = models.DateTimeField(
        auto_now=True, verbose_name='زمان به روز رسانی')
    price = models.DecimalField(max_digits=10, decimal_places=0,
                                default=0, help_text='قیمت به تومان', verbose_name='قیمت')
    pursuant = models.DecimalField(
        max_digits=2, decimal_places=0, default=0, help_text='درصد',
        verbose_name='كارمزد محصول')
    profit = models.DecimalField(
        max_digits=10, decimal_places=0, default=0, help_text='به تومان', editable=False,
        verbose_name='سود خالص')
    amount = models.IntegerField(default=0, verbose_name='موجودی نزد فروشنده')
    purchase_amount_limit = models.IntegerField(
        default=0, verbose_name='سقف خريد موجودي نزد فروشنده')
    store_amount = models.IntegerField(default=0, verbose_name='موجودی در انبار')
    purchase_store_amount_limit = models.IntegerField(
        default=0, verbose_name='سقف خريد موجودی در انبار')
    sold = models.IntegerField(
        default=0, editable=False, verbose_name='فروخته شده')
    description = RichTextUploadingField(verbose_name='توضیحات')
    special = models.BooleanField(default=False, verbose_name='خاص')
    featured = models.BooleanField(default=False, verbose_name='ویژه')
    banner_image = models.ImageField(
        upload_to='image/shop/product/%Y/%m/%d',
        help_text='از تصویری در سایز 280 در 280 استفاده کنید', verbose_name='تصویر بنر')
    hover_image = models.ImageField(
        upload_to='image/shop/product/%Y/%m/%d',
        help_text='از تصویری در سایز 280 در 280 استفاده کنید',
        verbose_name='تصویر بنر (شناور)')
    slider = models.BooleanField(default=False, verbose_name='اسلایدر')
    slider_title = models.CharField(
        max_length=200, blank=True, null=True, verbose_name='عنوان اسلایدر')
    slider_description = models.CharField(
        max_length=300, blank=True, null=True, verbose_name='توضیح مختصر اسلایدر')
    slider_image = models.ImageField(
        upload_to='image/shop/product/slider/%Y/%m/%d', blank=True, null=True,
        help_text='از تصویری در سایز 780 در 441 استفاده کنید',
        verbose_name='تصویر اسلایدر')
    related_art = models.ManyToManyField('self', blank=True, related_name="related_product", verbose_name='هنر مربوطه')
    related_tool = models.ManyToManyField('self', blank=True, related_name="related_product",
                                          verbose_name='ابزار مربوطه')
    related_material = models.ManyToManyField('self', blank=True, related_name="related_product",
                                              verbose_name='مواد اوليه مربوطه')
    variant = models.CharField(
        max_length=10, choices=VARIANTS, default='None', verbose_name='گوناگونی')

    class Meta:
        ordering = ('-create_time',)
        verbose_name = 'محصول'
        verbose_name_plural = 'محصولات'

    objects = ProductManager()

    def __str__(self):
        return self.name

    @property
    def vars(self):
        return self.vars

    def image_tag(self):
        if self.image.url is not None:
            return mark_safe('<img src="{}" height="50"/>'.format(self.image.url))
        else:
            return ""

    def averagereview(self):
        reviews = Comment.objects.filter(
            product=self, status='Allowed', parent=None).aggregate(
            average=Avg('rate'))
        avg = 0
        if reviews["average"] is not None:
            avg = float(reviews["average"])
        return avg

    def reviews(self):
        reviews = Comment.objects.filter(product=self, status='Allowed', parent=None).count()
        return reviews

    @property
    def total_amount(self):
        return (self.amount + self.store_amount)

    @property
    def variant_total_amount(self):
        variants = Variants.objects.get(product=self)
        return variants.seller_quantity + variants.quantity

    @property
    def comments_count(self):
        product = Product.objects.get(id=self.id)
        comment = Comment.objects.filter(product=product)
        return comment.count()

    def gallery_count(self):
        return Images.objects.filter(product=self).count()


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'product_type',
            'category',
            'name',
            'image',
            'slug',
            'price',
            'amount',
            'description',
            'banner_image',
            'hover_image'
        ]


class Coupon(models.Model):
    active = models.BooleanField(default=True, verbose_name='فعال')
    code = models.CharField(max_length=250, unique=True, verbose_name='كد')
    occasion = models.CharField(max_length=250, verbose_name='به مناسبت')
    amount = models.DecimalField(max_digits=10, decimal_places=0, help_text='به تومان', verbose_name='مقدار تخفيف')
    usage_count = models.IntegerField(default=0, editable=False, verbose_name='دفعات استفاده شده')
    create_at = models.DateTimeField(default=timezone.now, editable=False, verbose_name='زمان ساخت')
    valid_until = models.DateTimeField(verbose_name='معتبر تا')

    def __str__(self):
        return self.occasion

    class Meta:
        ordering = ['-valid_until']
        verbose_name = 'كوپن'
        verbose_name_plural = 'كوپن ها'


class Images(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='img_gal', verbose_name='محصول')
    title = models.CharField(max_length=50, blank=True, verbose_name='عنوان')
    image = models.ImageField(
        blank=True, upload_to='image/product/%Y/%m/%d', verbose_name='تصویر')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'گالری'
        verbose_name_plural = 'گالری'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        img = Image.open(self.image.path)
        if img.height > 1200 or img.width > 1200:
            output_size = (1200, 1200)
            img.thumbnail(output_size)
            img.save(self.image.path)


class ImagesForm(forms.ModelForm):
    class Meta:
        model = Images
        exclude = ('product',)


class Color(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name='اسم رنگ')
    code = models.CharField(
        max_length=10, unique=True, blank=True, null=True,
        help_text='به سایت https://htmlcolorcodes.com/ مراجعه کنید و کد هکس رنگ مورد نظر را بدون هشتگ در اینجا الصاق کنید',
        verbose_name='کد رنگ ')

    def __str__(self):
        return self.name

    def color_tag(self):
        if self.code is not None:
            return mark_safe('<p style="background-color:#%s">%s</p>' %
                             (self.code, self.name))

        else:
            return ""

    class Meta:
        verbose_name = 'رنگ'
        verbose_name_plural = 'رنگ ها'


class Size(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name='اندازه')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'سایز'
        verbose_name_plural = 'سایز ها'


class Variants(models.Model):
    title = models.CharField(max_length=100, verbose_name='عنوان')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='vars', verbose_name='محصول')
    color = models.ForeignKey(Color, on_delete=models.CASCADE, blank=True, null=True, verbose_name='رنگ')
    size = models.ForeignKey(Size, on_delete=models.CASCADE, blank=True, null=True, verbose_name='اندازه')
    image_id = models.IntegerField(verbose_name='ایدی تصویر')
    quantity = models.IntegerField(verbose_name='موجودی در انبار', default=0)
    seller_quantity = models.IntegerField(verbose_name='موجودی نزد فروشنده')
    price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name='قیمت')

    def __str__(self):
        if self.title:
            return self.title

    def image(self):
        img = Images.objects.get(id=self.image_id)
        if img.id is not None:
            varimage = img.image.url
        else:
            varimage = ""
        return varimage

    def image_tag(self):
        img = Images.objects.get(id=self.image_id)
        if img.id is not None:
            return mark_safe('<img src="{}" height="50"/>'.format(img.image.url))
        else:
            return ""

    class Meta:
        verbose_name = 'گوناگونی'
        verbose_name_plural = 'گوناگونی محصولات'


class VariantsForm(forms.ModelForm):
    class Meta:
        model = Variants
        fields = [
            'title',
            'color',
            'size',
            'image_id',
            'seller_quantity',
            'price',
        ]


class Comment(models.Model):
    STATUS = (
        ('Allowed', 'نمایش'),
        ('Unallowed', 'مخفی'),
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='comment', verbose_name='محصول')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='کاربر')
    parent = models.ForeignKey("self", on_delete=models.CASCADE, related_name='comment_parent', null=True, blank=True,
                               verbose_name='والد')
    subject = models.CharField(max_length=50, null=True, blank=True, verbose_name='عنوان')
    comment = models.CharField(max_length=5000, verbose_name='نظر')
    rate = models.IntegerField(default=1, verbose_name='امتیاز',
                               validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    helpful = models.PositiveIntegerField(default=0, verbose_name='لایک')
    ip = models.CharField(max_length=20, blank=True, verbose_name='آدرس ای پی')
    status = models.CharField(max_length=23, choices=STATUS, default='Unallowed', verbose_name='وضعیت')
    buyer = models.BooleanField(default=False)
    create_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ساخت')
    update_at = models.DateTimeField(auto_now=True, verbose_name='زمان به روز رسانی')

    def __str__(self):
        if self.subject:
            return self.subject
        return self.comment

    class Meta:
        ordering = ('-create_at',)
        verbose_name = 'نظر'
        verbose_name_plural = 'نظرات'

    def children(self):
        return Comment.objects.filter(parent=self)

    @property
    def is_parent(self):
        if self.parent is not None:
            return False
        return True


class CommentUpVote(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, verbose_name='كامنت')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='لايك كننده')
    upVoted = models.BooleanField(default=False)


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['subject', 'comment', 'rate']


class Wishlist(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name='کاربر')
    wished_item = models.ForeignKey(
        Product, on_delete=models.CASCADE, null=True, blank=True,
        verbose_name='محصول مورد علاقه')
    added_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'لیست علاقه مندی'
        verbose_name_plural = 'لیست علاقه مندی ها'


class Cart(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name='کاربر')
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='cart_product', verbose_name='محصول')
    variant = models.ForeignKey(
        Variants, on_delete=models.CASCADE, null=True, blank=True,
        verbose_name='گوناگونی')
    quantity = models.IntegerField(verbose_name='تعداد')
    from_store_amount = models.BooleanField(default=True, editable=False, verbose_name='از موجودي در انبار')
    from_amount = models.BooleanField(default=False, editable=False, verbose_name='از موجودي نزد فروشنده')
    out_of_stock = models.BooleanField(default=False, verbose_name='اتمام موجودی')
    create_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ساخت')

    def __str__(self):
        return self.product.name

    @property
    def price(self):
        return (self.product.price)

    @property
    def varamount(self):
        return (self.quantity * self.variant.price)

    @property
    def amount(self):
        return (self.quantity * self.product.price)

    class Meta:
        verbose_name = 'سبد خرید'
        verbose_name_plural = 'سبد های خرید'


class CartLimit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='کاربر')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='محصول')
    cart = models.ManyToManyField(Cart, verbose_name='سبد')
    first_purchase_store_amount_limit = models.IntegerField(verbose_name='اولین سقف خريد موجودی در انبار', default=0)
    purchase_store_amount_limit = models.IntegerField(verbose_name='سقف خريد موجودی در انبار', default=0)
    first_purchase_amount_limit = models.IntegerField(verbose_name='اولین سقف خريد موجودي نزد فروشنده', default=0)
    purchase_amount_limit = models.IntegerField(verbose_name='سقف خريد موجودي نزد فروشنده', default=0)
    store_amount_type = models.BooleanField(default=True)

    @property
    def total_variant_quantity(self):
        if not self.store_amount_type:
            return 0
        total_variant_quantity = 0
        cart_list = Cart.objects.filter(product=self.product, user=self.user, variant__isnull=False)
        for cart in cart_list:
            total_variant_quantity += cart.quantity
        return total_variant_quantity

    @property
    def total_variant_seller_quantity(self):
        if self.store_amount_type:
            return 0
        total_variant_seller_quantity = 0
        cart_list = Cart.objects.filter(product=self.product, user=self.user, variant__isnull=False)
        for cart in cart_list:
            total_variant_seller_quantity += cart.quantity
        return total_variant_seller_quantity

    @property
    def total_product_store_amount(self):
        if not self.store_amount_type:
            return 0
        total_product_store_amount = 0
        cart_list = Cart.objects.filter(product=self.product, user=self.user, variant__isnull=True)
        for cart in cart_list:
            total_product_store_amount += cart.quantity
        return total_product_store_amount

    @property
    def total_product_amount(self):
        if self.store_amount_type:
            return 0
        total_product_amount = 0
        cart_list = Cart.objects.filter(product=self.product, user=self.user, variant__isnull=True)
        for cart in cart_list:
            total_product_amount += cart.quantity
        return total_product_amount


class CartForm(forms.ModelForm):
    class Meta:
        model = Cart
        fields = ['quantity']


class Order(models.Model):
    STATUS = (
        ('Payment', 'در انتظار پرداخت'),
        ('Preparing', 'در حال آماده سازی'),
        ('OnShipping', 'در حال ارسال'),
        ('Canceled', 'لغو شده'),
        ('LackOfInventory', 'کمبود موجودی'),
        ('Delivered', 'تحویل داده شده'),
        ('Bank', 'در انتظار بانک'),
    )
    SHIPPING_METHOD = (
        ('Normal', 'عادی'),
        ('Express', 'پیشتاز'),
    )
    orderid = models.CharField(default=create_id, max_length=13, editable=False, verbose_name='شماره سفارش')
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, null=True, blank=True, verbose_name='كوپن')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='user_order', verbose_name='کاربر')
    email = models.CharField(max_length=300, verbose_name='ایمیل')
    first_name = models.CharField(max_length=100, verbose_name='نام')
    last_name = models.CharField(max_length=200, verbose_name='نام خانوادگی')
    phone = models.CharField(max_length=11, verbose_name='شماره همراه')
    zipcode = models.CharField(max_length=10, verbose_name='کد پستی')
    address = models.CharField(max_length=500, verbose_name='آدرس')
    state = models.CharField(max_length=21, verbose_name='استان')
    city = models.CharField(max_length=21, verbose_name='شهر')
    total = models.DecimalField(
        max_digits=10, decimal_places=0, verbose_name='جمع هزینه محصولات')
    totalcost = models.DecimalField(
        max_digits=10, decimal_places=0, verbose_name='جمع کل')
    shipping_method = models.CharField(
        max_length=8, choices=SHIPPING_METHOD, default='Normal', verbose_name='روش ارسال')
    status = models.CharField(
        max_length=15, choices=STATUS, default=None, verbose_name='وضعیت')
    admin_order_deliverment_confirmation = models.BooleanField(
        default=False, verbose_name='تاييديه تحويل سفارش توسط ادمين')
    ip = models.CharField(blank=True, max_length=20, verbose_name='آدرس ای پی')
    create_at = models.DateTimeField(default=timezone.now, editable=False, verbose_name='زمان ساخت')
    update_at = models.DateTimeField(auto_now=True, verbose_name='زمان به روز رسانی')
    delivered_at = models.DateTimeField(blank=True, null=True, verbose_name='زمان ساخت')
    note = models.TextField(blank=True, max_length=1000, verbose_name='یادداشت')
    delay = models.BooleanField(default=False)
    decreased_products_amount = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.orderid}'

    @property
    def itemss(self):
        return self.order_itemss

    class Meta:
        ordering = ('-create_at',)
        verbose_name = 'سفارش'
        verbose_name_plural = 'سفارشات'


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['state', 'city', 'zipcode',
                  'address', 'note', 'shipping_method']


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE,
                              related_name='order_itemss', verbose_name='سفارش')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name='کاربر')
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='product_order_item', verbose_name='محصول')
    variant = models.ForeignKey(
        Variants, on_delete=models.CASCADE, blank=True, null=True,
        verbose_name='گوناگونی')
    quantity = models.IntegerField(verbose_name='تعداد')
    price = models.FloatField(verbose_name='قیمت')
    amount = models.FloatField(verbose_name='كل')
    create_at = models.DateTimeField(
        auto_now_add=True, verbose_name='زمان ساخت')
    update_at = models.DateTimeField(
        auto_now=True, verbose_name='زمان به روز رسانی')
    from_store_amount = models.BooleanField(
        default=True, editable=False, verbose_name='از موجودي در انبار')
    from_amount = models.BooleanField(
        default=False, editable=False, verbose_name='از موجودي نزد فروشنده')
    out_of_stock = models.BooleanField(default=False, verbose_name='اتمام موجودی')

    def __str__(self):
        return f'{self.product.name} {self.product.id}'

    class Meta:
        verbose_name = 'ایتم سفارش'
        verbose_name_plural = 'ایتم های سفارش'


class SellerOrder(models.Model):
    seller = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='فروشنده')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name='سفارش')
    send = models.BooleanField(default=False, editable=False, verbose_name='نياز به ارسال')
    notif = models.BooleanField(default=True, editable=False, verbose_name='نوتيف')
    create_at = models.DateTimeField(default=timezone.now, editable=False, verbose_name='زمان ساخت')
    update_at = models.DateTimeField(auto_now=True, verbose_name='زمان به روز رسانی')
    order_total = models.DecimalField(max_digits=10, default=0, decimal_places=0, verbose_name='جمع هزینه محصولات')
    order_pursuant = models.DecimalField(max_digits=10, default=0, decimal_places=0, verbose_name='كارمزد سفارش')
    order_profit = models.DecimalField(max_digits=10, default=0, decimal_places=0, verbose_name='سود خالص سفارش')


class SellerOrderItem(models.Model):
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='seller_order_items', verbose_name='فروشنده')
    seller_order = models.ForeignKey(SellerOrder, on_delete=models.CASCADE, verbose_name='سفارش')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='محصول')
    variant = models.ForeignKey(Variants, on_delete=models.CASCADE, blank=True, null=True, verbose_name='گوناگونی')
    quantity = models.IntegerField(verbose_name='تعداد')
    price = models.FloatField(verbose_name='قیمت')
    item_total = models.DecimalField(max_digits=10, default=0, decimal_places=0, verbose_name='جمع هزینه محصول')
    item_pursuant = models.DecimalField(max_digits=10, default=0, decimal_places=0, verbose_name='كارمزد محصول')
    item_profit = models.DecimalField(max_digits=10, default=0, decimal_places=0, verbose_name='سود خالص محصول')
    from_store_amount = models.BooleanField(default=True, editable=False, verbose_name='از موجودي در انبار')
    from_amount = models.BooleanField(default=False, editable=False, verbose_name='از موجودي نزد فروشنده')
    create_at = models.DateTimeField(default=timezone.now, editable=False, verbose_name='زمان ساخت')
    update_at = models.DateTimeField(auto_now=True, verbose_name='زمان به روز رسانی')


class Sms(models.Model):
    CATEGORY = (
        ('Seller_Request', 'درخواست فروشندگي'),
        ('Seller', 'فروشنده'),
        ('Customer', 'مشتري'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='مخاطب')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True, verbose_name='سفارش مشتري')
    seller_order = models.ForeignKey(SellerOrder, on_delete=models.CASCADE, null=True, blank=True, verbose_name='سفارش فروشنده')
    category = models.CharField(max_length=14, choices=CATEGORY, null=True, blank=True, verbose_name='دسته پيامك')
    message_api_exception = models.TextField(max_length=5000, null=True, blank=True, verbose_name='خطاي API')
    message_http_exception = models.TextField(max_length=5000, null=True, blank=True, verbose_name='خطاي HTTP')
    message_id = models.CharField(max_length=1000, null=True, blank=True, verbose_name='ايدي پيامك')
    message_content = models.TextField(max_length=5000, null=True, blank=True, verbose_name='محتواي پيامك')
    message_status = models.BooleanField(null=True, blank=True, verbose_name='وضعيت ارسال پيامك')
    message_sender = models.CharField(max_length=250, null=True, blank=True, verbose_name='فرستنده پيامك')
    message_receptor = models.CharField(max_length=250, null=True, blank=True, verbose_name='دريافت كننده پيامك')
    message_data = models.TextField(max_length=5000, null=True, blank=True, verbose_name='ديتاي پيامك')
    message_cost = models.CharField(max_length=1000, null=True, blank=True, verbose_name='هزينه پيامك')
    create_at = models.DateTimeField(default=timezone.now, editable=False, verbose_name='زمان ساخت')

    def __str__(self):
        if self.message_receptor is None:
            return 'Err'
        return self.message_receptor

    class Meta:
        ordering = ['-create_at']
        verbose_name = 'پيامك'
        verbose_name_plural = 'پيامك ها'


class SmsForm(forms.ModelForm):
    class Meta:
        model = Sms
        fields = ['message_content']


class Invoice(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name='سفارش')
    order_items = models.TextField(verbose_name='ایتم های سفارش شده')
    invoice_date = models.DateTimeField(auto_now_add=True)
    authority = models.CharField(max_length=200, blank=True, null=True, verbose_name='شناسه پرداخت')

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'فاکتور'
        verbose_name_plural = 'فاکتور ها'


class Contact(models.Model):
    STATUS = (
        ('New', 'تازه'),
        ('Read', 'خوانده شده'),
    )
    status = models.CharField(
        max_length=10, choices=STATUS, default='New', verbose_name='وضعیت')
    first_name = models.CharField(max_length=50, verbose_name='نام')
    last_name = models.CharField(max_length=50, verbose_name='نام خانوداگی')
    email = models.EmailField(max_length=50, verbose_name='ایمیل')
    phone_number = models.CharField(max_length=11, verbose_name='شماره همراه')
    ip = models.CharField(blank=True, max_length=20, verbose_name='آدرس ای پی')
    subject = models.CharField(max_length=100, verbose_name='عنوان')
    text = models.TextField(max_length=1000, verbose_name='محتوا')
    create_at = models.DateTimeField(
        auto_now_add=True, verbose_name='زمان ساخت')

    def __str__(self):
        return f'{self.first_name} {self.last_name}    {self.last_name}'

    class Meta:
        verbose_name = 'تماس با ما'
        verbose_name_plural = 'تماس با ما'


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['first_name', 'last_name', 'email',
                  'phone_number', 'subject', 'text']


class UserCouponUsage(models.Model):
    used = models.BooleanField(default=False, editable=False, verbose_name='استفاده شده')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='استفاده كننده')
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, verbose_name='كوپن')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True, verbose_name='سفارش')

#
# class SchedulerJobs(models.Model):
#     TYPES = (
#         ('Order', 'سفارش'),
#         ('Cart', 'سبد خرید'),
#     )
#     STATUS = (
#         ('Completed', 'کامل شد'),
#         ('Processing', 'در حال انجام'),
#     )
#     type = models.CharField(max_length=5, choices=TYPES, verbose_name='نوع')
#     status = models.CharField(max_length=10, choices=STATUS, default='Processing', verbose_name='وضعیت')
#     order_id = models.IntegerField(null=True, blank=True, verbose_name='ایدی سفارش')
#     cart_id = models.IntegerField(null=True, blank=True, verbose_name='ایدی سبد خرید')
#     create_at = models.DateTimeField(default=timezone.now, editable=False, verbose_name='زمان ساخت')
