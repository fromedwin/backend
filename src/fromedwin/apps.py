from django.apps import AppConfig

class MyAppConfig(AppConfig):
    name = 'fromedwin'
    verbose_name = "FromEdwin Core"

    def ready(self):
        import django_celery_beat.schedulers
