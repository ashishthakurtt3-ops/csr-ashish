from django.apps import AppConfig


class AdminPanelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.admin_panel'
    label = 'admin_panel'
    verbose_name = 'Enterprise Admin & Core Intelligence'

    def ready(self):
        try:
            import modules.admin_panel.signals  # noqa
        except Exception:
            pass
