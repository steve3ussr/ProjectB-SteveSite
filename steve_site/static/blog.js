var blogDeleteBtn = document.getElementById('blog-delete-button');
blogDeleteBtn.addEventListener('click', () => {
    const flagConfirm = confirm("确定要删除吗?");
    if (!flagConfirm) return;

    const currUrl = window.location.pathname;
    const reMatchRes = currUrl.match(/\/blog\/(\d+)/);
    if (!reMatchRes) return;

    const blogId = reMatchRes[1];
    fetch(`/blog/delete/${blogId}`);
    window.location.replace(`${window.location.origin}/blog/`);
});