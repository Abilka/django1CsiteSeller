from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import LeadRequestForm
from .models import (
    MigrationPath,
    OneCConfiguration,
    PriceListItem,
    SiteSettings,
    TeamMember,
    TypicalTask,
)
from .services.update_calculator import UpdatePathError, calculate_update_path
from .tool_context import build_tool_context
from .tools.migration_calc import estimate_migration
from .tools.platform_check import (
    PlatformCheckError,
    PLATFORM_VERSION_CUSTOM,
    check_platform_compatibility,
    get_known_platform_versions,
    resolve_platform_version,
)
from .tools.query_formatter import format_query
from .tools.registry import list_tools
from .tools.release_feed import get_feed_configurations, get_release_feed
from .tools.task_estimator import estimate_tasks


@require_http_methods(['GET', 'POST'])
def index(request):
    settings = SiteSettings.load()

    if request.method == 'POST':
        form = LeadRequestForm(request.POST)
        if form.is_valid():
            if form.is_bot:
                form.save_honeypot()
            else:
                form.save()
            return redirect('landing:thanks')
    else:
        form = LeadRequestForm()

    typical_tasks = TypicalTask.objects.filter(is_published=True)
    featured_task = typical_tasks.filter(is_featured=True).first()
    price_items = PriceListItem.objects.filter(is_published=True)
    team_members = TeamMember.objects.filter(is_published=True).prefetch_related('certificates')

    price_by_category = {}
    for item in price_items:
        price_by_category.setdefault(item.category, []).append(item)

    return render(request, 'landing/index.html', {
        'form': form,
        'settings': settings,
        'typical_tasks': typical_tasks,
        'featured_task': featured_task,
        'price_by_category': price_by_category,
        'price_categories': PriceListItem.Category.choices,
        'team_members': team_members,
    })


def thanks(request):
    return render(request, 'landing/thanks.html')


@require_http_methods(['GET', 'POST'])
def update_calculator(request):
    settings = SiteSettings.load()
    configurations = OneCConfiguration.objects.filter(is_published=True).prefetch_related('releases')

    selected_config = None
    selected_version = ''
    result = None
    error = None
    versions = []

    if request.method == 'POST':
        config_slug = request.POST.get('configuration', '')
        selected_version = request.POST.get('current_version', '').strip()
        selected_config = configurations.filter(slug=config_slug).first()

        if not selected_config:
            error = 'Выберите конфигурацию.'
        elif not selected_version:
            error = 'Выберите текущий релиз.'
        else:
            try:
                result = calculate_update_path(selected_config, selected_version)
            except UpdatePathError as exc:
                error = str(exc)
    else:
        config_slug = request.GET.get('configuration', '')
        if config_slug:
            selected_config = configurations.filter(slug=config_slug).first()

    if selected_config:
        versions = list(
            selected_config.releases.order_by('sort_order', '-release_date', '-id')
            .values_list('version', flat=True)
        )

    return render(request, 'landing/update_calculator.html', {
        'settings': settings,
        'configurations': configurations,
        'selected_config': selected_config,
        'selected_version': selected_version,
        'versions': versions,
        'result': result,
        'error': error,
    })


def release_version_help(request):
    return render(request, 'landing/release_version_help.html')


def user_agreement(request):
    return render(request, 'landing/user_agreement.html')


def privacy_policy(request):
    return render(request, 'landing/privacy_policy.html')


def tools_index(request):
    return render(request, 'landing/tools/index.html', {
        'tools': list_tools(),
    })


@require_http_methods(['GET', 'POST'])
def platform_check(request):
    settings = SiteSettings.load()
    configurations = OneCConfiguration.objects.filter(is_published=True).prefetch_related('releases')
    selected_config = None
    platform_version = ''
    platform_version_custom = ''
    platform_version_select = ''
    platform_versions = get_known_platform_versions()
    target_release = ''
    current_release = ''
    result = None
    error = None
    releases = []

    if request.method == 'POST':
        config_slug = request.POST.get('configuration', '')
        platform_version_select = request.POST.get('platform_version', '').strip()
        platform_version_custom = request.POST.get('platform_version_custom', '').strip()
        platform_version = resolve_platform_version(platform_version_select, platform_version_custom)
        target_release = request.POST.get('target_release', '').strip()
        current_release = request.POST.get('current_release', '').strip()
        selected_config = configurations.filter(slug=config_slug).first()

        if not selected_config:
            error = 'Выберите конфигурацию.'
        elif not platform_version:
            error = 'Укажите версию платформы.'
        else:
            try:
                result = check_platform_compatibility(
                    selected_config,
                    platform_version,
                    target_release or None,
                    current_release or None,
                )
            except PlatformCheckError as exc:
                error = str(exc)
    else:
        config_slug = request.GET.get('configuration', '')
        if config_slug:
            selected_config = configurations.filter(slug=config_slug).first()

    if selected_config:
        releases = list(
            selected_config.releases.order_by('sort_order', '-release_date', '-id')
            .values('version', 'min_platform')
        )

    return render(request, 'landing/tools/platform_check.html', build_tool_context(
        'platform-check',
        settings=settings,
        configurations=configurations,
        selected_config=selected_config,
        platform_version=platform_version,
        platform_version_select=platform_version_select or (
            platform_version if platform_version in platform_versions else PLATFORM_VERSION_CUSTOM
        ),
        platform_version_custom=platform_version_custom or (
            platform_version if platform_version_select == PLATFORM_VERSION_CUSTOM or platform_version not in platform_versions else ''
        ),
        platform_versions=platform_versions,
        target_release=target_release,
        current_release=current_release,
        releases=releases,
        result=result,
        error=error,
    ))


def release_feed(request):
    days = int(request.GET.get('days', '90') or 90)
    config_slug = request.GET.get('configuration', '').strip()
    items = get_release_feed(days=days, configuration_slug=config_slug or None)
    return render(request, 'landing/tools/release_feed.html', build_tool_context(
        'release-feed',
        items=items,
        configurations=get_feed_configurations(),
        selected_days=days,
        selected_config=config_slug,
    ))


@require_http_methods(['GET', 'POST'])
def task_estimator(request):
    settings = SiteSettings.load()
    typical_tasks = TypicalTask.objects.filter(is_published=True)
    price_items = PriceListItem.objects.filter(is_published=True)
    result = None
    selected_typical_ids: list[int] = []
    selected_price_ids: list[int] = []

    if request.method == 'POST':
        selected_typical_ids = [int(pk) for pk in request.POST.getlist('typical_tasks') if pk.isdigit()]
        selected_price_ids = [int(pk) for pk in request.POST.getlist('price_items') if pk.isdigit()]
        if not selected_typical_ids and not selected_price_ids:
            result = None
        else:
            result = estimate_tasks(selected_typical_ids, selected_price_ids)

    price_by_category = {}
    for item in price_items:
        price_by_category.setdefault(item.category, []).append(item)

    return render(request, 'landing/tools/task_estimator.html', build_tool_context(
        'task-estimator',
        settings=settings,
        typical_tasks=typical_tasks,
        price_by_category=price_by_category,
        price_categories=PriceListItem.Category.choices,
        result=result,
        selected_typical_ids=selected_typical_ids,
        selected_price_ids=selected_price_ids,
    ))


@require_http_methods(['GET', 'POST'])
def query_formatter(request):
    source_query = ''
    result = None

    if request.method == 'POST':
        source_query = request.POST.get('query', '')
        result = format_query(source_query)

    return render(request, 'landing/tools/query_formatter.html', build_tool_context(
        'query-formatter',
        source_query=source_query,
        result=result,
    ))


@require_http_methods(['GET', 'POST'])
def migration_calculator(request):
    settings = SiteSettings.load()
    paths = MigrationPath.objects.filter(is_published=True).prefetch_related('steps')
    selected_path = None
    result = None
    error = None

    if request.method == 'POST':
        path_slug = request.POST.get('migration_path', '')
        selected_path = paths.filter(slug=path_slug).first()
        if not selected_path:
            error = 'Выберите маршрут миграции.'
        else:
            result = estimate_migration(selected_path)
    else:
        path_slug = request.GET.get('path', '')
        if path_slug:
            selected_path = paths.filter(slug=path_slug).first()

    return render(request, 'landing/tools/migration_calculator.html', build_tool_context(
        'migration-calc',
        settings=settings,
        paths=paths,
        selected_path=selected_path,
        result=result,
        error=error,
    ))
