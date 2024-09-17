from django.urls import path

from . import views

app_name = 'blog'
urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Post
    path('post/<int:id>/<slug:slug>/', views.post, name='post'),
    path('addcomment/<int:id>', views.addcomment, name='addcomment'),
    path('comment_upvote/<int:id>', views.comment_upvote, name='comment_upvote'),

    # Category
    path('category/<int:id>/<slug:slug>/', views.category, name='category'),

    # Tag
    path('tag/<slug:slug>/', views.tagged, name="tagged"),

    # Search
    path('search/', views.search, name='search'),
]
