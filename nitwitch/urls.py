from django.conf import settings
from django.conf.urls.static import static

"""index URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from nitwitch import views

urlpatterns = [
    # path('', views.index, name='index'),
    path('', views.IndexView.as_view(), name='index'),
    path('articles/', include('articles.urls')),
    path('polls/', include('polls.urls')),
    path('scheduling/', include('scheduling.urls')),
    #path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),  # this is the login/signup stuff
    path('admin-controls/', include('accounts.urls')),  # this is "manage"
    path('photoalbums/', include('photoalbums.urls')),
    path('adventures/', include('adventures.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
