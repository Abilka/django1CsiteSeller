from decimal import Decimal

from django.db import migrations


def seed_content(apps, schema_editor):
    SiteSettings = apps.get_model('landing', 'SiteSettings')
    TypicalTask = apps.get_model('landing', 'TypicalTask')
    PriceListItem = apps.get_model('landing', 'PriceListItem')

    SiteSettings.objects.get_or_create(
        pk=1,
        defaults={'hourly_rate': 1500},
    )

    if not TypicalTask.objects.exists():
        TypicalTask.objects.bulk_create([
            TypicalTask(
                title='Обновление УТ 11',
                description='Обновление типовой конфигурации, проверка нетиповых доработок, тестирование.',
                estimated_hours=Decimal('6'),
                duration='2–3 дня',
                is_featured=True,
                sort_order=1,
            ),
            TypicalTask(
                title='Помощь в закрытии месяца',
                description='Поиск причин блокировки закрытия, исправление регистров и проводок.',
                estimated_hours=Decimal('4'),
                duration='1–2 дня',
                sort_order=2,
            ),
            TypicalTask(
                title='Устранение дублей контрагентов',
                description='Поиск и объединение дублей номенклатуры или контрагентов без потери данных.',
                estimated_hours=Decimal('3'),
                duration='1 день',
                sort_order=3,
            ),
            TypicalTask(
                title='Интеграция с Ozon',
                description='Настройка обмена заказами и остатками между 1С и маркетплейсом.',
                estimated_hours=Decimal('16'),
                duration='5–7 дней',
                sort_order=4,
            ),
            TypicalTask(
                title='Перенос базы в 1С:Fresh',
                description='Выгрузка, перенос в облако, настройка пользователей и веб-доступа.',
                estimated_hours=Decimal('10'),
                duration='3–5 дней',
                sort_order=5,
            ),
            TypicalTask(
                title='Оптимизация тормозящей базы',
                description='Анализ индексов, запросов и настроек СУБД для ускорения работы.',
                estimated_hours=Decimal('8'),
                duration='2–4 дня',
                sort_order=6,
            ),
        ])

    if not PriceListItem.objects.exists():
        PriceListItem.objects.bulk_create([
            PriceListItem(category='admin', name='Установка типовой конфигурации', price_from=6000, price_to=12000, estimated_hours=Decimal('4'), sort_order=1),
            PriceListItem(category='admin', name='Обновление типовой конфигурации', price_from=3000, price_to=6000, estimated_hours=Decimal('2'), sort_order=2),
            PriceListItem(category='admin', name='Публикация базы на веб-сервере (Apache/IIS)', price_from=9000, price_to=15000, estimated_hours=Decimal('6'), sort_order=3),
            PriceListItem(category='admin', name='Перенос базы в облако (1С:Fresh / 1С:ГРМ)', price_from=12000, price_to=20000, estimated_hours=Decimal('10'), sort_order=4),
            PriceListItem(category='admin', name='Настройка резервного копирования', price_from=4500, price_to=7500, estimated_hours=Decimal('3'), sort_order=5),
            PriceListItem(category='accounting', name='Поиск и устранение дублей', price_from=4500, price_to=9000, estimated_hours=Decimal('3'), sort_order=1),
            PriceListItem(category='accounting', name='Свёртка информационной базы', price_from=15000, price_to=30000, estimated_hours=Decimal('12'), note='Зависит от объёма данных', sort_order=2),
            PriceListItem(category='accounting', name='Закрытие месяца (диагностика и исправление)', price_from=6000, price_to=12000, estimated_hours=Decimal('4'), sort_order=3),
            PriceListItem(category='accounting', name='Исправление ошибки в конфигурации', price_from=1500, price_to=4500, estimated_hours=Decimal('1'), note='Минимум 1 час', sort_order=4),
            PriceListItem(category='development', name='Разработка внешнего отчёта', price_from=9000, price_to=18000, estimated_hours=Decimal('6'), sort_order=1),
            PriceListItem(category='development', name='Разработка обработки / расширения', price_from=7500, price_to=22500, estimated_hours=Decimal('5'), sort_order=2),
            PriceListItem(category='development', name='Доработка печатной формы', price_from=3000, price_to=7500, estimated_hours=Decimal('2'), sort_order=3),
            PriceListItem(category='development', name='Настройка обмена между базами', price_from=12000, price_to=24000, estimated_hours=Decimal('8'), sort_order=4),
            PriceListItem(category='integration', name='Подключение ККМ / сканера штрихкодов', price_from=4500, price_to=9000, estimated_hours=Decimal('3'), sort_order=1),
            PriceListItem(category='integration', name='Настройка «Честный ЗНАК»', price_from=9000, price_to=18000, estimated_hours=Decimal('6'), sort_order=2),
            PriceListItem(category='integration', name='Интеграция с Wildberries / Ozon', price_from=18000, price_to=36000, estimated_hours=Decimal('16'), sort_order=3),
            PriceListItem(category='integration', name='Интеграция с iiko', price_from=15000, price_to=30000, estimated_hours=Decimal('12'), sort_order=4),
        ])


def unseed_content(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('landing', '0002_pricelistitem_sitesettings_teammember_typicaltask_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_content, unseed_content),
    ]
