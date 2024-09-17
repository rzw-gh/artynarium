from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from shop.views import error404

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('allauth.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('', include('shop.urls')),
    path('', include('seller.urls')),
    path('artynarium_admin/', include('artynarium_admin.urls')),
    # path('blog/', include('blog.urls')),
    path('', include('users.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)

handler404 = error404

admin.site.site_header = "مدیریت آرتیناریوم"
admin.site.site_title = "مدیریت آرتیناریوم"
admin.site.index_title = "مدیریت آرتیناریوم"
