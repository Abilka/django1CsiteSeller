from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html

from blog.models import BlogPost
from blog.services.indexnow import (
    INDEXNOW_BATCH_SIZE,
    build_indexnow_admin_messages,
    submit_blog_posts,
)
from .models import (
    Certificate,
    LeadRequest,
    OneCConfiguration,
    OneCRelease,
    PriceListItem,
    ReleaseSyncLog,
    SiteSettings,
    TeamMember,
    TypicalTask,
)
from .telegram_notify import send_lead_to_telegram, send_telegram_message


class CertificateInline(admin.TabularInline):
    model = Certificate
    extra = 1
    fields = ('title', 'image', 'sort_order')


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Оформление сайта', {
            'fields': ('favicon', 'favicon_preview'),
            'description': 'Favicon отображается во вкладке браузера на всех страницах сайта.',
        }),
        ('Стоимость', {
            'fields': ('hourly_rate', 'update_hours_per_release'),
            'description': (
                'Ставка за час используется в калькуляторе обновлений и для автоматического '
                'расчёта цен в прайс-листе (часы × ставка). При изменении ставки все позиции '
                'прайса пересчитываются.'
            ),
        }),
        ('Контакты для клиентов', {
            'fields': ('contact_email', 'contact_phone', 'telegram_contact_url', 'max_contact_url'),
        }),
        ('Уведомления о заявках в Telegram', {
            'fields': (
                'telegram_notify_enabled',
                'telegram_bot_token',
                'telegram_chat_id',
                'telegram_test_link',
            ),
            'description': (
                'Создайте бота через @BotFather, добавьте его в чат/группу '
                'и укажите chat_id (можно узнать через @userinfobot или getUpdates API). '
                'Ссылка «Telegram» в блоке контактов — это только кнопка для клиентов, '
                'она не связана с уведомлениями о заявках.'
            ),
        }),
        ('Синхронизация релизов freesc.ru', {
            'fields': (
                'freesc_auto_sync_enabled',
                'freesc_sync_interval_days',
                'freesc_last_sync_at',
            ),
            'description': (
                'Автоматическая загрузка релизов с freesc.ru. '
                'Планировщик включается переменной окружения FREESC_RUN_SCHEDULER=1 '
                '(проверка каждые 6 часов, синхронизация — по интервалу в днях).'
            ),
        }),
        ('IndexNow', {
            'fields': ('indexnow_submit_all_link',),
            'description': (
                f'Принудительная отправка URL опубликованных статей блога в IndexNow '
                f'пачками по {INDEXNOW_BATCH_SIZE}. '
                'Для выборочной отправки отметьте статьи в разделе «Статьи» и выберите '
                f'действие «Отправить выбранные в IndexNow». '
                'Требуются переменные SITE_URL, SITE_HOST и INDEXNOW_KEY.'
            ),
        }),
    )

    readonly_fields = (
        'freesc_last_sync_at',
        'favicon_preview',
        'telegram_test_link',
        'indexnow_submit_all_link',
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'test-telegram/',
                self.admin_site.admin_view(self.test_telegram_view),
                name='landing_sitesettings_test_telegram',
            ),
            path(
                'submit-indexnow/',
                self.admin_site.admin_view(self.submit_indexnow_view),
                name='landing_sitesettings_submit_indexnow',
            ),
        ]
        return custom_urls + urls

    @admin.display(description='Проверка')
    def telegram_test_link(self, obj):
        url = reverse('admin:landing_sitesettings_test_telegram')
        return format_html(
            '<a class="button" href="{}">Отправить тестовое уведомление</a>',
            url,
        )

    def test_telegram_view(self, request):
        ok, error = send_telegram_message(
            '✅ Тестовое уведомление с сайта. Если вы видите это сообщение — настройки верны.',
        )
        if ok:
            messages.success(request, 'Тестовое сообщение отправлено в Telegram.')
        else:
            messages.error(request, f'Не удалось отправить: {error}')
        return redirect('admin:landing_sitesettings_change', 1)

    @admin.display(description='Отправка статей')
    def indexnow_submit_all_link(self, obj):
        url = reverse('admin:landing_sitesettings_submit_indexnow')
        return format_html(
            '<a class="button" href="{}">Отправить все опубликованные статьи в IndexNow</a>',
            url,
        )

    def submit_indexnow_view(self, request):
        posts = list(BlogPost.published.all())
        result = submit_blog_posts(posts)
        for level, text in build_indexnow_admin_messages(result):
            getattr(messages, level)(request, text)
        return redirect('admin:landing_sitesettings_change', 1)

    @admin.display(description='Предпросмотр')
    def favicon_preview(self, obj):
        if obj.favicon:
            return format_html(
                '<img src="{}" style="height:32px;width:32px;object-fit:contain;" />',
                obj.favicon.url,
            )
        return '—'

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TypicalTask)
class TypicalTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'estimated_hours', 'duration', 'is_featured', 'is_published', 'sort_order')
    list_editable = ('is_featured', 'is_published', 'sort_order')
    list_filter = ('is_featured', 'is_published')
    search_fields = ('title', 'description')


@admin.register(PriceListItem)
class PriceListItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'hours_from', 'hours_to', 'price_from', 'price_to', 'is_published', 'sort_order')
    list_editable = ('is_published', 'sort_order')
    list_filter = ('category', 'is_published')
    search_fields = ('name', 'note')
    readonly_fields = ('price_from', 'price_to')
    fieldsets = (
        (None, {
            'fields': ('category', 'name', 'hours_from', 'hours_to', 'price_from', 'price_to', 'note', 'sort_order', 'is_published'),
            'description': (
                'Укажите диапазон часов — цены рассчитаются автоматически по ставке из «Настройки сайта». '
                'При изменении ставки все позиции прайса пересчитаются.'
            ),
        }),
    )


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialization', 'photo_preview', 'is_published', 'sort_order')
    list_editable = ('is_published', 'sort_order')
    list_filter = ('is_published',)
    search_fields = ('name', 'specialization')
    inlines = [CertificateInline]

    @admin.display(description='Фото')
    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="height:40px;border-radius:6px;" />', obj.photo.url)
        return '—'


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('title', 'member', 'sort_order')
    list_filter = ('member',)
    search_fields = ('title', 'member__name')


@admin.register(LeadRequest)
class LeadRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'service', 'created_at', 'is_processed', 'telegram_sent')
    list_filter = ('service', 'is_processed', 'telegram_sent', 'created_at')
    search_fields = ('name', 'phone', 'email', 'message')
    list_editable = ('is_processed',)
    readonly_fields = ('created_at', 'telegram_sent')
    actions = ('resend_to_telegram',)

    @admin.action(description='Повторно отправить в Telegram')
    def resend_to_telegram(self, request, queryset):
        sent = 0
        failed = 0
        for lead in queryset:
            if send_lead_to_telegram(lead):
                LeadRequest.objects.filter(pk=lead.pk).update(telegram_sent=True)
                sent += 1
            else:
                failed += 1
        if sent:
            messages.success(request, f'Отправлено в Telegram: {sent}.')
        if failed:
            messages.error(
                request,
                f'Не удалось отправить: {failed}. Проверьте настройки сайта и колонку «Отправлено в Telegram».',
            )


class OneCReleaseInline(admin.TabularInline):
    model = OneCRelease
    extra = 0
    fields = ('version', 'release_date', 'from_versions', 'min_platform', 'sort_order')
    ordering = ('sort_order',)


@admin.register(OneCConfiguration)
class OneCConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_published', 'sort_order', 'releases_count')
    list_editable = ('is_published', 'sort_order')
    list_filter = ('is_published',)
    search_fields = ('name', 'slug')
    inlines = [OneCReleaseInline]

    @admin.display(description='Релизов')
    def releases_count(self, obj):
        return obj.releases.count()


@admin.register(OneCRelease)
class OneCReleaseAdmin(admin.ModelAdmin):
    list_display = ('version', 'configuration', 'release_date', 'min_platform', 'sort_order')
    list_filter = ('configuration',)
    search_fields = ('version', 'configuration__name', 'configuration__slug')
    list_editable = ('sort_order',)
    autocomplete_fields = ('configuration',)


@admin.register(ReleaseSyncLog)
class ReleaseSyncLogAdmin(admin.ModelAdmin):
    list_display = (
        'started_at',
        'status',
        'triggered_by',
        'configurations_synced',
        'releases_created',
        'releases_updated',
    )
    list_filter = ('status', 'triggered_by', 'started_at')
    readonly_fields = (
        'started_at',
        'finished_at',
        'status',
        'triggered_by',
        'configurations_total',
        'configurations_synced',
        'configurations_failed',
        'configs_created',
        'configs_updated',
        'releases_created',
        'releases_updated',
        'releases_deleted',
        'message',
        'error_message',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
