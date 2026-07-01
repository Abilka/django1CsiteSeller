import markdown
from django.conf import settings
from django.contrib.syndication.views import Feed

from blog.models import BlogPost
from blog.templatetags.blog_extras import MARKDOWN_EXTENSIONS
from config.feed_utils import absolute_url, image_mime_type

BLOG_FEED_LIMIT = 50


class BlogPostFeed(Feed):
    title = f'Блог о 1С — {settings.SITE_NAME}'
    link = '/blog/'
    description = 'Статьи, инструкции и советы по настройке, доработке и обновлению 1С:Предприятие 8.'

    def items(self):
        return list(BlogPost.published.all()[:BLOG_FEED_LIMIT])

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        if item.excerpt:
            return f'<p>{item.excerpt}</p>'
        return markdown.markdown(item.body, extensions=MARKDOWN_EXTENSIONS)

    def item_link(self, item):
        return absolute_url(item.get_absolute_url())

    def item_pubdate(self, item):
        return item.published_at

    def item_updateddate(self, item):
        return item.updated_at

    def item_enclosure_url(self, item):
        if item.cover_image:
            return absolute_url(item.cover_image.url)
        return None

    def item_enclosure_mime_type(self, item):
        if item.cover_image:
            return image_mime_type(item.cover_image.name)
        return None
