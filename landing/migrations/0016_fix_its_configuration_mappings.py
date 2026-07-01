from django.db import migrations


def fix_its_configuration_mappings(apps, schema_editor):
    OneCConfiguration = apps.get_model('landing', 'OneCConfiguration')

    its_configs = {
        'rel_1c_bp30': {
            'name': '1С:Бухгалтерия 8',
            'its_doc_id': 4,
            'is_published': True,
            'sort_order': 3,
        },
        'rel_1c_bp30b': {
            'name': '1С:Бухгалтерия 8 (базовая)',
            'its_doc_id': 4,
            'is_published': True,
            'sort_order': 4,
        },
        'rel_1c_zup30': {
            'name': '1С:Зарплата и Управление Персоналом, ред. 3',
            'its_doc_id': 210,
            'is_published': True,
            'sort_order': 6,
        },
        'rel_1c_ut11': {
            'name': '1С:Управление торговлей 11',
            'its_doc_id': 284,
            'is_published': True,
            'sort_order': 8,
        },
    }
    for slug, fields in its_configs.items():
        OneCConfiguration.objects.filter(slug=slug).update(**fields)

    OneCConfiguration.objects.filter(
        slug__in=[
            'rel_1c_bp20',
            'rel_1c_bp20b',
            'rel_1c_zup25',
            'rel_1c_ut10',
            'rel_1c_zkh20',
            'rel_1c_zkh30',
        ],
    ).update(is_published=False)


class Migration(migrations.Migration):

    dependencies = [
        ('landing', '0015_sitesettings_favicon_path'),
    ]

    operations = [
        migrations.RunPython(fix_its_configuration_mappings, migrations.RunPython.noop),
    ]
