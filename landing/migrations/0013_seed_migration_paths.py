from decimal import Decimal

from django.db import migrations


def seed_migration_paths(apps, schema_editor):
    MigrationPath = apps.get_model('landing', 'MigrationPath')
    MigrationPathStep = apps.get_model('landing', 'MigrationPathStep')

    paths = [
        {
            'slug': 'ut10-to-ut11',
            'name': 'УТ 10.3 → УТ 11',
            'source_name': 'Управление торговлей, ред. 10.3',
            'target_name': 'Управление торговлей, ред. 11',
            'description': 'Переход с линейки УТ 10.3 на актуальную редакцию 11 с переносом данных и настройкой обменов.',
            'sort_order': 10,
            'steps': [
                ('Аудит текущей базы и доработок', 'Инвентаризация отличий от типовой, оценка рисков.', Decimal('8')),
                ('Подготовка эталонной УТ 11', 'Развёртывание целевой конфигурации и настройка учёта.', Decimal('16')),
                ('Перенос справочников и остатков', 'Загрузка НСИ, цен, остатков и взаиморасчётов.', Decimal('24')),
                ('Настройка обменов и интеграций', 'Восстановление обменов с сайтом, CRM, кассами.', Decimal('12')),
                ('Обучение и опытная эксплуатация', 'Пилотный запуск, исправление замечаний.', Decimal('8')),
            ],
        },
        {
            'slug': 'bp2-to-bp3',
            'name': 'БП 2.0 → БП 3.0',
            'source_name': 'Бухгалтерия предприятия, ред. 2.0',
            'target_name': 'Бухгалтерия предприятия, ред. 3.0',
            'description': 'Миграция учёта на БП 3.0 с переносом данных и проверкой отчётности.',
            'sort_order': 20,
            'steps': [
                ('Анализ учётной политики и доработок', 'Сверка регламентированного учёта и отчётов.', Decimal('6')),
                ('Развёртывание БП 3.0', 'Установка конфигурации и базовые настройки.', Decimal('8')),
                ('Перенос данных', 'Загрузка остатков, документов и справочников.', Decimal('16')),
                ('Проверка отчётности', 'Сверка баланса, ОСВ и регламентированных форм.', Decimal('8')),
            ],
        },
        {
            'slug': 'upp-to-erp',
            'name': 'УПП → ERP',
            'source_name': 'Управление производственным предприятием',
            'target_name': '1С:ERP Управление предприятием 2',
            'description': 'Комплексный переход с УПП на ERP с реинжинирингом процессов.',
            'sort_order': 30,
            'steps': [
                ('Обследование процессов', 'Карта процессов и целевая модель в ERP.', Decimal('24')),
                ('Проектирование целевой системы', 'Настройка подсистем ERP под бизнес.', Decimal('40')),
                ('Миграция НСИ и остатков', 'Поэтапный перенос данных.', Decimal('48')),
                ('Пусконаладка и обучение', 'Запуск подразделений, сопровождение.', Decimal('24')),
            ],
        },
    ]

    for path_data in paths:
        steps = path_data.pop('steps')
        path, _ = MigrationPath.objects.update_or_create(
            slug=path_data['slug'],
            defaults={
                **path_data,
                'base_hours': Decimal('0'),
                'is_published': True,
            },
        )
        path.steps.all().delete()
        for index, (title, description, hours) in enumerate(steps):
            MigrationPathStep.objects.create(
                migration_path=path,
                title=title,
                description=description,
                estimated_hours=hours,
                sort_order=index,
            )


def unseed_migration_paths(apps, schema_editor):
    MigrationPath = apps.get_model('landing', 'MigrationPath')
    MigrationPath.objects.filter(
        slug__in=['ut10-to-ut11', 'bp2-to-bp3', 'upp-to-erp'],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('landing', '0012_migration_paths_and_tools'),
    ]

    operations = [
        migrations.RunPython(seed_migration_paths, unseed_migration_paths),
    ]
