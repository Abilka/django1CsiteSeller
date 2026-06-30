from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from landing.models import LeadRequest, SiteSettings


class LeadAdminHoneypotVisibilityTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin_user = user_model.objects.create_superuser(
            username='admin',
            email='admin@test.ru',
            password='test-pass',
        )
        self.client.force_login(self.admin_user)
        self.changelist_url = reverse('admin:landing_leadrequest_changelist')

        LeadRequest.objects.create(
            name='Реальная заявка',
            phone='+79991234567',
            service=LeadRequest.ServiceCategory.OTHER,
        )
        LeadRequest.objects.create(
            name='Спам-бот',
            phone='+70000000000',
            service=LeadRequest.ServiceCategory.OTHER,
            is_honeypot=True,
        )

    def test_honeypot_leads_hidden_by_default(self):
        response = self.client.get(self.changelist_url)
        self.assertContains(response, 'Реальная заявка')
        self.assertNotContains(response, 'Спам-бот')

    def test_honeypot_leads_visible_when_flag_enabled(self):
        settings = SiteSettings.load()
        settings.show_honeypot_leads = True
        settings.save()

        response = self.client.get(self.changelist_url)
        self.assertContains(response, 'Реальная заявка')
        self.assertContains(response, 'Спам-бот')
