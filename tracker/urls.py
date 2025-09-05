from django.urls import path, include
from . import views
from . import views as tracker_views
from .views import SourceDetailView
from config import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from django.contrib.auth.decorators import login_required
from django.contrib import admin
from django.contrib.auth import views as auth_views


urlpatterns = [
    path("login/", auth_views.LoginView.as_view(
        template_name="registration/login.html"
    ), name="login"),
    path("logout/", tracker_views.custom_logout, name="logout"),
    path("register/", tracker_views.register, name="register"),
    
    # Home / dashboard
    
    path("", views.dashboard, name="dashboard"),
    # path("", RedirectView.as_view(pattern_name="dashboard", permanent=False)),
    path("accounts/", include("django.contrib.auth.urls")),
    
    path("admin/", admin.site.urls),
    
    # Threat
    path("themes/all/", views.theme_list_all, name="theme_list_all"),
    path("themes/category/<int:category_id>/", views.theme_list_by_category, name="theme_list_by_category"),
    path("themes/<int:pk>/", views.view_theme, name="view_theme"),
    path("themes/add/", views.add_theme, name="add_theme"),
    path("themes/<int:pk>/edit/", views.ThemeUpdateView.as_view(), name="edit_theme"),
    path("themes/<int:pk>/delete/", views.ThemeDeleteView.as_view(), name="delete_theme"),
    path("themes/", views.theme_list_all, name="theme_list_all"),
    path("themes/<int:pk>/", views.ThemeDetailView.as_view(), name="theme_detail"),


    path("events/add/<int:theme_id>/", views.add_event, name="add_event"),
    path("themes/redirect/add-event/", views.add_event_redirect, name="add_event_redirect"),
    path('themes/toggle/<int:pk>/', views.toggle_theme_active, name='toggle_theme_active'),

    path("events/", views.event_list, name="event_list"),

    path("events/<int:pk>/", views.event_detail, name="event_detail"),           
    path("events/view/<int:event_id>/", views.view_event, name="view_event"),    

    path("events/<int:pk>/edit/", views.edit_event, name="edit_event"),
    
    path("events/<int:pk>/delete/", views.EventDeleteView.as_view(), name="event_delete"),

    path("events/<int:event_pk>/sources/add/", views.add_source, name="add_source"),
    path('events/toggle/<int:pk>/', views.toggle_event_active, name='toggle_event_active'),

    path("sources/redirect/add/", views.add_source_redirect, name="add_source_redirect"),
    path("source/<int:pk>/", views.source_detail, name="source_detail"),
    path("source/<int:pk>/edit/", views.SourceUpdateView.as_view(), name="edit_source"),
    path("source/<int:pk>/delete/", views.SourceDeleteView.as_view(), name="delete_source"),
    path("source/<int:pk>/toggle/", views.toggle_source_active, name="toggle_source_active"),
        
    # AJAX helpers
    path("ajax/themes/", views.get_themes, name="get_themes"),
    path("ajax/events/", views.get_events, name="get_events"),

    # Admin / logs
    path("access-logs/", views.access_logs, name="access_logs"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)