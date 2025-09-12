from django.urls import path
from . import views


from tracker import views_downloads


urlpatterns = [
    
    # path("admin/", admin.site.urls),
    # path("", include("tracker.urls")),
    # path("login/", auth_views.LoginView.as_view(
    #     template_name="registration/login.html",
    #     authentication_form=EmailOrUsernameAuthenticationForm
    # ), name="login"),
    # path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    
    # Home / dashboard
    
    path("", views.dashboard, name="dashboard"),
    
    
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
    path("f/<uuid:token>/", views_downloads.secure_file_download, name="secure_file_download"),
    

    # AJAX helpers
    path("ajax/themes/", views.get_themes, name="get_themes"),
    path("ajax/events/", views.get_events, name="get_events"),

    # Admin / logs
    path("access-logs/", views.access_logs, name="access_logs"),
]

