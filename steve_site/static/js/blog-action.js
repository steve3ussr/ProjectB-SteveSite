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

/* blog-editor form submit event */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('blog-edit-form');
    if (!form) return;
    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        if (!event.submitter || !event.submitter.value) {
            console.error(`Error: submit button has no action`);
            return;
        }

        data['action'] = event.submitter.value;

        try {
            const response = await fetch(window.location.href, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });

            const result = await response.json();
            if (response.ok) {
                showToast('success', result.msg, "3秒后自动跳转", ()=>{
                    setTimeout(() => { window.location.href = result.redirect_url }, 500);
                });
            } else {
                showToast("warning", `提交失败, 请重试: `, `${result.msg}`);
            }

        } catch (error) {
            showToast("error", `请求出错: ${error}`);
        }
    })
})
