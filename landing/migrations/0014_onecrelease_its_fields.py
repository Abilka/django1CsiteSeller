from django.db import migrations, models


def seed_its_doc_ids(apps, schema_editor):
    OneCConfiguration = apps.get_model('landing', 'OneCConfiguration')
    mapping = {
        'rel_1c_bp30': 4,
        'rel_1c_zup30': 210,
        'rel_1c_ut11': 284,
    }
    for slug, doc_id in mapping.items():
        OneCConfiguration.objects.filter(slug=slug).update(its_doc_id=doc_id)


class Migration(migrations.Migration):

    dependencies = [
        ('landing', '0013_seed_migration_paths'),
    ]

    operations = [
        migrations.AddField(
            model_name='onecconfiguration',
            name='its_doc_id',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='Идентификатор раздела на its.1c.ru/db/updinfo.',
                null=True,
                verbose_name='ID раздела на ИТС',
            ),
        ),
        migrations.AddField(
            model_name='onecrelease',
            name='its_doc_id',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='Идентификатор страницы «Новое в версии» на its.1c.ru/db/updinfo.',
                null=True,
                verbose_name='ID версии на ИТС',
            ),
        ),
        migrations.AddField(
            model_name='onecrelease',
            name='its_url',
            field=models.URLField(
                blank=True,
                max_length=255,
                verbose_name='Ссылка на описание изменений ИТС',
            ),
        ),
        migrations.RunPython(seed_its_doc_ids, migrations.RunPython.noop),
    ]
