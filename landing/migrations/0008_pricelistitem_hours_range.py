from decimal import Decimal

from django.db import migrations, models


def migrate_price_list_hours(apps, schema_editor):
    PriceListItem = apps.get_model('landing', 'PriceListItem')
    SiteSettings = apps.get_model('landing', 'SiteSettings')
    settings = SiteSettings.objects.first()
    rate = settings.hourly_rate if settings else 1500

    for item in PriceListItem.objects.all():
        if item.price_from:
            item.hours_from = Decimal(item.price_from) / rate
        elif item.estimated_hours is not None:
            item.hours_from = item.estimated_hours

        if item.price_to:
            item.hours_to = Decimal(item.price_to) / rate
        elif item.estimated_hours is not None:
            item.hours_to = item.estimated_hours

        if item.hours_from is not None:
            item.price_from = int(item.hours_from * rate)
        if item.hours_to is not None:
            item.price_to = int(item.hours_to * rate)

        item.save(update_fields=['hours_from', 'hours_to', 'price_from', 'price_to'])


class Migration(migrations.Migration):

    dependencies = [
        ('landing', '0007_releasesynclog_sitesettings_freesc_auto_sync_enabled_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pricelistitem',
            name='hours_from',
            field=models.DecimalField(
                blank=True,
                decimal_places=1,
                help_text='Минимальная оценка трудозатрат.',
                max_digits=5,
                null=True,
                verbose_name='Часов от',
            ),
        ),
        migrations.AddField(
            model_name='pricelistitem',
            name='hours_to',
            field=models.DecimalField(
                blank=True,
                decimal_places=1,
                help_text='Максимальная оценка трудозатрат.',
                max_digits=5,
                null=True,
                verbose_name='Часов до',
            ),
        ),
        migrations.RunPython(migrate_price_list_hours, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='pricelistitem',
            name='estimated_hours',
        ),
        migrations.AlterField(
            model_name='pricelistitem',
            name='price_from',
            field=models.PositiveIntegerField(
                blank=True,
                editable=False,
                help_text='Рассчитывается автоматически: часы × ставка за час.',
                null=True,
                verbose_name='Цена от, ₽',
            ),
        ),
        migrations.AlterField(
            model_name='pricelistitem',
            name='price_to',
            field=models.PositiveIntegerField(
                blank=True,
                editable=False,
                help_text='Рассчитывается автоматически: часы × ставка за час.',
                null=True,
                verbose_name='Цена до, ₽',
            ),
        ),
        migrations.AlterField(
            model_name='sitesettings',
            name='hourly_rate',
            field=models.PositiveIntegerField(
                default=1500,
                help_text='Используется для расчёта стоимости типовых задач, обновлений и позиций прайс-листа.',
                verbose_name='Стоимость часа работы, ₽',
            ),
        ),
    ]
