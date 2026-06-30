from django.contrib import admin, messages

from .models import BlogPost
from .services.indexnow import (
    INDEXNOW_BATCH_SIZE,
    build_indexnow_admin_messages,
    submit_blog_posts,
)


def _report_indexnow_result(request, result, *, skipped: int = 0):
    for level, text in build_indexnow_admin_messages(result, skipped=skipped):
        getattr(messages, level)(request, text)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'published_at', 'cover_preview', 'updated_at')
    list_filter = ('is_published', 'published_at')
    list_editable = ('is_published',)
    search_fields = ('title', 'slug', 'excerpt', 'body')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
    actions = ('submit_selected_to_indexnow',)
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'excerpt', 'body', 'cover_image'),
        }),
        ('Публикация', {
            'fields': ('is_published', 'published_at'),
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',),
        }),
    )

    @admin.action(description=f'Отправить выбранные в IndexNow (пачками по {INDEXNOW_BATCH_SIZE})')
    def submit_selected_to_indexnow(self, request, queryset):
        publishable = [post for post in queryset if post.is_visible]
        skipped = queryset.count() - len(publishable)
        result = submit_blog_posts(publishable)
        _report_indexnow_result(request, result, skipped=skipped)

    @admin.display(description='Обложка')
    def cover_preview(self, obj):
        from django.utils.html import format_html

        if obj.cover_image:
            return format_html(
                '<img src="{}" style="height:40px;border-radius:6px;" />',
                obj.cover_image.url,
            )
        return '—'
