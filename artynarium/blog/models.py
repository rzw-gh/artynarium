from django.db import models
from django import forms
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from ckeditor_uploader.fields import RichTextUploadingField
from taggit.managers import TaggableManager
# User
from django.conf import settings
User = settings.AUTH_USER_MODEL

from PIL import Image


###### Category ######
class Category(models.Model):
    STATUS = (
        ('True', 'نمایش'),
        ('False', 'مخفی'),
    )
    title = models.CharField(max_length=50, verbose_name='عنوان')
    status = models.CharField(max_length=10, choices=STATUS, verbose_name='وضعیت')
    slug = models.SlugField(null=False, unique=True, verbose_name='اسلاگ')
    create_at = models.DateTimeField(auto_now_add = True, verbose_name='زمان ساخت')
    
    def __str__(self):
        return self.title

    class Meta:
        ordering = ('-create_at',)
        verbose_name = 'دسته بندی'
        verbose_name_plural = 'دسته بندی ها'
###### End Category ######



###### Post ######
class Post(models.Model):
    STATUS = (
        ('a', 'نمایش'),
        ('ua', 'مخفی'),
    )
    category = models.ForeignKey(Category, on_delete = models.CASCADE, related_name='pos', verbose_name='دسته بندی')
    author = models.ForeignKey(User, on_delete = models.CASCADE, verbose_name='نویسنده')
    title = models.CharField(max_length = 100, verbose_name='عنوان')
    image = models.ImageField(upload_to ='image/blog/post/%Y/%m/%d', verbose_name='تصویر', help_text='از تصویری در سایز 1200 در 1200 استفاده کنید')
    slug = models.SlugField(null = False, unique = True, verbose_name='اسلاگ')
    views = models.IntegerField(default=0, editable = False, verbose_name='بازدید')
    status = models.CharField(max_length=2, choices = STATUS, verbose_name='وضعیت')
    create_time = models.DateTimeField(auto_now_add = True)
    update_time = models.DateTimeField(auto_now = True)
    short_description = models.CharField(max_length = 300, verbose_name='توضیح مختصر')
    description = RichTextUploadingField(verbose_name='محتوا')
    related_post = models.ManyToManyField('self', blank = True, related_name = "related_post", verbose_name = 'پست های مشابه')
    tags = TaggableManager(verbose_name='برچسب')

    class Meta:
        ordering = ('-create_time',)
        verbose_name = 'پست'
        verbose_name_plural = 'پست ها'

    def __str__(self):
        return self.title

    def image_tag(self):
        if self.image.url is not None:
            return mark_safe('<img src="{}" height="50"/>'.format(self.image.url))
        else:
            return ""
    
    def save(self, *args, **kwargs): 
        super().save(*args, **kwargs) 

        img = Image.open(self.image.path) 
        if img.height > 1200 or img.width > 1200: 
            output_size = (1200, 1200) 
            img.thumbnail(output_size) 
            img.save(self.image.path)
    

class Images(models.Model):
    post = models.ForeignKey(Post, on_delete = models.CASCADE, verbose_name='پست')
    image = models.ImageField(blank = True, upload_to = 'image/product/%Y/%m/%d', verbose_name='تصویر')

    def __str__(self):
        return self.post.title
    
    class Meta:
        verbose_name_plural = 'گالری'

    def save(self, *args, **kwargs): 
        super().save(*args, **kwargs) 

        img = Image.open(self.image.path) 
        if img.height > 1200 or img.width > 1200: 
            output_size = (1200, 1200) 
            img.thumbnail(output_size) 
            img.save(self.image.path) 


class Comment(models.Model):
    STATUS = (
        ('Allowed', 'نمایش'),
        ('Unallowed', 'مخفی'),
    )
    post = models.ForeignKey(Post, on_delete = models.CASCADE, related_name = 'comment', verbose_name='پست')
    name = models.CharField(max_length = 250, verbose_name='نام')
    email = models.EmailField(max_length = 250, verbose_name='ایمیل')
    comment = models.TextField(max_length = 400, null = False, unique = True, verbose_name='نظر')
    agree = models.PositiveIntegerField(default = 0, verbose_name='لایک')
    ip = models.CharField(max_length = 20, blank = True, verbose_name='آدرس ای پی')
    status = models.CharField(max_length = 23,choices=STATUS, default = 'Unallowed', verbose_name='وضعیت')
    create_at = models.DateTimeField(auto_now_add = True, verbose_name='زمان ساخت')

    def __str__(self):
        return self.post.title

    class Meta:
        ordering = ('-create_at',)
        verbose_name = 'نظر'
        verbose_name_plural = 'نظرات'
    

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['comment', 'name', 'email']
###### End Post ######



###### SearchForm ######
class SearchForm(forms.Form):
    query = forms.CharField(max_length=100)
###### End SearchForm ######
