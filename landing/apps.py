from django.apps import AppConfig


class LandingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'landing'

    def ready(self):
        import landing.signals  # noqa: F401
        from landing.scheduler import start_freesc_scheduler

        start_freesc_scheduler()
