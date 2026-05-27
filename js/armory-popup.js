document.addEventListener("DOMContentLoaded", function () {
    const hoverTriggers = document.querySelectorAll(".hover-trigger");
    let activePopup = null;
    let hideTimer = null;

    function getMode() {
        return window.location.pathname.toLowerCase().includes("hcbuilds") ? "hc" : "sc";
    }

    function resolvePopup(trigger) {
        return trigger.closest(".character-info")?.nextElementSibling?.querySelector(".popup") || null;
    }

    function buildPopupUrl(characterName) {
        const params = new URLSearchParams({
            charName: characterName,
            mode: getMode(),
        });
        return `./armory/video_component.html?${params.toString()}`;
    }

    function clearHideTimer() {
        if (hideTimer) {
            clearTimeout(hideTimer);
            hideTimer = null;
        }
    }

    function ensureIframe(popup, characterName) {
        const mode = getMode();
        const expectedSrc = buildPopupUrl(characterName);
        const existingFrame = popup.querySelector("iframe");

        if (
            existingFrame &&
            existingFrame.dataset.characterName === characterName &&
            existingFrame.dataset.mode === mode
        ) {
            return;
        }

        popup.innerHTML = "";

        const iframe = document.createElement("iframe");
        iframe.src = expectedSrc;
        iframe.loading = "lazy";
        iframe.title = `Armory for ${characterName}`;
        iframe.dataset.characterName = characterName;
        iframe.dataset.mode = mode;
        popup.appendChild(iframe);
    }

    function hidePopup(popup = activePopup) {
        clearHideTimer();
        if (!popup) {
            return;
        }

        popup.classList.remove("active");
        popup.classList.add("hidden");
        popup.style.display = "none";
        if (popup === activePopup) {
            activePopup = null;
        }
    }

    function scheduleHide(popup) {
        clearHideTimer();
        hideTimer = setTimeout(function () {
            hidePopup(popup);
        }, 140);
    }

    function showPopup(trigger) {
        const characterName = trigger.getAttribute("data-character-name");
        const popup = resolvePopup(trigger);
        if (!characterName || !popup) {
            return;
        }

        clearHideTimer();
        if (activePopup && activePopup !== popup) {
            hidePopup(activePopup);
        }

        ensureIframe(popup, characterName);
        popup.classList.remove("hidden");
        popup.classList.add("active");
        popup.style.display = "block";
        activePopup = popup;

        popup.onmouseenter = function () {
            clearHideTimer();
        };
        popup.onmouseleave = function () {
            scheduleHide(popup);
        };
    }

    hoverTriggers.forEach(function (trigger) {
        trigger.addEventListener("mouseenter", function () {
            showPopup(trigger);
        });

        trigger.addEventListener("mouseleave", function () {
            const popup = resolvePopup(trigger);
            if (popup) {
                scheduleHide(popup);
            }
        });

        trigger.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            const popup = resolvePopup(trigger);
            if (popup && popup === activePopup) {
                hidePopup(popup);
                return;
            }
            showPopup(trigger);
        });
    });

    document.addEventListener("click", function (event) {
        if (!activePopup) {
            return;
        }

        if (activePopup.contains(event.target) || event.target.closest(".hover-trigger")) {
            return;
        }

        hidePopup(activePopup);
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            hidePopup(activePopup);
        }
    });
});
