from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import LeadRequestForm
from .models import OneCConfiguration, PriceListItem, SiteSettings, TeamMember, TypicalTask
from .services.update_calculator import UpdatePathError, calculate_update_path


@require_http_methods(['GET', 'POST'])
def index(request):
    settings = SiteSettings.load()

    if request.method == 'POST':
        form = LeadRequestForm(request.POST)
        if form.is_valid():
            if not form.is_bot:
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
