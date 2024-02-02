"""diplom URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
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
from django.urls import path, include

from rest_framework import routers

from backend.views import *

router = routers.SimpleRouter()
router.register(r'user', UserViewSet)


urlpatterns = [
    path("admin/", admin.site.urls),
    path('partner/update', PartnerUpdate.as_view()),
    path('user/register', RegisterUser.as_view()),
    path('api/v1/', include(router.urls)),
    path('user/register/confirm', Сonfirmation.as_view()),
    path('user/login', LoginUser.as_view()),
]
