from django.urls import path
from . import sms_views, views, order_views

app_name = 'artynarium_admin'
urlpatterns = [
    path('', views.home, name='home'),

    # SMS
    path('sms/customer_sms/', sms_views.customer_sms_manager, name='customer_sms_manager'),
    path('sms/customer_sms/<int:id>', sms_views.customer_sms_manager_detail, name='customer_sms_detail'),
    path('sms/seller_sms/', sms_views.seller_sms_manager, name='seller_sms_manager'),
    path('sms/seller_sms/<int:id>', sms_views.seller_sms_manager_detail, name='seller_sms_detail'),
    path('sms/seller_request_sms/', sms_views.seller_request_sms_manager, name='seller_request_sms_manager'),
    path('sms/seller_request_sms/<int:id>', sms_views.seller_request_sms_manager_detail, name='seller_request_sms_manager_detail'),

    # Orders
    path('orders/', order_views.orders, name='orders'),
    path('order/<int:id>', order_views.order_detail, name='order_detail'),
]
