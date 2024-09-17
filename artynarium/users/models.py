from django.contrib.auth.models import (AbstractBaseUser, BaseUserManager,
                                        PermissionsMixin)
from datetime import datetime, timedelta
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Sum, Count
from django.utils import timezone
from shop import models as shop_model
from seller.models import Withdraw
import pytz


class UserManager(BaseUserManager):

    def _create_user(self, email, password, is_staff, is_superuser, **extra_fields):
        if not email:
            raise ValueError('کاربر باید ایمیل داشته باشد')
        now = timezone.now()
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            is_staff=is_staff,
            is_active=True,
            is_superuser=is_superuser,
            last_login=now,
            date_joined=now,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password, **extra_fields):
        return self._create_user(email, password, False, False, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        user = self._create_user(email, password, True, True, **extra_fields)
        user.phone_number = '09999999999'
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    STATUS = (
        ('true', 'فروشنده تاييد شده'),
        ('false', 'فروشنده تاييد نشده'),
        ('under_review', 'در حال بررسي'),
    )
    commitment_to_send = models.CharField(max_length=250, default='3 روز', verbose_name='تعهد ارسال')
    in_time_supply = models.CharField(max_length=250, default='100', help_text='درصد', verbose_name='تامین به موقع')
    request_seller = models.BooleanField(default=False, verbose_name='درخواست فروشندگي')
    seller = models.BooleanField(default=False, verbose_name='فروشنده')
    activate_payback = models.BooleanField(default=False, verbose_name='فعال سازي بازپرداخت')
    ghost = models.BooleanField(default=False, verbose_name='روح')
    seller_status = models.CharField(max_length=12, choices=STATUS, default='false', verbose_name='وضعيت فروشندگي')
    balance = models.DecimalField(max_digits=10, decimal_places=0, default=0, help_text='به تومان',
                                  verbose_name='موجودي', editable=False)
    performance = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(10)],
                                      verbose_name="عملكرد فروشنده", default=10)
    shaba_number = models.CharField(blank=True, null=True, max_length=24, verbose_name='شماره شبا')
    card_number = models.CharField(blank=True, null=True, max_length=16, verbose_name='شماره كارت')
    national_card_image = models.ImageField(blank=True, null=True, upload_to='image/user/seller/%Y/%m/%d',
                                            verbose_name='تصوير كارت ملي')
    profile_image = models.ImageField(blank=True, null=True, upload_to='image/user/seller/%Y/%m/%d',
                                      verbose_name='عكس پروفايل')
    slug = models.SlugField(blank=True, null=True, max_length=15, unique=True, verbose_name='ايدي اختصاصي فروشنده')
    seller_title = models.CharField(max_length=254, blank=True, null=True, verbose_name='عنوان فروشنده')
    phone_number_verified = models.BooleanField(default=False, blank=True, null=True, verbose_name='شماره همراه تاييد شده')
    users_rate = models.IntegerField(verbose_name='امتياز خريداران', null=True, blank=True)
    rate = models.IntegerField(verbose_name='امتیاز', null=True, blank=True)
    first_name = models.CharField(max_length=254, verbose_name='نام')
    last_name = models.CharField(max_length=254, verbose_name='نام خانوادگی')
    email = models.EmailField(max_length=254, unique=True, verbose_name='ایمیل')
    phone_number = models.CharField(max_length=11, unique=True, verbose_name='شماره همراه')
    zipcode = models.CharField(blank=True, null=True, max_length=10, verbose_name='کد پستی')
    address = models.CharField(blank=True, null=True, max_length=200, verbose_name='آدرس')
    state = models.CharField(blank=True, null=True, max_length=21, verbose_name='استان')
    city = models.CharField(blank=True, null=True, max_length=21, verbose_name='شهر')
    is_staff = models.BooleanField(default=False, verbose_name='پرسنل')
    is_superuser = models.BooleanField(default=False, verbose_name='مدير')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    last_login = models.DateTimeField(null=True, blank=True, verbose_name='آخرین تاریخ ورود')
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ عضويت')

    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'
        ordering = ('-date_joined',)

    def __str__(self):
        return f'{self.first_name}  {self.last_name}'

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    @property
    def average_seller_rate(self):
        reviews = shop_model.Comment.objects.filter(product__user=self, status='Allowed').aggregate(average=Avg('rate'))
        avg = 0
        if reviews["average"] is not None:
            avg = float(reviews["average"])
        return avg

    @property
    def last_week_sale_count(self):
        last_week = datetime.today() - timedelta(days=7)
        order_item = shop_model.SellerOrderItem.objects.filter(
            user=self, seller_order__order__status="Delivered",
            seller_order__order__delivered_at__gte=last_week).aggregate(
            quantity=Count('quantity'))
        sold = 0
        if order_item["quantity"] is not None:
            sold = order_item["quantity"]
        return sold

    @property
    def last_week_user_sale(self):
        last_week = datetime.today() - timedelta(days=7)
        order_item = shop_model.SellerOrderItem.objects.filter(
            user=self, seller_order__order__status="Delivered",
            seller_order__order__delivered_at__gte=last_week).aggregate(
            item_total=Sum('item_total'))
        total = 0
        if order_item["item_total"] is not None:
            total = order_item["item_total"]
        return total

    @property
    def last_week_sale_change(self):
        a_week_ago = datetime.today() - timedelta(days=7)
        two_week_ago = datetime.today() - timedelta(days=14)
        a_week_ago_order_item = shop_model.SellerOrderItem.objects.filter(
            user=self, seller_order__order__status="Delivered",
            seller_order__order__delivered_at__gte=a_week_ago).aggregate(
            item_total=Sum('item_total'))
        two_week_ago_order_item = shop_model.SellerOrderItem.objects.filter(
            user=self, seller_order__order__status="Delivered",
            seller_order__order__delivered_at__gte=two_week_ago,
            seller_order__order__delivered_at__lte=a_week_ago).aggregate(
            item_total=Sum('item_total'))

        change = 0
        if a_week_ago_order_item["item_total"] is not None:
            change = 100
            if two_week_ago_order_item["item_total"] is not None:
                change = ((a_week_ago_order_item - two_week_ago_order_item) / two_week_ago_order_item) * 100
        return change

    @property
    def last_week_site_profit(self):
        last_week = datetime.today() - timedelta(days=7)
        order_item = shop_model.SellerOrderItem.objects.filter(
            user=self, seller_order__order__status="Delivered",
            seller_order__order__delivered_at__gte=last_week).aggregate(
            item_pursuant=Sum('item_pursuant'))
        total = 0
        if order_item["item_pursuant"] is not None:
            total = order_item["item_pursuant"]
        return total

    @property
    def last_week_site_profit_change(self):
        a_week_ago = datetime.today() - timedelta(days=7)
        two_week_ago = datetime.today() - timedelta(days=14)
        a_week_ago_order_item = shop_model.SellerOrderItem.objects.filter(
            user=self, seller_order__order__status="Delivered",
            seller_order__order__delivered_at__gte=a_week_ago).aggregate(
            item_pursuant=Sum('item_pursuant'))
        two_week_ago_order_item = shop_model.SellerOrderItem.objects.filter(
            user=self, seller_order__order__status="Delivered",
            seller_order__order__delivered_at__gte=two_week_ago,
            seller_order__order__delivered_at__lte=a_week_ago).aggregate(
            item_pursuant=Sum('item_pursuant'))

        change = 0
        if a_week_ago_order_item["item_pursuant"] is not None:
            change = 100
            if two_week_ago_order_item["item_pursuant"] is not None:
                change = ((a_week_ago_order_item - two_week_ago_order_item) / two_week_ago_order_item) * 100
        return change

    @property
    def user_products_comments_buyer_count(self):
        return shop_model.Comment.objects.filter(product__user=self, parent=None, status='Allowed', buyer=True).count()

    @property
    def user_products_comments_count(self):
        return shop_model.Comment.objects.filter(product__user=self, parent=None, status='Allowed').count()

    @property
    def user_products_satisfaction_percent(self):
        user_products = shop_model.Product.objects.filter(user=self)
        user_products_sold_count = 0
        for product in user_products:
            user_products_sold_count += product.sold
        total = 0
        for product in user_products:
            averagereview_buyer_count = shop_model.Comment.objects.filter(product_id=product.id, status='Allowed',
                                                                          parent=None, buyer=True).count()
            averagereview_buyer = shop_model.Comment.objects.filter(product_id=product.id, status='Allowed',
                                                                    parent=None, buyer=True).aggregate(
                average=Avg('rate'))
            if averagereview_buyer["average"] or averagereview_buyer_count > 0:
                total += averagereview_buyer_count * averagereview_buyer["average"]
        if total == 0:
            return 0
        return ((total / user_products_sold_count) * 100) / 5

    @property
    def user_products_count(self):
        return shop_model.Product.objects.filter(user=self).count()

    @property
    def withdrawable_balance(self):
        balance = 0
        time_threshold = datetime.now(pytz.timezone('Asia/Tehran')) - timedelta(days=7)
        for seller_balance in SellerBalance.objects.filter(user=self, create_at__lte=time_threshold):
            balance += seller_balance.amount
        for withdraw in Withdraw.objects.filter(user=self):
            balance -= withdraw.amount
        return balance


class SellerBalance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='كاربر')
    amount = models.DecimalField(max_digits=10, decimal_places=0, default=0, help_text='به تومان', verbose_name='موجودي', editable=False)
    order = models.ForeignKey(shop_model.Order, on_delete=models.CASCADE, verbose_name='سفارش')
    order_item = models.ForeignKey(shop_model.OrderItem, on_delete=models.CASCADE, verbose_name='ایتم سفارش')
    create_at = models.DateTimeField(default=timezone.now, editable=False, verbose_name='زمان ساخت')
