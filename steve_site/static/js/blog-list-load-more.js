// blog-list-main-load-more
document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('blog-load-more-btn');
    const entries = document.querySelectorAll('.blog-entry');
    if ((entries.length == 0) && (btn)) btn.style.display = "none";

    let defaultCount = 10;
    const step = 20;

    let currIndex = defaultCount;

    const renderVisibleItems = () => {
        entries.forEach((item, index) => {
            if (index < currIndex) item.setAttribute('blog-visible', 'true');
        });
    };

    renderVisibleItems();

    if (!btn) return;
    btn.addEventListener('click', () => {
        currIndex += step;
        renderVisibleItems();
        if (currIndex >= entries.length) btn.style.display = 'none';
    });
});