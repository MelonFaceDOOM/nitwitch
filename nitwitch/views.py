from itertools import chain
from operator import attrgetter
from django.views import generic
from articles.models import Article
from photoalbums.models import PhotoAlbum


# def index(request):
    # simplest home page
    # return render(request, 'index.html')

    # just 1 article for home page
    # article = get_object_or_404(Article, title='Stupid Shapes')
    # return render(request, 'articles/article.html', {'article': article})
    

class IndexView(generic.ListView):
    context_object_name = "recent_publications"
    template_name = "index.html"

    def get_queryset(self):
        articles = Article.objects.all()
        photoalbums = PhotoAlbum.objects.all()
        combined_list = list(chain(articles, photoalbums))
        combined_list.sort(key=attrgetter('pub_date'), reverse=True)
        recent_publications = combined_list[:10]
        return recent_publications

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['background_grid_class'] = 'background-grid'
        return context