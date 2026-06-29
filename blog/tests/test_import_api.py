import re
from pathlib import Path

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from blog.api.import_service import save_import_chunk
from blog.models import BlogPost


class BlogPostImportAPITests(APITestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.staff = User.objects.create_user(
            username='blog_import_staff',
            password='test-pass',
            is_staff=True,
        )
        self.token = Token.objects.create(user=self.staff)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        text = Path('article_test/0020-avtomatizaciya-na-baze-1s-c37a729b.md').read_text(encoding='utf-8')
        match = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n', text, re.DOTALL)
        self.body = text[match.end():].lstrip('\r\n')
        self.meta = {
            'title': 'Импорт chunked test',
            'slug': 'import-chunked-test',
            'excerpt': 'Кратко',
            'meta_description': 'Описание',
            'is_published': False,
        }

    def _chunk_text(self, text: str, max_bytes: int = 1200) -> list[str]:
        chunks = []
        current = []
        current_size = 0
        for char in text:
            char_size = len(char.encode('utf-8'))
            if current and current_size + char_size > max_bytes:
                chunks.append(''.join(current))
                current = [char]
                current_size = char_size
            else:
                current.append(char)
                current_size += char_size
        if current:
            chunks.append(''.join(current))
        return chunks

    def test_chunked_import_creates_post(self):
        chunks = self._chunk_text(self.body)
        last_response = None
        for index, chunk in enumerate(chunks):
            payload = {
                **self.meta,
                'chunk_index': index,
                'chunk_total': len(chunks),
                'body_chunk': chunk,
            }
            last_response = self.client.post('/api/v1/blog/import/', payload, format='json')
            if index + 1 < len(chunks):
                self.assertEqual(last_response.status_code, status.HTTP_202_ACCEPTED)
            else:
                self.assertEqual(last_response.status_code, status.HTTP_201_CREATED)

        post = BlogPost.objects.get(slug='import-chunked-test')
        self.assertEqual(post.body, self.body)
        self.assertGreater(len(chunks), 1)

    def test_chunked_import_service(self):
        chunks = self._chunk_text(self.body)
        for index, chunk in enumerate(chunks):
            save_import_chunk({
                **self.meta,
                'chunk_index': index,
                'chunk_total': len(chunks),
                'body_chunk': chunk,
            })

        post = BlogPost.objects.get(slug='import-chunked-test')
        self.assertEqual(post.body, self.body)

    def tearDown(self):
        BlogPost.objects.filter(slug='import-chunked-test').delete()
