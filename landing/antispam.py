import time

from django.core.signing import BadSignature, Signer

SIGNER_SALT = 'landing.lead-form.v1'
MIN_SUBMIT_SECONDS = 3
MAX_SUBMIT_SECONDS = 7200
JS_TOKEN = 'ok'

_signer = Signer(salt=SIGNER_SALT)

HONEYPOT_FIELDS = ('company_website', 'fax_number')
ANTISPAM_FIELDS = ('form_ts', 'js_ok')


def issue_form_timestamp() -> str:
    return _signer.sign(str(int(time.time())))


def is_bot_submission(get_field) -> bool:
    def get(name: str) -> str:
        return (get_field(name) or '').strip()

    for field in HONEYPOT_FIELDS:
        if get(field):
            return True

    if get('js_ok') != JS_TOKEN:
        return True

    token = get('form_ts')
    if not token:
        return True

    try:
        issued_at = int(_signer.unsign(token))
    except (BadSignature, ValueError):
        return True

    elapsed = time.time() - issued_at
    if elapsed < MIN_SUBMIT_SECONDS or elapsed > MAX_SUBMIT_SECONDS:
        return True

    return False
