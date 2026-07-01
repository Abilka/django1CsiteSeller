(function () {
    'use strict';

    var POLL_INTERVAL_MS = 30000;
    var STORAGE_KEY = 'adminLeadNotifyLastId';

    if (!('Notification' in window)) {
        return;
    }

    var script = document.currentScript;
    var pollUrl = script && script.getAttribute('data-poll-url');
    var iconUrl = (script && script.getAttribute('data-icon')) || '/static/favicon.ico';

    if (!pollUrl) {
        return;
    }

    function getLastId() {
        var value = localStorage.getItem(STORAGE_KEY);
        if (value === null) {
            return null;
        }
        var parsed = parseInt(value, 10);
        return Number.isFinite(parsed) ? parsed : null;
    }

    function setLastId(id) {
        localStorage.setItem(STORAGE_KEY, String(id));
    }

    function poll(afterId) {
        var url = pollUrl;
        if (afterId !== null) {
            url += (url.indexOf('?') >= 0 ? '&' : '?') + 'after_id=' + encodeURIComponent(afterId);
        }
        return fetch(url, { credentials: 'same-origin' }).then(function (response) {
            if (!response.ok) {
                return null;
            }
            return response.json();
        });
    }

    function showNotification(lead) {
        var parts = [lead.phone, lead.service].filter(Boolean);
        var notification = new Notification('Новая заявка: ' + lead.name, {
            body: parts.join(' · '),
            icon: iconUrl,
            tag: 'lead-' + lead.id,
        });
        notification.onclick = function () {
            window.focus();
            window.location.href = lead.admin_url;
            notification.close();
        };
    }

    var pollTimer = null;

    function checkLeads() {
        var lastId = getLastId();
        return poll(lastId).then(function (data) {
            if (!data) {
                return;
            }

            if (lastId === null) {
                setLastId(data.latest_id);
                return;
            }

            data.leads.forEach(showNotification);
            if (data.latest_id > lastId) {
                setLastId(data.latest_id);
            }
        });
    }

    function startPolling() {
        if (pollTimer !== null) {
            return;
        }
        checkLeads();
        pollTimer = window.setInterval(checkLeads, POLL_INTERVAL_MS);
    }

    function removeBanner() {
        var banner = document.getElementById('lead-notify-banner');
        if (banner) {
            banner.remove();
        }
    }

    function showEnableBanner() {
        if (document.getElementById('lead-notify-banner')) {
            return;
        }

        var banner = document.createElement('div');
        banner.id = 'lead-notify-banner';
        banner.setAttribute('role', 'status');
        banner.style.cssText = [
            'position:fixed',
            'bottom:16px',
            'right:16px',
            'z-index:9999',
            'max-width:360px',
            'padding:12px 14px',
            'border-radius:8px',
            'background:#417690',
            'color:#fff',
            'box-shadow:0 4px 16px rgba(0,0,0,.2)',
            'font:14px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
        ].join(';');

        banner.innerHTML = [
            '<p style="margin:0 0 10px;">Получать уведомления о новых заявках с сайта?</p>',
            '<button type="button" id="lead-notify-enable" style="margin-right:8px;padding:6px 12px;border:0;border-radius:4px;background:#fff;color:#417690;font-weight:600;cursor:pointer;">Включить</button>',
            '<button type="button" id="lead-notify-dismiss" style="padding:6px 12px;border:1px solid rgba(255,255,255,.5);border-radius:4px;background:transparent;color:#fff;cursor:pointer;">Не сейчас</button>',
        ].join('');

        document.body.appendChild(banner);

        document.getElementById('lead-notify-enable').addEventListener('click', function () {
            Notification.requestPermission().then(function (permission) {
                removeBanner();
                if (permission === 'granted') {
                    startPolling();
                }
            });
        });

        document.getElementById('lead-notify-dismiss').addEventListener('click', removeBanner);
    }

    function init() {
        if (Notification.permission === 'granted') {
            startPolling();
        } else if (Notification.permission === 'default') {
            showEnableBanner();
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
