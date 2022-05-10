from .models import Article, ArticleImage
from .forms import ArticleImageForm
from django.views import generic
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import get_object_or_404, render
from django.forms import modelformset_factory


class IndexView(generic.ListView):
    context_object_name = "latest_articles_list"
    template_name = "articles/index.html"
    paginate_by = 5
    model = Article


def article(request, title):
    article = get_object_or_404(Article, title=title)
    article.view_count += 1
    article.save()
    return render(request, 'articles/article.html', {'article': article})


def create_article(request):
    article = Article.create_placeholder()
    return HttpResponseRedirect(reverse('articles:edit_article', args=(article.id,)))


def edit_article(request, article_id):
    article = get_object_or_404(Article, pk=article_id)
    if request.method == 'POST':
        try:
            title = request.POST['title']
            author = request.POST['author']
            article_text = request.POST['article-text']
        except KeyError:
            return HttpResponseRedirect(reverse('articles:edit_article', args=(article.id,)))

        article.title = title
        article.author = author
        article.article_text = article_text
        article.save()
        article.apply_markup()
        return HttpResponseRedirect(reverse('articles:article', args=(article.title,)))
    else:
        return render(request, 'articles/edit_article.html', {'article': article})


def submit_images(request, article_id):
    article = get_object_or_404(Article, pk=article_id)
    images = request.FILES.getlist("images")
    for image in images:
        article_image = ArticleImage(article=article, image=image)
        article_image.save()
    return HttpResponseRedirect(reverse('articles:edit_article', args=(article.id,)))


def delete_article(request, article_id):
    article = get_object_or_404(Article, pk=article_id)
    article.delete()
    return HttpResponseRedirect(reverse('articles:index'))
