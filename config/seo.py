"""Helpers for structured data (schema.org JSON-LD)."""


def organization_schema(
    site_name: str,
    url: str = '',
    email: str = '',
    phone: str = '',
    logo_url: str = '',
) -> dict:
    schema = {
        '@context': 'https://schema.org',
        '@type': 'Organization',
        'name': site_name,
    }
    if url:
        schema['url'] = url
    if logo_url:
        schema['logo'] = logo_url

    contact_points = []
    if email:
        contact_points.append({
            '@type': 'ContactPoint',
            'email': email,
            'contactType': 'customer service',
            'availableLanguage': 'Russian',
        })
    if phone:
        contact_points.append({
            '@type': 'ContactPoint',
            'telephone': phone,
            'contactType': 'customer service',
            'availableLanguage': 'Russian',
        })
    if contact_points:
        schema['contactPoint'] = contact_points

    return schema


def website_schema(site_name: str, url: str = '') -> dict:
    schema = {
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        'name': site_name,
        'inLanguage': 'ru-RU',
    }
    if url:
        schema['url'] = url
    return schema


def professional_service_schema(
    site_name: str,
    description: str,
    url: str = '',
    email: str = '',
    phone: str = '',
    price_range: str = '',
) -> dict:
    schema = {
        '@context': 'https://schema.org',
        '@type': 'ProfessionalService',
        'name': site_name,
        'description': description,
        'areaServed': {
            '@type': 'Country',
            'name': 'RU',
        },
        'serviceType': [
            'Настройка 1С',
            'Доработка 1С',
            'Интеграция 1С',
            'Обновление 1С',
        ],
    }
    if url:
        schema['url'] = url
    if email:
        schema['email'] = email
    if phone:
        schema['telephone'] = phone
    if price_range:
        schema['priceRange'] = price_range
    return schema


def webpage_schema(name: str, description: str, url: str = '') -> dict:
    schema = {
        '@context': 'https://schema.org',
        '@type': 'WebPage',
        'name': name,
        'description': description,
        'inLanguage': 'ru-RU',
    }
    if url:
        schema['url'] = url
    return schema


def collection_page_schema(name: str, description: str, url: str = '') -> dict:
    schema = {
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        'name': name,
        'description': description,
        'inLanguage': 'ru-RU',
    }
    if url:
        schema['url'] = url
    return schema


def software_application_schema(name: str, description: str, url: str = '') -> dict:
    schema = {
        '@context': 'https://schema.org',
        '@type': 'SoftwareApplication',
        'name': name,
        'description': description,
        'applicationCategory': 'BusinessApplication',
        'operatingSystem': 'Web',
        'offers': {
            '@type': 'Offer',
            'price': '0',
            'priceCurrency': 'RUB',
        },
    }
    if url:
        schema['url'] = url
    return schema


def blog_posting_schema(
    *,
    headline: str,
    description: str,
    date_published: str,
    date_modified: str,
    site_name: str,
    page_url: str = '',
    image_url: str = '',
) -> dict:
    schema = {
        '@context': 'https://schema.org',
        '@type': 'BlogPosting',
        'headline': headline,
        'description': description,
        'datePublished': date_published,
        'dateModified': date_modified,
        'author': {
            '@type': 'Organization',
            'name': site_name,
        },
        'publisher': {
            '@type': 'Organization',
            'name': site_name,
        },
        'inLanguage': 'ru-RU',
    }
    if page_url:
        schema['mainEntityOfPage'] = {
            '@type': 'WebPage',
            '@id': page_url,
        }
    if image_url:
        schema['image'] = image_url
    return schema


def breadcrumb_schema(items: list[tuple[str, str]]) -> dict:
    return {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        'itemListElement': [
            {
                '@type': 'ListItem',
                'position': index,
                'name': name,
                'item': url,
            }
            for index, (name, url) in enumerate(items, start=1)
        ],
    }
