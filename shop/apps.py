from django.apps import AppConfig


class ShopConfig(AppConfig):
    name = 'shop'
    verbose_name = 'فروشگاه'

    # def ready(self):
    #     from . import scheduler
    #     scheduler.on_server_reboot_check_jobs()
