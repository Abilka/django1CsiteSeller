from django.core.management.base import BaseCommand

from landing.management.commands.sync_freesc_releases import Command as SyncFreescReleasesCommand


class Command(SyncFreescReleasesCommand):
    help = 'Синхронизация конфигураций и релизов 1С с freesc.ru (алиас sync_freesc_releases).'
