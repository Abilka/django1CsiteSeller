(function () {
    'use strict';

    var STORAGE_KEY = 'tortug_cookie_consent_v1';
    var root = document.getElementById('cookie-consent-root');
    if (!root) {
        return;
    }

    var yandexId = (root.dataset.yandexId || '').trim();
    var googleId = (root.dataset.googleId || '').trim();
    if (!yandexId && !googleId) {
        return;
    }

    var banner = document.getElementById('cookie-consent-banner');
    var acceptBtn = document.getElementById('cookie-consent-accept');
    var rejectBtn = document.getElementById('cookie-consent-reject');
    var analyticsLoaded = false;

    function readConsent() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) {
                return null;
            }
            var data = JSON.parse(raw);
            if (!data || typeof data.analytics !== 'boolean' || data.version !== 1) {
                return null;
            }
            return data;
        } catch (error) {
            return null;
        }
    }

    function writeConsent(analytics) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({
            version: 1,
            analytics: analytics,
            timestamp: new Date().toISOString(),
        }));
    }

    function loadScript(src) {
        return new Promise(function (resolve, reject) {
            var script = document.createElement('script');
            script.async = true;
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    function initYandexMetrica() {
        if (!yandexId || window['yaCounter' + yandexId]) {
            return;
        }

        window.ym = window.ym || function () {
            (window.ym.a = window.ym.a || []).push(arguments);
        };
        window.ym.l = Date.now();

        return loadScript('https://mc.yandex.ru/metrika/tag.js').then(function () {
            window.ym(yandexId, 'init', {
                clickmap: true,
                trackLinks: true,
                accurateTrackBounce: true,
                webvisor: false,
                ecommerce: 'dataLayer',
            });
        });
    }

    function initGoogleAnalytics() {
        if (!googleId) {
            return Promise.resolve();
        }

        window.dataLayer = window.dataLayer || [];
        window.gtag = window.gtag || function () {
            window.dataLayer.push(arguments);
        };
        window.gtag('js', new Date());
        window.gtag('consent', 'default', {
            analytics_storage: 'denied',
            ad_storage: 'denied',
            ad_user_data: 'denied',
            ad_personalization: 'denied',
        });
        window.gtag('consent', 'update', {
            analytics_storage: 'granted',
            ad_storage: 'denied',
            ad_user_data: 'denied',
            ad_personalization: 'denied',
        });

        return loadScript('https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(googleId))
            .then(function () {
                window.gtag('config', googleId, {
                    anonymize_ip: true,
                    allow_google_signals: false,
                    allow_ad_personalization_signals: false,
                });
            });
    }

    function disableAnalytics() {
        if (googleId) {
            window['ga-disable-' + googleId] = true;
        }
        if (yandexId) {
            window['ym-disable-' + yandexId] = true;
        }
    }

    function enableAnalytics() {
        if (analyticsLoaded) {
            return;
        }

        analyticsLoaded = true;
        if (googleId) {
            window['ga-disable-' + googleId] = false;
        }
        if (yandexId) {
            window['ym-disable-' + yandexId] = false;
        }

        Promise.all([
            initYandexMetrica(),
            initGoogleAnalytics(),
        ]).catch(function () {
            analyticsLoaded = false;
        });
    }

    function hideBanner() {
        if (!banner) {
            return;
        }
        banner.hidden = true;
        banner.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('cookie-consent-open');
    }

    function showBanner() {
        if (!banner) {
            return;
        }
        banner.hidden = false;
        banner.setAttribute('aria-hidden', 'false');
        document.body.classList.add('cookie-consent-open');
        if (acceptBtn) {
            acceptBtn.focus();
        }
    }

    function applyConsent(consent) {
        if (consent.analytics) {
            enableAnalytics();
        } else {
            disableAnalytics();
        }
        hideBanner();
    }

    function handleAccept() {
        writeConsent(true);
        enableAnalytics();
        hideBanner();
    }

    function handleReject() {
        writeConsent(false);
        disableAnalytics();
        hideBanner();
    }

    if (acceptBtn) {
        acceptBtn.addEventListener('click', handleAccept);
    }
    if (rejectBtn) {
        rejectBtn.addEventListener('click', handleReject);
    }

    document.addEventListener('click', function (event) {
        var trigger = event.target.closest('[data-cookie-settings]');
        if (!trigger) {
            return;
        }
        event.preventDefault();
        showBanner();
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && banner && !banner.hidden) {
            handleReject();
        }
    });

    var consent = readConsent();
    if (consent) {
        applyConsent(consent);
    } else {
        showBanner();
    }

    window.TortugCookieConsent = {
        openSettings: showBanner,
        getConsent: readConsent,
        revoke: function () {
            writeConsent(false);
            disableAnalytics();
            showBanner();
        },
    };
})();
