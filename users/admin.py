from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None,
         {
             'fields':
             ('balance', 'performance', 'activate_payback', 'card_number', 'request_seller', 'seller_status', 'in_time_supply', 'commitment_to_send', 'ghost', 'slug', 'profile_image', 'shaba_number',
              'national_card_image', 'seller_title', 'phone_number_verified', 'seller',
              'email', 'first_name', 'last_name', 'phone_number', 'zipcode', 'address',
              'state', 'city', 'password', 'last_login')}),
        ('Permissions',
         {
             'fields':
             ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions',)}),)
    add_fieldsets = (
        (None,
         {'classes': ('wide',),
          'fields':
          ('seller_status', 'shaba_number', 'ghost', 'slug', 'profile_image',
           'national_card_image', 'seller_title', 'phone_number_verified', 'seller',
           'email', 'first_name', 'last_name', 'phone_number', 'zipcode', 'address',
           'state', 'city', 'password1', 'password2',)}),)
    list_display = ('email', 'seller', 'ghost', '__str__', 'phone_number',
                    'is_superuser', 'is_staff', 'last_login', 'id')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'request_seller')
    search_fields = ('email', 'phone_number', 'name', 'id',)
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions',)
    search_fields = ('name', 'phone_number', 'email', )
    readonly_fields = ('balance',)


admin.site.register(User, UserAdmin)
