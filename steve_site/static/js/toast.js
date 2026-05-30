function showToast(msg_type, msg, msg_callback, callback) {
    const toast = document.getElementById('toast-msg-container');
    if (!toast) return;

    const toastTextMain = document.getElementById('toast-msg-main');
    const toastTextCallback = document.getElementById('toast-msg-callback');
    const toastIcon = document.getElementById('toast-icon');

    toastTextMain.innerText = msg;
    if (msg_callback) {
        toastTextCallback.innerText = msg_callback;
    } else {
        toastTextCallback.innerText = '';
    }

    if (msg_type === "success") {
        toastIcon.classList.add("far", "fa-check-circle");
    } else if (msg_type === "warning") {
        toastIcon.classList.add("fas", "fa-exclamation-circle");
    } else if (msg_type === "error") {
        toastIcon.classList.add("far", "fa-times-circle");
    } else {
        return;
    }

    toast.classList.add('toast-show');

    setTimeout(() => {
        toast.classList.remove('toast-show');
        toast.addEventListener('transitionend', (e) => {
            if (e.propertyName === 'opacity') {
                if (msg_type === "success") {
                    toastIcon.classList.remove("far", "fa-check-circle");
                } else if (msg_type === "warning") {
                    toastIcon.classList.remove("fas", "fa-exclamation-circle");
                } else if (msg_type === "error") {
                    toastIcon.classList.remove("far", "fa-times-circle");
                }
                if (callback) { setTimeout(callback, 500); }
            }
        }, {once: true})

        // if (callback) {
        //     setTimeout(callback, 500);
        // }
    }, 2000);  // toast message fade away in 2.5s
    /*
     * 0s: 触发开始动画
     * 0.5s: 开始动画结束
     * 2.5s: 开始执行
     * 2.5s: 执行结束动画       执行callback(url跳转,按钮恢复动画0.5s)
     * 3s: toast完全消失       跳转完成, 按钮恢复
     * 3s: icon class清除
     * 3s: 执行callback
     * 3.5s: 按钮恢复
     */
}