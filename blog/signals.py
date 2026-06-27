from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import BlogPost
from .services.indexnow import build_absolute_url, notify_indexnow


def _should_notify(post: BlogPost) -> bool:
    return post.is_published and post.published_at is not None and post.is_visible


@receiver(post_save, sender=BlogPost)
def indexnow_on_post_save(sender, instance, **kwargs):
    if _should_notify(instance):
        notify_indexnow([build_absolute_url(instance.get_absolute_url())])


@receiver(post_delete, sender=BlogPost)
def indexnow_on_post_delete(sender, instance, **kwargs):
    if instance.is_published:
        notify_indexnow([build_absolute_url(instance.get_absolute_url())])
