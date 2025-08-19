from django.contrib import admin
from django.http import HttpResponse
from django.urls import path

urlpatterns = [
    path("ping/", lambda r: HttpResponse("pong")),   # debe devolver "pong"
    path("admin/", admin.site.urls),
]

print("URLS LOADED:", [str(p.pattern) for p in urlpatterns])  # 🔊 evidencia en Deploy Logs



# # config/urls.py (VERSIÓN MINIMAL Y DEFINITIVA)
# from django.contrib import admin
# from django.http import HttpResponse
# from django.urls import path
# from tracker.views import oneoff_diagnose_admin  

# urlpatterns = [
#     path("ping/", lambda r: HttpResponse("pong")),      
#     path("admin/", admin.site.urls),
       
# ]


# """
# URL configuration for config project.

# The `urlpatterns` list routes URLs to views. For more information please see:
#     https://docs.djangoproject.com/en/5.2/topics/http/urls/
# Examples:
# Function views
#     1. Add an import:  from my_app import views
#     2. Add a URL to urlpatterns:  path('', views.home, name='home')
# Class-based views
#     1. Add an import:  from other_app.views import Home
#     2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
# Including another URLconf
#     1. Import the include() function: from django.urls import include, path
#     2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
# """
# from django.contrib import admin
# from tracker.views import oneoff_autologin_admin, oneoff_diagnose_admin, oneoff_reset_superuser
# from django.urls import path, include
# from django.contrib.auth import views as auth_views
# from config import settings
# from tracker import views as tracker_views
# from django.conf.urls.static import static
# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path("oneoff-reset/", oneoff_reset_superuser),     
#     path("oneoff-autologin/", oneoff_autologin_admin),
#     path("oneoff-diagnose/", oneoff_diagnose_admin),
    
#     path('', include('tracker.urls')),
#     path('register/', tracker_views.register, name='register'),
#     path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
#     path('logout/', auth_views.LogoutView.as_view(), name='logout'),
#     path('admin/access-logs/', tracker_views.access_logs, name='access_logs'),
# ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
