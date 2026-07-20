from django.urls import path
from .views import manage, delete_object, ban_ip, unban_ip, promote_user, demote_user

urlpatterns = [
    path('manage/', manage, name='manage'),
    path('delete_object/', delete_object, name='delete_object'),
    path('ban_ip/', ban_ip, name='ban_ip'),
    path('unban_ip/', unban_ip, name='unban_ip'),
    path('promote_user/', promote_user, name='promote_user'),
    path('demote_user/', demote_user, name='demote_user'),
]