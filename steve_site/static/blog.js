var blogDeleteA = document.getElementById('blog-delete-anchor');
blogDeleteA.addEventListener('click', async (event) => {
    event.preventDefault();

    const flagConfirm = confirm("确定要删除吗?");
    if (!flagConfirm) return;

    try {
        const currUrl = window.location.pathname;
        const resp = await fetch(`${currUrl}/delete`, {method: 'DELETE'});
        window.location.href = resp.url;
    } catch (error) {
        alert("不知道为什么, 但是请求失败了");
    }
});
