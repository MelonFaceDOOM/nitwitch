from django.urls import path

from . import views

app_name = 'scheduling'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('<int:pk>/', views.EventView.as_view(), name='event'),
    path('create_event/', views.create_event, name='create_event'),
    path('submit_event/', views.submit_event, name='submit_event'),
    path('delete_event/', views.delete_event, name='delete_event'),
    path('participant/<int:pk>/', views.ParticipantView.as_view(), name='participant'),
    path('delete_participant/', views.delete_participant, name='delete_participant'),
    path('<int:event_id>/add_participant', views.add_participant, name='add_participant'),
    path('delete_suggested_time', views.delete_suggested_time, name='delete_suggested_time'),
    path('participant/<int:participant_id>/add_suggested_time', views.add_suggested_time, name='add_suggested_time')
]
