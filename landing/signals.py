from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import LeadRequest
from .telegram_notify import send_lead_to_telegram


@receiver(post_save, sender=LeadRequest)
def notify_telegram_on_lead(sender, instance, created, **kwargs):
    if not created or instance.telegram_sent or instance.is_honeypot:
        return
    if send_lead_to_telegram(instance):
        LeadRequest.objects.filter(pk=instance.pk).update(telegram_sent=True)
