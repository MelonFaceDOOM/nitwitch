from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views

app_name = 'adventures'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('submit_adventures/', views.submit_adventures, name='submit_adventures'),
    path('get_adventure_titles/', views.get_adventure_titles, name='get_adventure_titles'),
    path('delete_adventure/<int:adventure_id>', views.delete_adventure, name='delete_adventure'),
    path('game_tree/<str:title>', views.game_tree, name='game_tree'),
    path('game_content/<str:title>', views.game_content, name='game_content'),
    path('<str:title>/<str:card_id>', views.adventure_game_card, name='adventure_game_card')  # this HAS TO come last, or the <str> tag will match to
                                                          # everything else (i.e. 'write_adventure')
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
