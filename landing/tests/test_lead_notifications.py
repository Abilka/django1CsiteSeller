from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from landing.models import LeadRequest, SiteSettings


class LeadPollApiTests(TestCase):
    def setUp(self):
        SiteSettings.load()
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(
            username='staff',
            password='secret',
            is_staff=True,
        )
        self.client = APIClient()
        self.url = reverse('lead-poll')

        self.lead1 = LeadRequest.objects.create(
            name='Иван',
            phone='+79991234567',
            service=LeadRequest.ServiceCategory.ADMIN,
            message='Нужна настройка',
        )
        self.lead2 = LeadRequest.objects.create(
            name='Мария',
            phone='+79997654321',
            service=LeadRequest.ServiceCategory.OTHER,
        )
        LeadRequest.objects.create(
            name='Спам',
            phone='+70000000000',
            service=LeadRequest.ServiceCategory.OTHER,
            is_honeypot=True,
        )

    def test_requires_staff(self):
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_baseline_without_after_id(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['latest_id'], self.lead2.pk)
        self.assertEqual(response.data['leads'], [])

    def test_returns_new_leads_after_id(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(self.url, {'after_id': self.lead1.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['leads']), 1)
        lead = response.data['leads'][0]
        self.assertEqual(lead['id'], self.lead2.pk)
        self.assertEqual(lead['name'], 'Мария')
        self.assertIn('/admin/landing/leadrequest/', lead['admin_url'])

    def test_honeypot_excluded_from_poll(self):
        self.client.force_authenticate(user=self.staff)
        honeypot = LeadRequest.objects.filter(is_honeypot=True).first()
        response = self.client.get(self.url, {'after_id': honeypot.pk - 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in response.data['leads']}
        self.assertNotIn(honeypot.pk, returned_ids)

    def test_invalid_after_id(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(self.url, {'after_id': 'bad'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AdminLeadNotificationsScriptTests(TestCase):
    def setUp(self):
        SiteSettings.load()
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username='admin',
            email='admin@test.ru',
            password='test-pass',
        )
        self.client = APIClient()
        self.client.force_login(self.admin)

    def test_admin_includes_notification_script(self):
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'admin-lead-notifications.js')
        self.assertContains(response, reverse('lead-poll'))
