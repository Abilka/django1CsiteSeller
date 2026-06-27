from django.db import migrations


CONFIGURATIONS = [
    ('rel_1c_bp20', 'Бухгалтерия предприятия 2.0', 1),
    ('rel_1c_bp20b', 'Бухгалтерия предприятия базовая 2.0', 2),
    ('rel_1c_bp30', 'Бухгалтерия предприятия 3.0', 3),
    ('rel_1c_bp30b', 'Бухгалтерия предприятия базовая 3.0', 4),
    ('rel_1c_zup25', 'Зарплата и Управление Персоналом, ред. 2.5', 5),
    ('rel_1c_zup30', 'Зарплата и Управление Персоналом, ред. 3', 6),
    ('rel_1c_ut10', 'Управление торговлей, ред. 10', 7),
    ('rel_1c_ut11', 'Управление торговлей, ред. 11', 8),
    ('rel_1c_zkh20', 'Учет в управляющих компаниях ЖКХ, ТСЖ базовая, ред. 2.0', 9),
    ('rel_1c_zkh30', 'Учет в управляющих компаниях ЖКХ, ТСЖ базовая, ред. 3.0', 10),
]

UT11_DEMO_RELEASES = [
    ('11.5.27.52', 0, ['11.5.22.186', '11.5.27.50'], '8.3.27.1859'),
    ('11.5.27.50', 1, ['11.5.22.186'], '8.3.27.1859'),
    ('11.5.22.186', 2, ['11.5.17.234'], '8.3.27.1559'),
    ('11.5.17.234', 3, ['11.5.12.270'], '8.3.27.1559'),
    ('11.5.12.270', 4, ['11.5.12.251', '11.5.12.256'], '8.3.27.1559'),
    ('11.5.12.251', 5, [], ''),
]


def seed_configurations(apps, schema_editor):
    OneCConfiguration = apps.get_model('landing', 'OneCConfiguration')
    OneCRelease = apps.get_model('landing', 'OneCRelease')

    for slug, name, sort_order in CONFIGURATIONS:
        OneCConfiguration.objects.get_or_create(
            slug=slug,
            defaults={'name': name, 'sort_order': sort_order, 'is_published': True},
        )

    ut11 = OneCConfiguration.objects.filter(slug='rel_1c_ut11').first()
    if ut11 and not OneCRelease.objects.filter(configuration=ut11).exists():
        for version, sort_order, from_versions, platform in UT11_DEMO_RELEASES:
            OneCRelease.objects.create(
                configuration=ut11,
                version=version,
                from_versions=from_versions,
                min_platform=platform,
                sort_order=sort_order,
            )


def unseed_configurations(apps, schema_editor):
    OneCConfiguration = apps.get_model('landing', 'OneCConfiguration')
    OneCConfiguration.objects.filter(slug__in=[item[0] for item in CONFIGURATIONS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('landing', '0004_onecconfiguration_onecrelease'),
    ]

    operations = [
        migrations.RunPython(seed_configurations, unseed_configurations),
    ]
