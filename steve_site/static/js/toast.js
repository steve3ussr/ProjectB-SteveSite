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
        if (msg_type === "success") {
            toastIcon.classList.remove("far", "fa-check-circle");
        } else if (msg_type === "warning") {
            toastIcon.classList.remove("fas", "fa-exclamation-circle");
        } else if (msg_type === "error") {
            toastIcon.classList.remove("far", "fa-times-circle");
        } else {
            return;
        }
        if (callback) {
            
            setTimeout(callback, 300);
        }
    }, 2500);  // toast message fade away in 2.5s
}