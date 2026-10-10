"""
URL configuration for NOVA project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.urls import path , include 
from .views import * 

urlpatterns = [
    path('', home_page , name='home_page'),
    path('Stream/', include('Streamer.urls')),
    path('admin/', admin.site.urls),
    path('login/',login_page , name='login_page'),
    path('logout/', logout_page , name = 'logout_page'),
    path('register/',register_page , name='register_page' ) ,
    path('demo/' , demo, name='demo') ,
    path('user_guide/',user_guide , name='user_guide'),
    
]
