import time
from unittest.mock import patch

from django.test import TestCase

from django.core.signing import Signer

from landing.antispam import JS_TOKEN
from landing.antispam import SIGNER_SALT
from landing.antispam import is_bot_submission
from landing.forms import LeadRequestForm
from landing.models import LeadRequest

_signer = Signer(salt=SIGNER_SALT)


class LeadFormAntispamTests(TestCase):
    def _valid_payload(self, issued_at: int | None = None, **overrides):
        if issued_at is None:
            issued_at = int(time.time())
        payload = {
            'contact_name': 'Иван Петров',
            'phone': '+7 (999) 123-45-67',
            'email': 'ivan@example.com',
            'service': 'other',
            'message': 'Нужна помощь с 1С',
            'form_ts': _signer.sign(str(issued_at)),
            'js_ok': JS_TOKEN,
            'company_website': '',
            'fax_number': '',
        }
        payload.update(overrides)
        return payload, issued_at

    def test_valid_submission_is_not_bot(self):
        payload, issued_at = self._valid_payload()
        with patch('landing.antispam.time.time', return_value=issued_at + 5):
            form = LeadRequestForm(payload)
            self.assertTrue(form.is_valid())
            self.assertFalse(form.is_bot)

    def test_honeypot_marks_submission_as_bot(self):
        payload, issued_at = self._valid_payload(company_website='https://spam.test')
        with patch('landing.antispam.time.time', return_value=issued_at + 5):
            form = LeadRequestForm(payload)
            self.assertTrue(form.is_valid())
            self.assertTrue(form.is_bot)

    def test_missing_js_token_marks_submission_as_bot(self):
        payload, issued_at = self._valid_payload(js_ok='')
        with patch('landing.antispam.time.time', return_value=issued_at + 5):
            form = LeadRequestForm(payload)
            self.assertTrue(form.is_valid())
            self.assertTrue(form.is_bot)

    def test_too_fast_submission_marks_as_bot(self):
        payload, issued_at = self._valid_payload()
        with patch('landing.antispam.time.time', return_value=issued_at + 1):
            form = LeadRequestForm(payload)
            self.assertTrue(form.is_valid())
            self.assertTrue(form.is_bot)

    def test_invalid_timestamp_marks_submission_as_bot(self):
        payload, _issued_at = self._valid_payload(form_ts='broken-token')
        form = LeadRequestForm(payload)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.is_bot)

    def test_bot_submission_is_not_saved_by_view_logic(self):
        payload, issued_at = self._valid_payload(fax_number='+7 000')
        with patch('landing.antispam.time.time', return_value=issued_at + 5):
            form = LeadRequestForm(payload)
            self.assertTrue(form.is_valid())
            self.assertTrue(form.is_bot)
        self.assertEqual(LeadRequest.objects.count(), 0)

    def test_real_submission_is_saved(self):
        payload, issued_at = self._valid_payload()
        with patch('landing.antispam.time.time', return_value=issued_at + 5):
            form = LeadRequestForm(payload)
            self.assertTrue(form.is_valid())
            self.assertFalse(form.is_bot)
            lead = form.save()
        self.assertEqual(LeadRequest.objects.count(), 1)
        self.assertEqual(lead.name, 'Иван Петров')


class AntispamHelperTests(TestCase):
    def test_is_bot_submission_detects_honeypot(self):
        issued_at = int(time.time())
        data = {
            'company_website': 'spam',
            'js_ok': JS_TOKEN,
            'form_ts': _signer.sign(str(issued_at)),
        }
        with patch('landing.antispam.time.time', return_value=issued_at + 5):
            self.assertTrue(is_bot_submission(data.get))
