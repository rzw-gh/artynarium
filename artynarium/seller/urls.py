from django.urls import path
from . import views

app_name = 'seller'
urlpatterns = [
    path('sellers/', views.sellers, name='sellers'),
    path('seller/<slug:slug>/', views.seller_page, name='seller_page'),
    path('account/my_products/', views.my_products, name='my_products'),
    path('account/step_1/product_create/', views.product_create, name='product_create'),
    path('account/step_1/product_update/<int:id>', views.product_update, name='product_update'),
    path('account/step_2/product_gallery_create_update/<int:id>/<int:edit>', views.product_gallery_create_update, name='product_gallery_create_update'),
    path('account/step_2/del_product_gal/<int:id>/', views.del_product_gal, name='del_product_gal'),
    path('account/step_3/product_variant_create_update/<int:id>/<int:edit>', views.product_variant_create_update, name='product_variant_create_update'),
    path('account/step_3/del_product_var/<int:id>/', views.del_product_var, name='del_product_var'),
    path('account/product_final_submit/<int:id>', views.product_final_submit, name='product_final_submit'),
    path('account/delete_product/<int:id>', views.product_delete, name='delete_product'),
    path('account/order/', views.order, name='order'),
    path('account/order_detail/<int:id>', views.order_detail, name='order_detail'),
    path('account/send_product_to_store/<int:id>', views.send_product_to_store, name='send_product_to_store'),
    path('account/seller_request/', views.seller_request, name='seller_request'),
    path('account/edit_seller_info/', views.edit_seller_info, name='edit_seller_info'),
    path('account/ghost_mode/', views.ghost_mode, name='ghost_mode'),
    path('account/seller_faq/', views.faq, name='faq'),
    path('account/redirect_to_ticket_disable_product/', views.redirect_to_ticket_disable_product, name='redirect_to_ticket_disable_product'),
    path('account/redirect_to_ticket_ghost_mode/', views.redirect_to_ticket_ghost_mode, name='redirect_to_ticket_ghost_mode'),
    path('account/redirect_to_ticket_edit_seller_info/', views.redirect_to_ticket_edit_seller_info, name='redirect_to_ticket_edit_seller_info'),
    path('account/seller_tickets/', views.ticket_list, name='ticket_list'),
    path('account/seller_tickets/<int:id>/', views.ticket_detail, name='ticket_detail'),
    path('account/financial/', views.financial, name='financial'),
    path('account/transactions/', views.transactions, name='transactions'),
    path('account/order_charge_list/<int:id>', views.order_charge_list, name='order_charge_list'),
    path('account/order_charge/<int:id>', views.order_charge, name='order_charge'),
    path('validate_product_name/', views.validate_product_name, name='validate_product_name'),
]
