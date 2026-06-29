from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from blog.models import BlogPost


class BlogPostAPITests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username='blog_api_staff',
            password='test-pass',
            is_staff=True,
        )
        self.token = Token.objects.create(user=self.staff)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_create_update_and_public_read(self):
        response = self.client.post(
            '/api/v1/blog/posts/',
            {
                'title': 'API test post',
                'slug': 'api-test-post',
                'body': '# Hello',
                'is_published': True,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['slug'], 'api-test-post')

        response = self.client.patch(
            '/api/v1/blog/posts/api-test-post/',
            {'excerpt': 'Updated excerpt'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['excerpt'], 'Updated excerpt')

        self.client.credentials()
        response = self.client.get('/api/v1/blog/posts/api-test-post/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_cannot_create(self):
        self.client.credentials()
        response = self.client.post(
            '/api/v1/blog/posts/',
            {'title': 'Blocked', 'slug': 'blocked', 'body': 'x'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def tearDown(self):
        BlogPost.objects.filter(slug__in=('api-test-post', 'blocked')).delete()
