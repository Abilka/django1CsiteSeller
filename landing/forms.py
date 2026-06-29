import re

from django import forms

from .antispam import issue_form_timestamp
from .antispam import is_bot_submission
from .models import LeadRequest


class LeadRequestForm(forms.ModelForm):
    contact_name = forms.CharField(
        label='Имя',
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Как к вам обращаться?',
            'autocomplete': 'name',
        }),
    )
    company_website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'tabindex': '-1',
        }),
    )
    fax_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'tabindex': '-1',
        }),
    )
    form_ts = forms.CharField(required=False, widget=forms.HiddenInput())
    js_ok = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = LeadRequest
        fields = ['phone', 'email', 'service', 'message']
        widgets = {
            'phone': forms.TextInput(attrs={
                'placeholder': '+7 (___) ___-__-__',
                'autocomplete': 'tel',
                'inputmode': 'tel',
                'data-phone-mask': 'true',
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'email@company.ru',
                'autocomplete': 'email',
            }),
            'service': forms.Select(),
            'message': forms.Textarea(attrs={
                'placeholder': 'Кратко опишите задачу: конфигурация, симптомы, сроки...',
                'rows': 4,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_bot = False
        self.fields['company_website'].label = 'Сайт компании'
        self.fields['fax_number'].label = 'Факс'
        self.fields['phone'].label = 'Телефон'
        self.fields['email'].label = 'Email'
        self.fields['service'].label = 'Категория услуги'
        self.fields['message'].label = 'Описание задачи'
        if not self.is_bound:
            self.initial.setdefault('form_ts', issue_form_timestamp())
            self.initial.setdefault('phone', '+7 ')
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def is_valid(self):
        if self.is_bound and is_bot_submission(
            lambda name: self.data.get(self.add_prefix(name), '')
        ):
            self.is_bot = True
            self.cleaned_data = {}
            self._errors = {}
            return True
        return super().is_valid()

    def clean(self):
        cleaned_data = super().clean()
        contact_name = cleaned_data.get('contact_name', '').strip()
        if not contact_name:
            self.add_error('contact_name', 'Обязательное поле.')
        else:
            cleaned_data['contact_name'] = contact_name
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.name = self.cleaned_data['contact_name']
        if commit:
            instance.save()
        return instance

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        digits = re.sub(r'\D', '', phone)
        if digits.startswith('8') and len(digits) == 11:
            digits = '7' + digits[1:]
        if not digits.startswith('7'):
            digits = '7' + digits.lstrip('0')
        if len(digits) < 11:
            raise forms.ValidationError('Введите полный номер телефона.')
        return f'+{digits}'
