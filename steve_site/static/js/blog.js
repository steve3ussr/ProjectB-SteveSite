// blog-detail-delete
document.addEventListener('DOMContentLoaded', () => {
    var blogDeleteA = document.getElementById('blog-delete-anchor');
    if (!blogDeleteA) return;

    blogDeleteA.addEventListener('click', async (event) => {
        event.preventDefault();
        if (!confirm("确定要删除吗?")) return;

        try {
            const currUrl = window.location.pathname;
            const resp = await fetch(`${currUrl}/delete`, {method: 'DELETE'});
            window.location.href = resp.url;
        } catch (error) {
            alert("不知道为什么, 但是请求失败了");
        }
    });
});

// blog-back-to-top
document.addEventListener('DOMContentLoaded', () => {
    const backBtn = document.getElementById('back-to-top-btn');

    if (!backBtn) return;
    window.addEventListener("scroll", () => {
        const threshold = window.innerHeight * 0.8;
        if (window.scrollY > threshold) backBtn.classList.add('back-to-top-btn-show');
        else backBtn.classList.remove('back-to-top-btn-show');
    }, {passive: true});

    backBtn.addEventListener('click', () => {
        window.scrollTo({top: 0, behavior: 'smooth'});
    });
});

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
