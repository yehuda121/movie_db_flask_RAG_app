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
});
