import re
from pathlib import Path

from django.core.files.storage import default_storage
from django.db import models

ALLOWED_FAVICON_EXTENSIONS = {'.ico', '.png', '.svg', '.webp', '.gif'}


def favicon_upload_path(instance, filename):
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_FAVICON_EXTENSIONS:
        ext = '.ico'
    return f'favicon/favicon{ext}'


class SiteSettings(models.Model):
    hourly_rate = models.PositiveIntegerField(
        'Стоимость часа работы, ₽',
        default=1500,
        help_text='Используется для расчёта стоимости типовых задач, обновлений и позиций прайс-листа.',
    )
    update_hours_per_release = models.DecimalField(
        'Часов на один релиз обновления',
        max_digits=4,
        decimal_places=2,
        default=0.5,
        help_text='Трудозатраты на установку одного промежуточного обновления в калькуляторе.',
    )
    telegram_contact_url = models.URLField(
        'Ссылка на Telegram',
        blank=True,
        help_text='Например: https://t.me/your_username',
    )
    max_contact_url = models.URLField(
        'Ссылка на MAX',
        blank=True,
        help_text='Ссылка для связи в мессенджере MAX.',
    )
    contact_email = models.EmailField(
        'Email для связи',
        blank=True,
        help_text='Отображается в блоке контактов и в юридических документах.',
    )
    contact_phone = models.CharField(
        'Телефон для связи',
        max_length=30,
        blank=True,
        help_text='Например: +7 (999) 123-45-67',
    )
    telegram_bot_token = models.CharField(
        'Токен Telegram-бота',
        max_length=120,
        blank=True,
        help_text='Получите у @BotFather. Нужен для дублирования заявок.',
    )
    telegram_chat_id = models.CharField(
        'Chat ID для уведомлений',
        max_length=64,
        blank=True,
        help_text='ID чата или группы, куда отправлять заявки (например: -1001234567890).',
    )
    telegram_notify_enabled = models.BooleanField(
        'Дублировать заявки в Telegram',
        default=False,
    )
    show_honeypot_leads = models.BooleanField(
        'Показывать заявки из honeypot в админке',
        default=False,
        help_text='По умолчанию заявки, попавшие в антиспам, скрыты в списке заявок.',
    )
    freesc_auto_sync_enabled = models.BooleanField(
        'Автосинхронизация релизов с ИТС',
        default=True,
        help_text='Периодически загружать релизы с its.1c.ru/db/updinfo в калькулятор.',
    )
    freesc_sync_interval_days = models.PositiveSmallIntegerField(
        'Интервал синхронизации, дней',
        default=3,
    )
    freesc_last_sync_at = models.DateTimeField(
        'Последняя синхронизация релизов',
        null=True,
        blank=True,
    )
    favicon = models.ImageField(
        'Favicon',
        upload_to=favicon_upload_path,
        blank=True,
        help_text='Иконка вкладки браузера. Рекомендуется PNG или ICO, 32×32 или 64×64 px.',
    )

    class Meta:
        verbose_name = 'Настройки сайта'
        verbose_name_plural = 'Настройки сайта'

    def save(self, *args, **kwargs):
        old_rate = None
        old_favicon_name = ''
        if self.pk:
            try:
                row = SiteSettings.objects.values('hourly_rate', 'favicon').get(pk=1)
                old_rate = row['hourly_rate']
                old_favicon_name = row['favicon'] or ''
            except SiteSettings.DoesNotExist:
                pass

        if self.favicon and not self.favicon._committed:
            target_name = favicon_upload_path(self, self.favicon.name)
            if default_storage.exists(target_name):
                default_storage.delete(target_name)

        self.pk = 1
        super().save(*args, **kwargs)

        new_favicon_name = self.favicon.name if self.favicon else ''
        if old_favicon_name and old_favicon_name != new_favicon_name:
            if default_storage.exists(old_favicon_name):
                default_storage.delete(old_favicon_name)

        if old_rate is not None and old_rate != self.hourly_rate:
            PriceListItem.recalculate_all_prices(self.hourly_rate)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'Настройки сайта'

    @property
    def contact_phone_tel(self) -> str:
        if not self.contact_phone:
            return ''
        return re.sub(r'[^\d+]', '', self.contact_phone)

    def estimate_update_price(self, steps_count: int) -> dict:
        hours = self.update_hours_per_release * steps_count
        price = int(hours * self.hourly_rate)
        return {
            'hourly_rate': self.hourly_rate,
            'hours_per_release': self.update_hours_per_release,
            'estimated_hours': hours,
            'estimated_price': price,
        }


class TypicalTask(models.Model):
    title = models.CharField('Название задачи', max_length=200)
    description = models.TextField('Описание', blank=True)
    estimated_hours = models.DecimalField(
        'Оценка, часов',
        max_digits=5,
        decimal_places=1,
    )
    duration = models.CharField('Срок выполнения', max_length=80)
    is_featured = models.BooleanField(
        'Показывать в блоке Hero',
        default=False,
        help_text='Только одна задача рекомендуется для Hero.',
    )
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)
    is_published = models.BooleanField('Опубликовано', default=True)

    class Meta:
        verbose_name = 'Типовая задача'
        verbose_name_plural = 'Типовые задачи'
        ordering = ['sort_order', 'title']

    def __str__(self):
        return self.title

    def estimated_price(self, hourly_rate=None):
        rate = hourly_rate if hourly_rate is not None else SiteSettings.load().hourly_rate
        return int(self.estimated_hours * rate)

    @property
    def price_display(self):
        return self.estimated_price()


class PriceListItem(models.Model):
    class Category(models.TextChoices):
        ADMIN = 'admin', 'Администрирование'
        ACCOUNTING = 'accounting', 'Учёт и ошибки'
        DEVELOPMENT = 'development', 'Разработка'
        INTEGRATION = 'integration', 'Интеграции'

    category = models.CharField(
        'Категория',
        max_length=20,
        choices=Category.choices,
    )
    name = models.CharField('Наименование работы', max_length=250)
    hours_from = models.DecimalField(
        'Часов от',
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        help_text='Минимальная оценка трудозатрат.',
    )
    hours_to = models.DecimalField(
        'Часов до',
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        help_text='Максимальная оценка трудозатрат.',
    )
    price_from = models.PositiveIntegerField(
        'Цена от, ₽',
        null=True,
        blank=True,
        editable=False,
        help_text='Рассчитывается автоматически: часы × ставка за час.',
    )
    price_to = models.PositiveIntegerField(
        'Цена до, ₽',
        null=True,
        blank=True,
        editable=False,
        help_text='Рассчитывается автоматически: часы × ставка за час.',
    )
    note = models.CharField('Примечание', max_length=200, blank=True)
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)
    is_published = models.BooleanField('Опубликовано', default=True)

    class Meta:
        verbose_name = 'Позиция прайса'
        verbose_name_plural = 'Прайс-лист'
        ordering = ['category', 'sort_order', 'name']

    def __str__(self):
        return self.name

    def recalculate_prices(self, hourly_rate=None):
        rate = hourly_rate if hourly_rate is not None else SiteSettings.load().hourly_rate
        self.price_from = int(self.hours_from * rate) if self.hours_from is not None else None
        self.price_to = int(self.hours_to * rate) if self.hours_to is not None else None

    def save(self, *args, **kwargs):
        self.recalculate_prices()
        super().save(*args, **kwargs)

    @classmethod
    def recalculate_all_prices(cls, hourly_rate):
        for item in cls.objects.all():
            item.recalculate_prices(hourly_rate)
            item.save(update_fields=['price_from', 'price_to'])

    @property
    def hours_display(self):
        if self.hours_from is not None and self.hours_to is not None:
            if self.hours_from == self.hours_to:
                return f'{self.hours_from:g} ч'
            return f'{self.hours_from:g} – {self.hours_to:g} ч'
        if self.hours_from is not None:
            return f'от {self.hours_from:g} ч'
        if self.hours_to is not None:
            return f'до {self.hours_to:g} ч'
        return '—'

    def price_display(self, hourly_rate=None):
        if hourly_rate is not None:
            self.recalculate_prices(hourly_rate)
        if self.price_from and self.price_to:
            if self.price_from == self.price_to:
                return f'{self.price_from:,}'.replace(',', '\u2009') + ' ₽'
            return (
                f'{self.price_from:,}'.replace(',', '\u2009')
                + ' – '
                + f'{self.price_to:,}'.replace(',', '\u2009')
                + ' ₽'
            )
        if self.price_from:
            return 'от ' + f'{self.price_from:,}'.replace(',', '\u2009') + ' ₽'
        if self.price_to:
            return 'до ' + f'{self.price_to:,}'.replace(',', '\u2009') + ' ₽'
        return 'по оценке'


class TeamMember(models.Model):
    name = models.CharField('Имя', max_length=120)
    photo = models.ImageField('Фото', upload_to='team/')
    specialization = models.CharField('Специализация', max_length=250)
    bio = models.TextField('Кратко о специалисте', blank=True)
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)
    is_published = models.BooleanField('Опубликовано', default=True)

    class Meta:
        verbose_name = 'Специалист'
        verbose_name_plural = 'Команда'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Certificate(models.Model):
    member = models.ForeignKey(
        TeamMember,
        on_delete=models.CASCADE,
        related_name='certificates',
        verbose_name='Специалист',
    )
    title = models.CharField('Название сертификата', max_length=200)
    image = models.ImageField('Изображение', upload_to='certificates/')
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Сертификат'
        verbose_name_plural = 'Сертификаты'
        ordering = ['sort_order', 'title']

    def __str__(self):
        return f'{self.member.name} — {self.title}'


class LeadRequest(models.Model):
    class ServiceCategory(models.TextChoices):
        ADMIN = 'admin', 'Настройка и администрирование'
        ACCOUNTING = 'accounting', 'Учёт и исправление ошибок'
        DEVELOPMENT = 'development', 'Разработка под ваши задачи'
        INTEGRATION = 'integration', 'Оборудование и интеграции'
        OTHER = 'other', 'Другое / не уверен'

    name = models.CharField('Имя', max_length=120)
    phone = models.CharField('Телефон', max_length=30)
    email = models.EmailField('Email', blank=True)
    company = models.CharField('Компания', max_length=200, blank=True)
    service = models.CharField(
        'Категория услуги',
        max_length=20,
        choices=ServiceCategory.choices,
        default=ServiceCategory.OTHER,
    )
    message = models.TextField('Описание задачи', blank=True)
    created_at = models.DateTimeField('Дата заявки', auto_now_add=True)
    is_processed = models.BooleanField('Обработана', default=False)
    telegram_sent = models.BooleanField('Отправлено в Telegram', default=False)
    is_honeypot = models.BooleanField('Honeypot', default=False, db_index=True)

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} — {self.get_service_display()}'


class OneCConfiguration(models.Model):
    slug = models.SlugField(
        'Код конфигурации',
        max_length=40,
        unique=True,
        help_text='Например: rel_1c_ut11',
    )
    name = models.CharField('Название', max_length=200)
    is_published = models.BooleanField('Показывать в калькуляторе', default=True)
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)
    its_doc_id = models.PositiveIntegerField(
        'ID раздела на ИТС',
        null=True,
        blank=True,
        help_text='Идентификатор раздела на its.1c.ru/db/updinfo.',
    )

    class Meta:
        verbose_name = 'Конфигурация 1С'
        verbose_name_plural = 'Конфигурации 1С'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    @property
    def latest_release(self):
        releases = list(self.releases.all())
        if not releases:
            return None
        from landing.services.version_utils import version_parts

        return max(releases, key=lambda release: version_parts(release.version))


class OneCRelease(models.Model):
    configuration = models.ForeignKey(
        OneCConfiguration,
        on_delete=models.CASCADE,
        related_name='releases',
        verbose_name='Конфигурация',
    )
    version = models.CharField('Номер релиза', max_length=32)
    release_date = models.DateField('Дата выхода', null=True, blank=True)
    from_versions = models.JSONField(
        'Обновление с версий',
        default=list,
        help_text='Список версий, с которых можно обновиться на этот релиз.',
    )
    min_platform = models.CharField(
        'Мин. версия платформы',
        max_length=32,
        blank=True,
        help_text='Например: 8.3.27.1859',
    )
    sort_order = models.PositiveIntegerField(
        'Порядок (меньше = новее)',
        default=0,
        help_text='0 — самый новый релиз в конфигурации.',
    )
    its_doc_id = models.PositiveIntegerField(
        'ID версии на ИТС',
        null=True,
        blank=True,
        help_text='Идентификатор страницы «Новое в версии» на its.1c.ru/db/updinfo.',
    )
    its_url = models.URLField(
        'Ссылка на описание изменений ИТС',
        blank=True,
        max_length=255,
    )

    class Meta:
        verbose_name = 'Релиз 1С'
        verbose_name_plural = 'Релизы 1С'
        ordering = ['sort_order', '-release_date', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['configuration', 'version'],
                name='unique_release_per_configuration',
            ),
        ]

    def __str__(self):
        return f'{self.configuration.slug} — {self.version}'


class MigrationPath(models.Model):
    slug = models.SlugField('Код маршрута', max_length=60, unique=True)
    name = models.CharField('Название миграции', max_length=200)
    source_name = models.CharField('Исходная конфигурация', max_length=200)
    target_name = models.CharField('Целевая конфигурация', max_length=200)
    description = models.TextField('Описание', blank=True)
    base_hours = models.DecimalField(
        'Базовая оценка, часов',
        max_digits=6,
        decimal_places=1,
        default=0,
        help_text='Используется, если этапы не заданы.',
    )
    is_published = models.BooleanField('Опубликовано', default=True)
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Маршрут миграции'
        verbose_name_plural = 'Маршруты миграции'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class MigrationPathStep(models.Model):
    migration_path = models.ForeignKey(
        MigrationPath,
        on_delete=models.CASCADE,
        related_name='steps',
        verbose_name='Маршрут',
    )
    title = models.CharField('Этап', max_length=200)
    description = models.TextField('Описание', blank=True)
    estimated_hours = models.DecimalField('Оценка, часов', max_digits=6, decimal_places=1)
    sort_order = models.PositiveSmallIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Этап миграции'
        verbose_name_plural = 'Этапы миграции'
        ordering = ['sort_order', 'title']

    def __str__(self):
        return f'{self.migration_path.name} — {self.title}'


class ReleaseSyncLog(models.Model):
    class Status(models.TextChoices):
        RUNNING = 'running', 'Выполняется'
        SUCCESS = 'success', 'Успешно'
        PARTIAL = 'partial', 'Частично'
        ERROR = 'error', 'Ошибка'

    class Trigger(models.TextChoices):
        MANUAL = 'manual', 'Вручную'
        SCHEDULER = 'scheduler', 'Планировщик'
        FORCE = 'force', 'Принудительно'

    started_at = models.DateTimeField('Начало', auto_now_add=True)
    finished_at = models.DateTimeField('Окончание', null=True, blank=True)
    status = models.CharField('Статус', max_length=16, choices=Status.choices, default=Status.RUNNING)
    triggered_by = models.CharField('Источник', max_length=16, choices=Trigger.choices, default=Trigger.MANUAL)
    configurations_total = models.PositiveSmallIntegerField('Конфигураций всего', default=0)
    configurations_synced = models.PositiveSmallIntegerField('Конфигураций успешно', default=0)
    configurations_failed = models.PositiveSmallIntegerField('Конфигураций с ошибкой', default=0)
    configs_created = models.PositiveSmallIntegerField('Новых конфигураций', default=0)
    configs_updated = models.PositiveSmallIntegerField('Обновлённых конфигураций', default=0)
    releases_created = models.PositiveIntegerField('Релизов создано', default=0)
    releases_updated = models.PositiveIntegerField('Релизов обновлено', default=0)
    releases_deleted = models.PositiveIntegerField('Релизов удалено', default=0)
    message = models.TextField('Сводка', blank=True)
    error_message = models.TextField('Ошибки', blank=True)

    class Meta:
        verbose_name = 'Лог синхронизации релизов'
        verbose_name_plural = 'Логи синхронизации релизов'
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.started_at:%d.%m.%Y %H:%M} — {self.get_status_display()}'
