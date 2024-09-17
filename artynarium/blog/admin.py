from django.contrib import admin
from blog import models
import admin_thumbnails
from django.db.models import Count


###### Post ######
@admin_thumbnails.thumbnail('image')
class ProductImageInline(admin.TabularInline):
    model = models.Images
    readonly_fields = ('id',)
    extra = 0


class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'status',
                    'views', 'comment_count', 'image_tag']
    search_fields = ['title', 'category__title',
                     'author__first_name', 'author__first_name', 'id']
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ['category', 'create_time', 'update_time', 'status']
    inlines = [ProductImageInline]

    def get_queryset(self, request):
        return models.Post.objects.annotate(comment_count=Count('comment'))

    def comment_count(self, obj):
        return obj.comment_count

    comment_count.short_description = 'Comments count'
    comment_count.admin_order_field = 'comment_count'


admin.site.register(models.Post, PostAdmin)
###### End Post ######


###### Comment ######
class CommentAdmin(admin.ModelAdmin):
    list_display = ['post', 'name', 'status', 'agree', 'ip', 'create_at']
    list_filter = ['status', 'create_at']
    search_fields = ['post__title', 'name', 'comment', 'email', 'ip']
    readonly_fields = ('ip', 'name', 'email', 'post',)


admin.site.register(models.Comment, CommentAdmin)
###### End Comment ######


###### Category ######
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
    list_display = ['title', 'status']
    search_fields = ['id', 'post__title']
    list_filter = ['status', 'create_at']


admin.site.register(models.Category, CategoryAdmin)
###### End Category ######


###### Images ######
class ImagesAdmin(admin.ModelAdmin):
    search_fields = ['id', 'title']
    list_display = ['__str__', 'id']


# admin.site.register(models.Images, ImagesAdmin)
###### End Images ######
