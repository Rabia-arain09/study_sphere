// Main client-side script for StudySphere

(function() {
    function initThemeSwitch() {
        var currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        var buttons = document.querySelectorAll('.theme-btn');

        function updateActiveButton(theme) {
            buttons.forEach(function(btn) {
                var btnTheme = btn.getAttribute('data-theme') || btn.getAttribute('data-theme-val');
                var isActive = btnTheme === theme;
                if (isActive) {
                    btn.classList.add('active');
                    btn.setAttribute('aria-pressed', 'true');
                } else {
                    btn.classList.remove('active');
                    btn.setAttribute('aria-pressed', 'false');
                }
            });
        }

        updateActiveButton(currentTheme);

        buttons.forEach(function(btn) {
            btn.addEventListener('click', function() {
                var newTheme = this.getAttribute('data-theme') || this.getAttribute('data-theme-val');
                if (!newTheme) return;

                document.documentElement.setAttribute('data-theme', newTheme);
                try {
                    localStorage.setItem('studysphere-theme', newTheme);
                } catch (e) {
                    // localStorage may be unavailable in sandboxed environments
                }
                updateActiveButton(newTheme);

                window.dispatchEvent(new CustomEvent('themechanged', { detail: { theme: newTheme } }));
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initThemeSwitch);
    } else {
        initThemeSwitch();
    }
})();
