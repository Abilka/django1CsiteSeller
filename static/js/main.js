(function () {
    const burger = document.getElementById('burger');
    const nav = document.getElementById('nav');

    if (burger && nav) {
        burger.addEventListener('click', function () {
            const isOpen = nav.classList.toggle('is-open');
            burger.classList.toggle('is-active', isOpen);
            burger.setAttribute('aria-expanded', isOpen);
        });

        nav.querySelectorAll('.nav__link').forEach(function (link) {
            link.addEventListener('click', function () {
                nav.classList.remove('is-open');
                burger.classList.remove('is-active');
                burger.setAttribute('aria-expanded', 'false');
            });
        });
    }

    document.querySelectorAll('.service-card__link[data-service]').forEach(function (link) {
        link.addEventListener('click', function () {
            const service = link.dataset.service;
            const select = document.querySelector('#id_service');
            if (select && service) {
                select.value = service;
            }
        });
    });

    const header = document.querySelector('.header');
    if (header) {
        window.addEventListener('scroll', function () {
            header.style.boxShadow = window.scrollY > 20
                ? '0 4px 24px rgba(0,0,0,0.3)'
                : 'none';
        }, { passive: true });
    }

    document.querySelectorAll('a[href="#top"]').forEach(function (link) {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            window.scrollTo({ top: 0, behavior: 'smooth' });
            if (window.location.hash) {
                history.replaceState(null, '', window.location.pathname + window.location.search);
            }
        });
    });

    initPhoneMask();
    initLeadFormAntispam();
})();

function initLeadFormAntispam() {
    const form = document.getElementById('lead-form');
    if (!form) {
        return;
    }
    const jsField = form.querySelector('[name="_js_ok"]');
    if (jsField) {
        jsField.value = 'ok';
    }
}

function initPhoneMask() {
    const input = document.querySelector('[data-phone-mask]');
    if (!input) return;

    const PREFIX = '+7 ';

    function getDigits(value) {
        let digits = value.replace(/\D/g, '');
        if (digits.startsWith('8')) {
            digits = '7' + digits.slice(1);
        }
        if (digits && !digits.startsWith('7')) {
            digits = '7' + digits;
        }
        return digits.slice(0, 11);
    }

    function formatPhone(digits) {
        const rest = digits.startsWith('7') ? digits.slice(1) : digits;
        let formatted = '+7';
        if (rest.length > 0) {
            formatted += ' (' + rest.slice(0, 3);
        }
        if (rest.length >= 3) {
            formatted += ') ' + rest.slice(3, 6);
        }
        if (rest.length >= 6) {
            formatted += '-' + rest.slice(6, 8);
        }
        if (rest.length >= 8) {
            formatted += '-' + rest.slice(8, 10);
        }
        return formatted;
    }

    function applyDigits(digits, cursorDigitIndex) {
        const formatted = digits.length <= 1 ? PREFIX : formatPhone(digits);
        input.value = formatted;
        const pos = cursorPosForDigitIndex(formatted, Math.min(cursorDigitIndex, digits.length));
        input.setSelectionRange(pos, pos);
    }

    function countDigitsBefore(str, pos) {
        let count = 0;
        for (let i = 0; i < pos && i < str.length; i++) {
            if (/\d/.test(str[i])) {
                count++;
            }
        }
        return count;
    }

    function cursorPosForDigitIndex(formatted, digitIndex) {
        if (digitIndex <= 1) {
            return PREFIX.length;
        }
        let count = 0;
        for (let i = 0; i < formatted.length; i++) {
            if (/\d/.test(formatted[i])) {
                count++;
                if (count === digitIndex) {
                    return i + 1;
                }
            }
        }
        return formatted.length;
    }

    if (!input.value || input.value.trim() === '' || input.value === '+7') {
        input.value = PREFIX;
    }

    input.addEventListener('focus', function () {
        if (!input.value.startsWith('+7')) {
            input.value = PREFIX;
        }
    });

    input.addEventListener('keydown', function (e) {
        if (e.key !== 'Backspace' && e.key !== 'Delete') {
            return;
        }

        const start = input.selectionStart;
        const end = input.selectionEnd;
        if (start !== end) {
            return;
        }

        if (e.key === 'Backspace' && start <= PREFIX.length) {
            e.preventDefault();
            return;
        }

        if (e.key === 'Delete' && start < PREFIX.length) {
            e.preventDefault();
            input.setSelectionRange(PREFIX.length, PREFIX.length);
            return;
        }

        e.preventDefault();

        const digits = getDigits(input.value);
        const digitIndex = countDigitsBefore(input.value, start);

        if (e.key === 'Backspace') {
            if (digitIndex <= 1) {
                input.value = PREFIX;
                input.setSelectionRange(PREFIX.length, PREFIX.length);
                return;
            }
            const newDigits = digits.slice(0, digitIndex - 1) + digits.slice(digitIndex);
            applyDigits(newDigits, digitIndex - 1);
            return;
        }

        if (digitIndex >= digits.length) {
            return;
        }
        const newDigits = digits.slice(0, digitIndex) + digits.slice(digitIndex + 1);
        applyDigits(newDigits, digitIndex);
    });

    input.addEventListener('input', function () {
        const digits = getDigits(input.value);
        const cursorDigitIndex = countDigitsBefore(input.value, input.selectionStart);
        applyDigits(digits, cursorDigitIndex);
    });

    input.addEventListener('paste', function (e) {
        e.preventDefault();
        const pasted = (e.clipboardData || window.clipboardData).getData('text');
        const digits = getDigits(pasted);
        applyDigits(digits, digits.length);
    });
}
