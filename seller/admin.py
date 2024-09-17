from django.contrib import admin
from . import models


class ProductChargeVariantsInline(admin.TabularInline):
    model = models.ProductChargeVariants
    extra = 0


class ProductChargeAdmin(admin.ModelAdmin):
    list_display = ['product', 'amount', 'admin_confirmation']
    search_fields = ['product__name', 'product__id']
    readonly_fields = ('product', 'amount',)
    list_filter = ['admin_confirmation']
    inlines = [ProductChargeVariantsInline]


class WithdrawAdmin(admin.ModelAdmin):
    readonly_fields = ('user', 'amount', 'create_time')

    def has_delete_permission(self, request, obj=None):
        return False


class TicketReplyInline(admin.TabularInline):
    model = models.TicketReply
    readonly_fields = ['user_status', 'user', 'ip']
    ordering = ["-create_at"]
    extra = 0

    def has_delete_permission(self, request, obj=None):
        return False


class TicketAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'user_unread_count', 'user', 'create_at', 'ip']
    search_fields = ['id', 'user__email', 'subject', 'ip', 'category'] # category be like --> finance
    list_filter = ['reply__user_status', 'create_at']
    readonly_fields = ['subject', 'text', 'user', 'ip']
    inlines = [TicketReplyInline]


class OrderChargeItemInline(admin.TabularInline):
    model = models.OrderChargeItem
    ordering = ["-create_at"]
    extra = 0

    def has_delete_permission(self, request, obj=None):
        return False


class OrderChargeAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'admin_confirmation']
    search_fields = ['id', 'user__email', 'seller_order_id']
    list_filter = ['admin_confirmation']
    readonly_fields = ['seller_order_id']
    inlines = [OrderChargeItemInline]


admin.site.register(models.OrderCharge, OrderChargeAdmin)
admin.site.register(models.Ticket, TicketAdmin)
admin.site.register(models.ProductCharge, ProductChargeAdmin)
admin.site.register(models.Withdraw, WithdrawAdmin)
