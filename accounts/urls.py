from django.urls import path
from .views import manage, delete_object, ban_ip, unban_ip

urlpatterns = [
    path('manage/', manage, name='manage'),
    path('delete_object/', delete_object, name='delete_object'),
    path('ban_ip/', ban_ip, name='ban_ip'),
    path('unban_ip/', unban_ip, name='unban_ip'),
]