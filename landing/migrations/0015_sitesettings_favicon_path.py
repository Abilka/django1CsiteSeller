import shutil
from pathlib import Path

import landing.models
from django.conf import settings
from django.db import migrations, models


def migrate_favicon_path(apps, schema_editor):
    SiteSettings = apps.get_model('landing', 'SiteSettings')
    site_settings = SiteSettings.objects.filter(pk=1).first()
    if not site_settings or not site_settings.favicon:
        return

    old_name = str(site_settings.favicon)
    if old_name.startswith('favicon/favicon.'):
        return

    media_root = Path(settings.MEDIA_ROOT)
    old_path = media_root / old_name
    if not old_path.exists():
        return

    ext = old_path.suffix.lower() or '.ico'
    new_dir = media_root / 'favicon'
    new_dir.mkdir(parents=True, exist_ok=True)
    new_path = new_dir / f'favicon{ext}'
    if new_path.exists():
        new_path.unlink()
    shutil.copy2(old_path, new_path)
    old_path.unlink()

    site_settings.favicon = f'favicon/favicon{ext}'
    site_settings.save(update_fields=['favicon'])


class Migration(migrations.Migration):

    dependencies = [
        ('landing', '0014_onecrelease_its_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitesettings',
            name='favicon',
            field=models.ImageField(
                blank=True,
                help_text='Иконка вкладки браузера. Рекомендуется PNG или ICO, 32×32 или 64×64 px.',
                upload_to=landing.models.favicon_upload_path,
                verbose_name='Favicon',
            ),
        ),
        migrations.RunPython(migrate_favicon_path, migrations.RunPython.noop),
    ]
