from django.contrib import admin as dj_admin
from django.urls import path
from . import views
from .views import EventDetailView, ThemeDetailView
from tracker.views import oneoff_reset_superuser 


urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Themes
    path('themes/', views.theme_list_all, name='theme_list'),
    path('themes/add/', views.add_theme, name='add_theme'),

    # Lista por categoría (dejamos alias por compatibilidad)
    path('themes/category/<int:category_id>/', views.theme_list_by_category, name='theme_list_by_category'),
    path('themes/category/<int:category_id>/', views.theme_list_by_category, name='view_theme_list'),

    # Detalle de theme (dos nombres apuntando al mismo view)
    path('themes/<int:pk>/', ThemeDetailView.as_view(), name='theme_detail'),
    path('themes/<int:pk>/', ThemeDetailView.as_view(), name='view_theme'),

    path('themes/<int:pk>/edit/', views.ThemeUpdateView.as_view(), name='edit_theme'),
    path('themes/<int:pk>/delete/', views.ThemeDeleteView.as_view(), name='delete_theme'),

    # Events
    path('events/<int:pk>/', EventDetailView.as_view(), name='event_detail'),

# Compatibilidad: detalle con event_id (tu vista funcional)
    path('events/<int:event_id>/', views.view_event, name='view_event'),
    path('events/', views.event_list, name='event_list'),

    # Crear (redir inteligente) y crear con theme
    path('events/add/', views.add_event_redirect, name='add_event_redirect'),
    path('themes/<int:theme_pk>/events/add/', views.edit_event, name='add_event'),

    # Detalle de evento (CBV primero; damos alias 'view_event' al mismo patrón)
    path('events/<int:pk>/', EventDetailView.as_view(), name='event_detail'),
    # path('events/<int:pk>/', EventDetailView.as_view(), name='view_event'),

    path('events/<int:pk>/edit/', views.edit_event, name='edit_event'),
    path('events/<int:pk>/delete/', views.EventDeleteView.as_view(), name='delete_event'),

    # Sources
    path('sources/add/', views.add_source_redirect, name='add_source_global'),
    path('events/<int:event_pk>/sources/add/', views.add_source, name='add_source'),
    path('sources/<int:pk>/edit/', views.SourceUpdateView.as_view(), name='edit_source'),
    path('sources/<int:pk>/delete/', views.SourceDeleteView.as_view(), name='delete_source'),
    path('sources/<int:pk>/edit/', views.SourceUpdateView.as_view(), name='update_source'),
    path('sources/<int:pk>/edit/', views.SourceUpdateView.as_view(), name='edit_source'),
    path('sources/<int:pk>/', views.source_detail, name='source_detail'),
    path('sources/<int:pk>/toggle/', views.toggle_source_active, name='toggle_source'),
    path('sources/<int:pk>/toggle-active/', views.toggle_source_active, name='toggle_source_active'),
    
    path("admin/", dj_admin.site.urls), 
    path('oneoff-reset/', oneoff_reset_superuser),

    # API
    path('api/themes/', views.get_themes, name='get_themes'),
    path('api/events/', views.get_events, name='get_events'),
]
