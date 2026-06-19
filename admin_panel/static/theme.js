const themeToggle = document.querySelector("[data-theme-toggle]");

function saveTheme(theme) {
    try {
        localStorage.setItem("adminTheme", theme);
    } catch (error) {
        return;
    }
}

function setThemeButtonLabel() {
    if (!themeToggle) {
        return;
    }

    const isDark = document.documentElement.dataset.theme === "dark";
    themeToggle.textContent = isDark ? "Light" : "Dark";
}

if (themeToggle) {
    setThemeButtonLabel();

    themeToggle.addEventListener("click", () => {
        const isDark = document.documentElement.dataset.theme === "dark";

        if (isDark) {
            delete document.documentElement.dataset.theme;
            saveTheme("light");
        } else {
            document.documentElement.dataset.theme = "dark";
            saveTheme("dark");
        }

        setThemeButtonLabel();
    });
}
