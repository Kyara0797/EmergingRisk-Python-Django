from django.apps import AppConfig


class TrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tracker'

class TrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tracker'
    
    def ready(self):
        if not self.apps.ready:
            from . import signals