(function () {
    const configSelect = document.getElementById('configuration');
    const targetSelect = document.getElementById('target_release');
    const currentSelect = document.getElementById('current_release');
    const form = document.getElementById('platform-check-form');

    if (!configSelect || !targetSelect || !currentSelect) {
        return;
    }

    configSelect.addEventListener('change', function () {
        loadReleases(configSelect.value);
    });

    function loadReleases(slug) {
        const loading = '<option value="">— Загрузка… —</option>';
        targetSelect.innerHTML = loading;
        currentSelect.innerHTML = '<option value="">— Не указывать —</option>';
        targetSelect.disabled = true;
        currentSelect.disabled = true;

        if (!slug) {
            targetSelect.innerHTML = '<option value="">— Последний релиз —</option>';
            return;
        }

        const apiBase = (window.TOOL_CONFIG && window.TOOL_CONFIG.versionsUrl) || '/api/v1/configurations/';
        fetch(apiBase + encodeURIComponent(slug) + '/versions/')
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('load failed');
                }
                return response.json();
            })
            .then(function (data) {
                targetSelect.innerHTML = '<option value="">— Последний релиз —</option>';
                currentSelect.innerHTML = '<option value="">— Не указывать —</option>';
                (data.versions || []).forEach(function (version) {
                    const targetOption = document.createElement('option');
                    targetOption.value = version;
                    targetOption.textContent = version;
                    targetSelect.appendChild(targetOption);

                    const currentOption = document.createElement('option');
                    currentOption.value = version;
                    currentOption.textContent = version;
                    currentSelect.appendChild(currentOption);
                });
                targetSelect.disabled = false;
                currentSelect.disabled = false;
            })
            .catch(function () {
                targetSelect.innerHTML = '<option value="">— Ошибка загрузки —</option>';
            });
    }

    if (form) {
        form.addEventListener('submit', function () {
            targetSelect.disabled = false;
            currentSelect.disabled = false;
        });
    }
})();
