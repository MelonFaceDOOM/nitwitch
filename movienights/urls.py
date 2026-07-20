from django.urls import path
from . import views

app_name = 'movienights'
urlpatterns = [
    path('', views.guild_index, name='index'),
    path('oauth/discord/start/', views.discord_oauth_start, name='discord_oauth_start'),
    path('oauth/discord/callback/', views.discord_oauth_callback, name='discord_oauth_callback'),
    path('viewer/clear/', views.clear_viewer_view, name='clear_viewer'),

    path('<int:guild_id>/', views.guild_hub, name='guild_hub'),
    path('<int:guild_id>/movies/', views.movie_list, name='movie_list'),
    path('<int:guild_id>/movie/<int:movie_id>/', views.movie_detail, name='movie_detail'),
    path(
        '<int:guild_id>/movie/<int:movie_id>/edit/',
        views.movie_edit,
        name='movie_edit',
    ),
    path(
        '<int:guild_id>/movie/<int:movie_id>/review/edit/',
        views.movie_review_edit,
        name='movie_review_edit',
    ),

    # Write actions (bot-parity)
    path('<int:guild_id>/suggest/', views.movie_suggest, name='movie_suggest'),
    path('<int:guild_id>/remove/', views.movie_remove, name='movie_remove'),
    path('<int:guild_id>/movie/<int:movie_id>/endorse/', views.movie_endorse, name='movie_endorse'),
    path('<int:guild_id>/movie/<int:movie_id>/unendorse/', views.movie_unendorse, name='movie_unendorse'),
    path('<int:guild_id>/movie/<int:movie_id>/review/', views.movie_review, name='movie_review'),
    path('<int:guild_id>/movie/<int:movie_id>/rate/', views.movie_rate, name='movie_rate'),
    path('<int:guild_id>/movie/<int:movie_id>/rename/', views.movie_rename, name='movie_rename'),
    path('<int:guild_id>/movie/<int:movie_id>/transfer/', views.movie_transfer, name='movie_transfer'),
    path(
        '<int:guild_id>/movie/<int:movie_id>/date-watched/',
        views.movie_change_date_watched,
        name='movie_change_date_watched',
    ),

    # Temporary JSON verify endpoints for query helpers
    path('<int:guild_id>/api/<slug:kind>/', views.api_list, name='api_list'),
]
