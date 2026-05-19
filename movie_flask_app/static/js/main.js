/**
 * Small client-side helpers for the movie gallery app.
 */

document.addEventListener("DOMContentLoaded", function () {
    // Auto-hide flash messages after a few seconds
    const flashMessages = document.querySelectorAll(".flash-message");
    flashMessages.forEach(function (message) {
        setTimeout(function () {
            message.classList.add("flash-hide");
        }, 4500);
    });

    initAskAiForm();
});

function initAskAiForm() {
    const form = document.querySelector(".ask-form");
    if (!form) {
        return;
    }

    const textarea = form.querySelector("#question");
    const submitBtn = form.querySelector("#ask-submit-btn");
    const clientError = form.querySelector("#ask-client-error");
    const maxLength = parseInt(form.dataset.maxLength, 10) || 150;
    const defaultButtonText = submitBtn ? submitBtn.textContent : "Ask";

    function showClientError(message) {
        if (!clientError) {
            return;
        }
        clientError.textContent = message;
        clientError.hidden = false;
    }

    function hideClientError() {
        if (!clientError) {
            return;
        }
        clientError.textContent = "";
        clientError.hidden = true;
    }

    function setLoadingState(isLoading) {
        if (!submitBtn) {
            return;
        }
        submitBtn.disabled = isLoading;
        submitBtn.textContent = isLoading ? "Thinking..." : defaultButtonText;
        submitBtn.classList.toggle("is-loading", isLoading);
    }

    function validateQuestion(cleaned) {
        if (!cleaned) {
            return "Please enter a question.";
        }
        if (cleaned.length > maxLength) {
            return "Question is too long. Maximum length is 150 characters.";
        }
        return null;
    }

    form.addEventListener("submit", function (event) {
        const cleaned = textarea.value.trim();
        textarea.value = cleaned;
        hideClientError();

        const validationMessage = validateQuestion(cleaned);
        if (validationMessage) {
            event.preventDefault();
            showClientError(validationMessage);
            setLoadingState(false);
            return;
        }

        setLoadingState(true);
    });

    // Trim spaces when the user leaves the field
    textarea.addEventListener("blur", function () {
        textarea.value = textarea.value.trim();
    });
}
