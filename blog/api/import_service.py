import json
import shutil
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from slugify import slugify as make_slug

from blog.models import BlogPost


IMPORT_DIR = Path(settings.MEDIA_ROOT) / 'blog-imports'


def _import_path(import_id: str) -> Path:
    return IMPORT_DIR / import_id


def _meta_path(import_id: str) -> Path:
    return _import_path(import_id) / 'meta.json'


def _chunk_path(import_id: str, index: int) -> Path:
    return _import_path(import_id) / f'{index}.part'


def save_import_chunk(data: dict) -> dict:
    title = data['title'].strip()
    slug = data.get('slug') or make_slug(title, max_length=220)
    if not slug:
        raise ValueError('Не удалось сформировать slug.')

    import_id = slug
    import_dir = _import_path(import_id)
    chunk_index = data['chunk_index']
    chunk_total = data['chunk_total']

    if chunk_index == 0:
        if import_dir.exists():
            shutil.rmtree(import_dir)
        import_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            'title': title,
            'slug': slug,
            'excerpt': data.get('excerpt', ''),
            'meta_title': data.get('meta_title', ''),
            'meta_description': data.get('meta_description', ''),
            'is_published': data.get('is_published', False),
            'published_at': data.get('published_at'),
            'chunk_total': chunk_total,
        }
        _meta_path(import_id).write_text(
            json.dumps(meta, ensure_ascii=False),
            encoding='utf-8',
        )

    if not _meta_path(import_id).is_file():
        raise ValueError('Импорт не начат: сначала отправьте chunk_index=0.')

    meta = json.loads(_meta_path(import_id).read_text(encoding='utf-8'))
    if meta['chunk_total'] != chunk_total:
        raise ValueError('chunk_total не совпадает с первым запросом.')

    _chunk_path(import_id, chunk_index).write_text(data['body_chunk'], encoding='utf-8')

    if chunk_index + 1 < chunk_total:
        return {
            'status': 'chunk_saved',
            'slug': slug,
            'chunk_index': chunk_index,
            'chunk_total': chunk_total,
        }

    body_parts = []
    for index in range(chunk_total):
        part_path = _chunk_path(import_id, index)
        if not part_path.is_file():
            raise ValueError(f'Не хватает части {index}.')
        body_parts.append(part_path.read_text(encoding='utf-8'))

    body = ''.join(body_parts)
    post, created = BlogPost.objects.get_or_create(
        slug=slug,
        defaults={
            'title': meta['title'],
            'body': body,
            'excerpt': meta.get('excerpt', ''),
            'meta_title': meta.get('meta_title', ''),
            'meta_description': meta.get('meta_description', ''),
            'is_published': meta.get('is_published', False),
        },
    )

    if not created:
        post.title = meta['title']
        post.body = body
        post.excerpt = meta.get('excerpt', '')
        post.meta_title = meta.get('meta_title', '')
        post.meta_description = meta.get('meta_description', '')
        post.is_published = meta.get('is_published', False)

    published_at = meta.get('published_at')
    if published_at:
        post.published_at = published_at
    elif post.is_published and not post.published_at:
        post.published_at = timezone.now()

    post.save()
    shutil.rmtree(import_dir, ignore_errors=True)

    return {
        'status': 'completed',
        'created': created,
        'slug': post.slug,
        'id': post.pk,
    }
