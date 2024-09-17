import admin_thumbnails
from django.contrib import admin
from mptt.admin import DraggableMPTTAdmin
from shop import models


###### Category ######
class CategoryAdmin(DraggableMPTTAdmin):
    mptt_indent_field = "title"
    search_fields = ['catproduct__name', 'title', 'id']
    list_filter = ['parent', 'create_time', 'important']
    list_display = ('tree_actions', 'indented_title',
                    'related_products_count', 'related_products_cumulative_count')
    list_display_links = ('indented_title',)
    prepopulated_fields = {'slug': ('title',)}

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # Add cumulative product count
        qs = models.Category.objects.add_related_count(
            qs,
            models.Product,
            'category',
            'products_cumulative_count',
            cumulative=True)

        # Add non cumulative product count
        qs = models.Category.objects.add_related_count(
            qs,
            models.Product,
            'category',
            'products_count',
            cumulative=False)
        return qs

    def related_products_count(self, instance):
        return instance.products_count

    related_products_count.short_description = 'Related products (for this specific category)'

    def related_products_cumulative_count(self, instance):
        return instance.products_cumulative_count

    related_products_cumulative_count.short_description = 'Related products (in tree)'


admin.site.register(models.Category, CategoryAdmin)


###### End Category ######


###### Product ######
@admin_thumbnails.thumbnail('image')
class ProductImageInline(admin.TabularInline):
    model = models.Images
    readonly_fields = ('id',)
    extra = 0


class ProductVariantsInline(admin.TabularInline):
    model = models.Variants
    readonly_fields = ('image_tag',)
    extra = 0
    show_change_link = True


class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'amount', 'sold', 'views', 'brand', 'productid', 'status', 'user', 'image_tag']
    search_fields = ['name', 'brand__title', 'category__title', 'id']
    readonly_fields = ['productid', 'sold', 'views', 'create_time', 'profit']
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ['create_time', 'update_time', 'category__title']
    inlines = [ProductImageInline, ProductVariantsInline]


admin.site.register(models.Product, ProductAdmin)


@admin_thumbnails.thumbnail('image')
class ImagesAdmin(admin.ModelAdmin):
    list_display = ['product', 'title', 'id', 'image_thumbnail']
    search_fields = ['product__name', 'title', 'id']
    extra = 0


# admin.site.register(models.Images, ImagesAdmin)


class ColorAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'color_tag']
    search_fields = ['name', 'code']


admin.site.register(models.Color, ColorAdmin)


class SizeAdmin(admin.ModelAdmin):
    list_display = ['name', 'id']
    search_fields = ['name', 'id']


admin.site.register(models.Size, SizeAdmin)


class VariantsAdmin(admin.ModelAdmin):
    list_display = ['title', 'color', 'size', 'product',
                    'price', 'quantity', 'id', 'image_tag']
    search_fields = ['title', 'color', 'size', 'product__name', 'price', 'id']


# admin.site.register(models.Variants, VariantsAdmin)


class CommentAdmin(admin.ModelAdmin):
    list_display = ['parent', 'product', 'user', 'subject',
                    'rate', 'status', 'id', 'create_at']
    list_filter = ['status', 'create_at', 'update_at']
    search_fields = ['product__name', 'user__first_name', 'subject', 'id']
    readonly_fields = ('ip', 'user', 'product', 'rate', 'id')


admin.site.register(models.Comment, CommentAdmin)


###### End Product ######


###### Cart ######
class CartAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'quantity',
                    'price', 'amount', 'id']
    search_fields = ['product__name',
                     'user__first_name', 'user__last_name', 'id']
    list_filter = ['create_at']
    readonly_fields = ('from_store_amount', 'from_amount')


# admin.site.register(models.Cart, CartAdmin)


class OrderItemInline(admin.TabularInline):
    model = models.OrderItem
    readonly_fields = ('user', 'product', 'price', 'quantity', 'amount')
    can_delete = False
    extra = 0


class SellerOrderInline(admin.TabularInline):
    model = models.SellerOrder
    readonly_fields = ('seller', 'order', 'send', 'order_total', 'order_pursuant', 'order_profit')
    can_delete = False
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    list_display = ['orderid', 'first_name', 'last_name',
                    'phone', 'state', 'city', 'totalcost', 'status', 'ip']
    list_filter = ['status', 'create_at', 'update_at']
    readonly_fields = (
        'user', 'orderid', 'address', 'state', 'city', 'zipcode', 'shipping_method',
        'totalcost', 'first_name', 'last_name', 'email', 'phone', 'ip', 'total')
    search_fields = ['orderid', 'first_name', 'last_name', 'email',
                     'phone', 'city', 'state', 'zipcode', 'ip', 'shipping_method']
    can_delete = False
    inlines = [OrderItemInline, SellerOrderInline]


admin.site.register(models.Order, OrderAdmin)


class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'price', 'quantity', 'amount', 'id']
    list_filter = ['create_at', 'update_at']
    search_fields = ['product__name', 'user__first_name', 'user__last_name', 'id']
    readonly_fields = ('from_store_amount', 'from_amount')


# admin.site.register(models.OrderItem, OrderItemAdmin)


class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['authority', 'invoice_date']
    list_filter = ['invoice_date']
    search_fields = ['authority', 'order__orderid']


# admin.site.register(models.Invoice, InvoiceAdmin)
###### End Cart ######


###### Contact ######
class ContactAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'subject', 'status', 'ip']
    list_filter = ['create_at', 'status']
    search_fields = ['first_name', 'last_name',
                     'subject', 'phone_number', 'email']


admin.site.register(models.Contact, ContactAdmin)


###### End Contact ######


###### Wishlist ######
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'wished_item', 'added_date']
    list_filter = ['added_date']
    search_fields = ['user__first_name', 'user__last_name',
                     'wished_item__name', 'user__phone_number', 'user__email']


admin.site.register(models.Wishlist, WishlistAdmin)


###### End Wishlist ######


###### ObjectViewed ######
class ObjectViewedAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'id']
    list_filter = ['timestamp', 'user']
    search_fields = ['user__first_name', 'user__last_name',
                     'id', 'user__phone_number', 'user__email']


admin.site.register(models.ObjectViewed, ObjectViewedAdmin)


###### End ObjectViewed ######


###### Brand ######
class BrandAdmin(admin.ModelAdmin):
    list_display = ['title', 'id']
    search_fields = ['title', 'id']


admin.site.register(models.Brand, BrandAdmin)
admin.site.register(models.Sms)


###### End Brand ######
# class SellerOrderAdmin(admin.ModelAdmin):
#     readonly_fields = ['send']
# admin.site.register(models.SellerOrder, SellerOrderAdmin)
# admin.site.register(models.SellerOrderItem)
class CouponAdmin(admin.ModelAdmin):
    readonly_fields = ['usage_count']
    list_display = ['active', '__str__', 'usage_count', 'amount']


admin.site.register(models.Coupon, CouponAdmin)
