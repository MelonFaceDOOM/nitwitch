from django.contrib import admin

from .models import PhotoAlbum, PhotoAlbumImage

admin.site.register(PhotoAlbum)
admin.site.register(PhotoAlbumImage)