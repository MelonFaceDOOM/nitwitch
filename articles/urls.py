from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views

app_name = 'articles'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('create_article/', views.create_article, name='create_article'),
    path('edit_article/<int:article_id>', views.edit_article, name='edit_article'),
    path('submit_images/<int:article_id>', views.submit_images, name='submit_images'),
    path('delete_article/<int:article_id>', views.delete_article, name='delete_article'),
    path('<str:title>/', views.article, name='article'),  # this HAS TO come last, or the <str> tag will match to
                                                          # everything else (i.e. 'write_article')
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
