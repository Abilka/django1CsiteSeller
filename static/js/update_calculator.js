(function () {
    const configSelect = document.getElementById('configuration');
    const versionSelect = document.getElementById('current_version');
    const form = document.getElementById('calc-form');

    if (!configSelect || !versionSelect) {
        return;
    }

    configSelect.addEventListener('change', function () {
        loadVersions(configSelect.value);
    });

    function loadVersions(slug) {
        versionSelect.innerHTML = '<option value="">— Загрузка… —</option>';
        versionSelect.disabled = true;

        if (!slug) {
            versionSelect.innerHTML = '<option value="">— Выберите релиз —</option>';
            return;
        }

        const apiBase = (window.UPDATE_CALC && window.UPDATE_CALC.apiBase) || '/api/v1/configurations/';
        fetch(apiBase + encodeURIComponent(slug) + '/versions/')
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('Не удалось загрузить список релизов');
                }
                return response.json();
            })
            .then(function (data) {
                versionSelect.innerHTML = '<option value="">— Выберите релиз —</option>';
                (data.versions || []).forEach(function (version) {
                    const option = document.createElement('option');
                    option.value = version;
                    option.textContent = version;
                    versionSelect.appendChild(option);
                });
                versionSelect.disabled = false;
            })
            .catch(function () {
                versionSelect.innerHTML = '<option value="">— Ошибка загрузки —</option>';
            });
    }

    if (form) {
        form.addEventListener('submit', function () {
            versionSelect.disabled = false;
        });
    }
})();
