from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views

app_name = 'photoalbums'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('create_photoalbum/', views.create_photoalbum, name='create_photoalbum'),
    path('edit_photoalbum/<int:photoalbum_id>', views.edit_photoalbum, name='edit_photoalbum'),
    path('submit_images/<int:photoalbum_id>', views.submit_images, name='submit_images'),
    path('delete_photoalbum/<int:photoalbum_id>', views.delete_photoalbum, name='delete_photoalbum'),
    path('update_image/<int:image_id>', views.update_image, name='update_image'),
    path('delete_image/<int:image_id>', views.delete_image, name='delete_image'),
    path('ambiguity_vote/', views.ambiguity_vote, name='ambiguity_vote'),
    path('image_comment_ambiguity_vote/', views.image_comment_ambiguity_vote, name='image_comment_ambiguity_vote'),
    path('photoalbum_comment_ambiguity_vote/', views.photoalbum_comment_ambiguity_vote, name='photoalbum_comment_ambiguity_vote'),
    path('submit_photoalbum_comment/<int:photoalbum_id>', views.submit_photoalbum_comment, name='submit_photoalbum_comment'),
    path('submit_image_comment/<int:image_id>', views.submit_image_comment, name='submit_image_comment'),
    path('image/<int:image_id>', views.image, name='image'),
    path('<str:title>/', views.photoalbum, {'album_page': 1}, name='photoalbum'),  # default to page 1
    path('<str:title>/<int:album_page>', views.photoalbum, name='photoalbum'),  # this HAS TO come last, or the <str> tag will match to
                                                          # everything else (i.e. 'write_photoalbum')
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
