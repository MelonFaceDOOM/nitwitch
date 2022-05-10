from django.views import generic
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from articles.models import Article
# Create your views here.


# def index(request):
    # simplest home page
    # return render(request, 'index.html')

    # just 1 article for home page
    # article = get_object_or_404(Article, title='Stupid Shapes')
    # return render(request, 'articles/article.html', {'article': article})
    

class IndexView(generic.ListView):
    context_object_name = "latest_articles_list"
    template_name = "articles/index.html"
    paginate_by = 5
    model = Article