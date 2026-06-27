from django.db import models
from django.urls import reverse
from django.utils import timezone


class PublishedPostManager(models.Manager):
    def get_queryset(self):
        now = timezone.now()
        return super().get_queryset().filter(
            is_published=True,
            published_at__isnull=False,
            published_at__lte=now,
        )


class BlogPost(models.Model):
    title = models.CharField('Заголовок', max_length=200)
    slug = models.SlugField('URL', max_length=220, unique=True)
    excerpt = models.TextField(
        'Краткое описание',
        blank=True,
        help_text='Отображается в списке статей и в meta description, если не задано отдельно.',
    )
    body = models.TextField('Текст статьи')
    cover_image = models.ImageField('Обложка', upload_to='blog/', blank=True)
    meta_title = models.CharField('SEO title', max_length=70, blank=True)
    meta_description = models.CharField('SEO description', max_length=160, blank=True)
    is_published = models.BooleanField('Опубликовано', default=False)
    published_at = models.DateTimeField('Дата публикации', null=True, blank=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    objects = models.Manager()
    published = PublishedPostManager()

    class Meta:
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'
        ordering = ('-published_at', '-created_at')

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog:detail', kwargs={'slug': self.slug})

    @property
    def seo_title(self):
        return self.meta_title or self.title

    @property
    def seo_description(self):
        if self.meta_description:
            return self.meta_description
        if self.excerpt:
            return self.excerpt[:160]
        return self.body[:160].replace('\n', ' ')

    @property
    def is_visible(self):
        if not self.is_published or not self.published_at:
            return False
        return self.published_at <= timezone.now()

    def save(self, *args, **kwargs):
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
