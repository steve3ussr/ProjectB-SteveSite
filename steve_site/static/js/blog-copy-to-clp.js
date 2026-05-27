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