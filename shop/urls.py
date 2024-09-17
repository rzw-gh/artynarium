from django.urls import path, re_path
from django.views.generic.base import TemplateView
from . import views

app_name = 'shop'
urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Search
    path('search/', views.search, name='search'),
    path('autocomplete/', views.autocomplete, name='autocomplete'),

    # Shop
    path('shop/', views.shop, name='shop'),
    path('shop/featured/', views.featured, name='featured'),
    path('shop/special/', views.special, name='special'),

    # Product
    path('addcomment/<int:id>', views.addcomment, name='addcomment'),
    path('comment_upvote/<int:id>', views.comment_upvote, name='comment_upvote'),
    path('ajaxcolor/', views.ajaxcolor, name='ajaxcolor'),

    # Category
    path('category/', views.cat, name='cat'),
    path('category/<int:id>/<slug:slug>/', views.category, name='category'),

    # Cart
    path('addtocart/<int:id>', views.addtocart, name='addtocart'),
    path('delitem/<int:id>', views.delitem, name='delitem'),
    path('del_order_item/<int:id>', views.del_order_item, name='del_order_item'),
    path('cancel_order/<int:id>', views.cancel_order, name='cancel_order'),
    path('cart/', views.cart, name='cart'),
    path('out_of_stock_reorder/<int:id>', views.out_of_stock_reorder, name='out_of_stock_reorder'),
    path('ajax_cart_amount/<int:id>', views.ajax_cart_amount, name='ajax_cart_amount'),
    path('checkout/', views.checkout, name='checkout'),
    path('validate_coupon/', views.validate_coupon, name='validate_coupon'),
    path('order/<int:id>', views.order, name='order'),

    # Bank
    path('pay/<int:id>/', views.pay, name='pay'),
    path('callback/', views.callback, name='callback'),
    path('last_payments/', views.last_payments, name='last_payments'),

    # Account
    path('account/edit_address', views.edit_address, name='edit_address'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('my_orders', views.my_orders, name='my_orders'),
    path('my_order_detail/<int:id>', views.my_order_detail, name='my_order_detail'),
    path('account_security', views.account_security, name='account_security'),

    # About
    path('about/', TemplateView.as_view(template_name='shop/about.html'), name='about'),

    # FAQ
    path('faq/', TemplateView.as_view(template_name='shop/faq.html'), name='faq'),

    # Instagram
    # path('instagram/', views.instagram, name='instagram'),

    # Contact
    path('contact/', views.contact, name='contact'),

    re_path('product/(?P<id>\d+)/(?P<slug>[-\w]+)/', views.product, name='product'),
    re_path('add_remove/(?P<id>\d+)/(?P<slug>[-\w]+)/', views.wishlist_add_remove, name='add_remove'),
]
