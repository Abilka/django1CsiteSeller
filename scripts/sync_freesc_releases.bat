@echo off
cd /d "%~dp0.."
python manage.py sync_freesc_releases --all --sync-configs --force --prune
