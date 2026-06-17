function copyCore(s) {
    if (navigator.clipboard && window.isSecureContext) {
        return navigator.clipboard.writeText(s);
    }

    return new Promise((resolve, reject) => {
        const textarea = document.createElement("textarea");
        textarea.id = "_tmp_copy_to_clipboard_textarea";
        textarea.value = s;
        textarea.style.opacity = '0';
        textarea.style.zIndex = '-99';
        document.body.appendChild(textarea);

        textarea.focus();
        textarea.select();
        const res = document.execCommand("copy");

        if (res) {
            resolve();
        } else {
            reject();
        }
    });
}

function copyLinkToClipboard(btn) {
    const currBlogLink = window.location.href;
    const titleElement = document.querySelector('.article-title');
    if (!titleElement) {
        console.error("<copyLinkToClipboard> get article-title failed");
        return;
    }
    const textToCopy = `标题: [${titleElement.innerText}] 链接: ${currBlogLink}`;

    copyCore(textToCopy).then(() => {
        const bubble = document.getElementById('share-bubble');
        bubble.classList.add('show');
        setTimeout(() => {
            bubble.classList.remove('show');
        }, 1000);
    }).catch((err) => {
        console.error("复制链接至剪贴板失败: ", err);
        const textarea = document.getElementById("_tmp_copy_to_clipboard_textarea");
        if (textarea) document.body.removeChild(textarea);
    });

}