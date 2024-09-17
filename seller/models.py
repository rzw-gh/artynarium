import os
from datetime import datetime

from django import forms
from django.conf import settings
from django.db import models
from django.utils import timezone
from shop.models import Product, Variants, SellerOrder
now = datetime.now()
User = settings.AUTH_USER_MODEL


class ProductCharge(models.Model):
    TYPE = (
        ('None', '---'),
        ('New', 'جديد'),
        ('From_Seller', 'از نزد فروشنده')
    )
    type = models.CharField(max_length=11, choices=TYPE, default='None', verbose_name='نوع')
    admin_confirmation = models.BooleanField(default=False, verbose_name='تاييديه تحويل توسط ادمين')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='محصول')
    amount = models.PositiveIntegerField(verbose_name='تعداد')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ ثبت')

    def __str__(self):
        return f'{self.product.name} - {self.product.id}'

    class Meta:
        ordering = ('-create_time',)
        verbose_name = 'شارژ محصول'
        verbose_name_plural = 'شارژ محصولات'


class ProductChargeForm(forms.ModelForm):
    class Meta:
        model = ProductCharge
        fields = ['amount']


class ProductChargeVariants(models.Model):
    TYPE = (
        ('New', 'جديد'),
        ('From_Seller', 'از نزد فروشنده')
    )
    type = models.CharField(max_length=11, choices=TYPE, default='From_Seller', verbose_name='نوع')
    variant_title = models.CharField(max_length=100, verbose_name='گوناگوني')
    product_charge = models.ForeignKey(ProductCharge, on_delete=models.CASCADE, verbose_name='شارژ محصول')
    amount = models.PositiveIntegerField(blank=True, null=True, verbose_name='تعداد')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ ثبت')

    def __str__(self):
        return f'{self.variant_title}'

    class Meta:
        ordering = ('-create_time',)
        verbose_name = 'گوناگوني شارژ محصول'
        verbose_name_plural = 'گوناگوني هاي شارژ محصولات'


class ProductChargeVariantsForm(forms.ModelForm):
    class Meta:
        model = ProductCharge
        fields = ['amount', 'type']


class Withdraw(models.Model):
    payed = models.BooleanField(default=False, verbose_name="پرداخت شده")
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             verbose_name='كاربر', default=1)
    amount = models.DecimalField(
        max_digits=10, decimal_places=0, default=0,
        verbose_name='مقدار درخواست پرداختي به تومان')
    order_tracking_number = models.PositiveIntegerField(
        verbose_name='شماره پيگيري پرداخت', blank=True, null=True)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ درخواست')
    pay_date = models.DateTimeField(verbose_name='تاريخ پرداخت', default=now)

    def __str__(self):
        return self.user.first_name

    class Meta:
        ordering = ('-create_time',)
        verbose_name = 'پرداخت'
        verbose_name_plural = 'پرداخت'


class WithdrawForm(forms.ModelForm):
    class Meta:
        model = Withdraw
        fields = ['amount']


class Ticket(models.Model):
    STATUS = (
        ('Open', 'باز'),
        ('Closed', 'بسته'),
    )
    CATEGORY = (
        ('FINANCE', 'امور مالي'),
        ('PRODUCTS', 'محصولات'),
        ('ACCOUNT', 'حساب كاربري'),
        ('OTHERS', 'ساير موارد'),
    )
    status = models.CharField(max_length=6, choices=STATUS, default='Open', verbose_name='وضعیت')
    category = models.CharField(max_length=8, choices=CATEGORY, verbose_name='دسته بندي')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='ايجاد شده توسط')
    to = models.ForeignKey(User, on_delete=models.CASCADE, default=1, related_name='to_user', verbose_name='مخاطب')
    subject = models.CharField(max_length=100, verbose_name='عنوان')
    text = models.TextField(verbose_name='متن پيام')
    document = models.FileField(upload_to='documents/tickets/%Y/%m/%d', blank=True, null=True)
    ip = models.CharField(max_length=20, blank=True, verbose_name='آدرس ای پی')
    create_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self):
        return self.subject

    class Meta():
        verbose_name = 'تیکت'
        verbose_name_plural = 'تیکت ها'

    def user_unread_count(self):
        return TicketReply.objects.filter(ticket=self, user_status='UnRead').count()

    def document_name(self):
        return os.path.basename(self.document.name)


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['category', 'subject', 'text', 'document']


class TicketReply(models.Model):
    STATUS = (
        ('Read', 'خوانده شده'),
        ('UnRead', 'خوانده نشده'),
    )
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='reply', verbose_name='تيكت')
    user_status = models.CharField(max_length=6, choices=STATUS, default='UnRead', verbose_name='وضعیت كاربر')
    user = models.ForeignKey(User, default=1, on_delete=models.CASCADE, verbose_name='فرستنده')
    text = models.TextField(verbose_name='متن پيام')
    document = models.FileField(upload_to='documents/ticket_replies/%Y/%m/%d', blank=True, null=True)
    ip = models.CharField(max_length=20, blank=True, verbose_name='آدرس ای پی')
    create_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.ticket.subject

    class Meta():
        verbose_name = 'پاسخ تيكت'
        verbose_name_plural = 'پاسخ تيكت ها'

    def document_name(self):
        return os.path.basename(self.document.name)


class TicketReplyForm(forms.ModelForm):
    class Meta:
        model = TicketReply
        fields = ['text', 'document']


class OrderCharge(models.Model):
    seller = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='فروشنده')
    order = models.ForeignKey(SellerOrder, on_delete=models.CASCADE, verbose_name='سفارش')
    sent = models.BooleanField(default=False, verbose_name='ارسال شد')
    admin_confirmation = models.BooleanField(default=False, verbose_name='تاييديه تحويل توسط ادمين')
    seller_order_id = models.BigIntegerField(editable=False, verbose_name='شماره سفارش')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ ثبت')

    def __str__(self):
        return f'{self.seller.seller_title} {self.seller_order_id}'

    class Meta:
        ordering = ('-create_time',)
        verbose_name = 'شارژ سفارش'
        verbose_name_plural = 'شارژ سفارشات'


class OrderChargeItem(models.Model):
    order_charge = models.ForeignKey(OrderCharge, on_delete=models.CASCADE, related_name='order_charge_item', verbose_name='شارژ سفارش')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='محصول')
    variant = models.ForeignKey(Variants, on_delete=models.CASCADE, blank=True, null=True, verbose_name='گوناگونی')
    quantity = models.IntegerField(verbose_name='تعداد')
    price = models.FloatField(verbose_name='قیمت')
    create_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ساخت')
    update_at = models.DateTimeField(auto_now=True, verbose_name='زمان به روز رسانی')

    def __str__(self):
        return f'{self.product.name} {self.product.id}'

    class Meta:
        verbose_name = 'ایتم شارژ سفارش'
        verbose_name_plural = 'ایتم های شارژ سفارش'
