// Project JavaScript lives here. Keep Django form and URL behavior intact.
document.addEventListener("click", function(event) {
    const row = event.target.closest(".clickable-row");
    if (!row || event.target.closest("a, button, input, select, textarea")) {
        return;
    }

    const href = row.dataset.href;
    if (href) {
        window.location.href = href;
    }
});

document.addEventListener("keydown", function(event) {
    if (event.key !== "Enter" && event.key !== " ") {
        return;
    }

    const row = event.target.closest(".clickable-row");
    if (!row) {
        return;
    }

    const href = row.dataset.href;
    if (href) {
        event.preventDefault();
        window.location.href = href;
    }
});
