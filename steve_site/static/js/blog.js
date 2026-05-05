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

// blog-detail-publish
document.addEventListener('DOMContentLoaded', () => {
    var blogPublishA = document.getElementById('blog-publish-anchor');
    if (!blogPublishA) return;

    blogPublishA.addEventListener('click', async (event) => {
        event.preventDefault();
        try {
            const currUrl = window.location.pathname;
            const resp = await fetch(`${currUrl}/publish`, {method: 'POST'});
            window.location.href = resp.url;
        } catch (error) {
            alert("不知道为什么, 但是请求失败了");
        }
    });
});

// blog-detail-submit
document.addEventListener('DOMContentLoaded', () => {
    var blogSubmitA = document.getElementById('blog-submit-anchor');
    if (!blogSubmitA) return;

    blogSubmitA.addEventListener('click', async (event) => {
        event.preventDefault();
        try {
            const currUrl = window.location.pathname;
            const resp = await fetch(`${currUrl}/submit`, {method: 'POST'});
            window.location.href = resp.url;
        } catch (error) {
            alert("不知道为什么, 但是请求失败了");
        }
    });
});

// blog-detail-hide
document.addEventListener('DOMContentLoaded', () => {
    var blogHideA = document.getElementById('blog-hide-anchor');
    if (!blogHideA) return;

    blogHideA.addEventListener('click', async (event) => {
        event.preventDefault();
        try {
            const currUrl = window.location.pathname;
            const resp = await fetch(`${currUrl}/hide`, {method: 'POST'});
            window.location.href = resp.url;
        } catch (error) {
            alert("不知道为什么, 但是请求失败了");
        }
    });
});

// blog-detail-restore
document.addEventListener('DOMContentLoaded', () => {
    var blogRestoreA = document.getElementById('blog-restore-anchor');
    if (!blogRestoreA) return;

    blogRestoreA.addEventListener('click', async (event) => {
        event.preventDefault();
        try {
            const currUrl = window.location.pathname;
            const resp = await fetch(`${currUrl}/restore`, {method: 'POST'});
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

function copyLinkToClipboard(btn) {
    const currBlogLink = window.location.href;
    const titleElement = document.querySelector('.article-title');
    if (!titleElement) {
        console.error("<copyLinkToClipboard> get article-title failed");
        return;
    }
    const textToCopy = `标题: [${titleElement.innerText}] 链接: ${currBlogLink}`;

    navigator.clipboard.writeText(textToCopy).then(() => {
        const bubble = document.getElementById('share-bubble');
        bubble.classList.add('show');
        setTimeout(() => {
            bubble.classList.remove('show');
        }, 1000);
    }).catch((err) => {
        console.error("复制链接至剪贴板失败: ", err);
    });

}
