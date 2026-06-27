from django.contrib import admin
from django.utils.html import format_html

from .models import BlogPost


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'published_at', 'cover_preview', 'updated_at')
    list_filter = ('is_published', 'published_at')
    list_editable = ('is_published',)
    search_fields = ('title', 'slug', 'excerpt', 'body')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
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

    @admin.display(description='Обложка')
    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html(
                '<img src="{}" style="height:40px;border-radius:6px;" />',
                obj.cover_image.url,
            )
        return '—'
