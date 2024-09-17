from django.shortcuts import render, HttpResponseRedirect, redirect, get_object_or_404
from django.http import JsonResponse
from . import models
from django.contrib import messages
from django.core.paginator import Paginator
from taggit.models import Tag


def home(request):
    post = models.Post.objects.order_by('-create_time')
    paginator = Paginator(post, 1)
    page = request.GET.get('page')
    post = paginator.get_page(page)
    return render(request, 'blog/home.html', {'post': post})


def post(request, id, slug):
    post = models.Post.objects.get(pk=id)
    post.views += 1
    post.save()
    images = models.Images.objects.filter(post_id=id)
    comment = models.Comment.objects.filter(
        post_id=id, status='Allowed').order_by('-create_at')
    next_post = models.Post.objects.filter(
        id__gt=post.id).order_by('id').first()
    prev_post = models.Post.objects.filter(
        id__lt=post.id).order_by('id').first()
    context = {
        'post': post,
        'images': images,
        'comment': comment,
        'next_post': next_post,
        'prev_post': prev_post,
    }
    return render(request, 'blog/post.html', context)


def category(request, id, slug):
    posts = models.Post.objects.filter(category_id=id)
    return render(request, 'blog/category.html', {'postss': posts})


def tagged(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    common_tags = models.Post.tags.most_common()[:10]
    posts = models.Post.objects.filter(tags=tag)
    context = {
        'tag': tag,
        'common_tags': common_tags,
        'posts': posts,
    }
    return render(request, 'blog/tag.html', context)


def addcomment(request, id):
    url = request.META.get('HTTP_REFERER')  # get last url
    if request.method == 'POST':
        form = models.CommentForm(request.POST)
        if form.is_valid():
            data = models.Comment()
            data.name = form.cleaned_data['name']
            data.email = form.cleaned_data['email']
            data.comment = form.cleaned_data['comment']
            data.ip = request.META.get('REMOTE_ADDR')  # user ip
            data.post_id = id
            data.save()
            messages.success(request, "با تشکر. نظر شما با موفقیت ارسال شد")
            return HttpResponseRedirect(url)
        else:
            messages.warning(request, form.errors)
            return redirect(url)
    return HttpResponseRedirect(url)


def comment_upvote(request, id):
    url = request.META.get('HTTP_REFERER')
    data = models.Comment.objects.get(pk=id)
    data.agree += 1
    data.save()
    if request.is_ajax:
        json_data = {
            'agreeCount': data.agree
        }
        return JsonResponse(json_data)
    return HttpResponseRedirect(url)


def search(request):
    if request.method == 'POST':
        form = models.SearchForm(request.POST)
        if form.is_valid():
            query = form.cleaned_data['query']
            posts = models.Post.objects.filter(title__icontains=query)
            count = posts.count()
            context = {
                'posts': posts,
                'count': count,
                'query': query,
            }
            return render(request, 'blog/search.html', context)
    return HttpResponseRedirect('/')
