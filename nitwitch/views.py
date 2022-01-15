from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from articles.models import Article
# Create your views here.


def index(request):
    # Render the HTML template index.html
    #return render(request, 'index.html')

    article = get_object_or_404(Article, title='sss')
    return render(request, 'articles/article.html', {'article': article})
