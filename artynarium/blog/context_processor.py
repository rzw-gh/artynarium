from . import models
from taggit.models import Tag


def side(request):
    cate = models.Category.objects.all()
    pop = models.Post.objects.order_by('-views')[:6]
    tag = models.Post.tags.most_common()[:10]
    context = {
        'cate': cate,
        'pop': pop,
        'tag': tag,
    }
    return context
