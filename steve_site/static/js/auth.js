function flashMsg(msg_type, msg) {
    const warningDiv = document.querySelector(".auth-warning");
    const warningSpan = document.querySelector(".auth-warning > span");
    const warningIcon = document.querySelector(".auth-warning > i");

    warningSpan.innerText = "";
    warningIcon.className = "";
    warningDiv.style.display = "none";

    warningSpan.innerText = msg;
    if (msg_type === "error") {
        warningIcon.className = "fas fa-times";
        warningIcon.style.color = "#d1242f";
    } else if (msg_type === "warning") {
        warningIcon.className = "fas fa-exclamation-triangle";
        warningIcon.style.color = "#FF8B36DB";
    } else if (msg_type === "success") {
        warningIcon.className = "fas fa-check";
        warningIcon.style.color = "#199f48";
    }
    warningDiv.style.display = "flex";
}


async function submitAuthForm(event, data, text) {
    // submitter text switch
        const btn = event.submitter;
        let originalText = btn.innerText;
        btn.innerText = text;
        btn.disabled = true;
        btn.classList.add('btn-submit-disabled');

        // btn recover
        const btnRecover = () => {
            btn.disabled = false;
            btn.classList.remove('btn-submit-disabled');
            btn.innerText = originalText;
        };

        try {
            const response = await fetch(window.location.href, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });

            const result = await response.json();
            if (Object.hasOwn(result, 'redirect_url')) {
                setTimeout(() => {
                    btnRecover();
                    flashMsg(result.status, result.msg);
                    setTimeout(() => {
                        window.location.href = result.redirect_url
                    }, 3000);
                }, 1000);
            } else {
                setTimeout(()=>{
                    btnRecover();
                    flashMsg(result.status, result.msg);
                }, 1000);
            }

        } catch (error) {
            setTimeout(()=>{
                btnRecover();
                flashMsg("error", `请求出错: ${error}`);
                }, 1000);
        }
}


// login-form
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('login-form');
    if (!form) return;
    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        // make submit json
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        if (!event.submitter) {
            console.error(`Error: missing submit button`);
            return;
        }

        await submitAuthForm(event, data, "登录中...");
    })
})


// register-form
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('register-form');
    if (!form) return;

    const inputPwd = document.getElementById('auth-form-password');
    const inputPwdCfm = document.getElementById('auth-form-password-confirm');

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        // make submit json
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        if (!event.submitter) {
            console.error(`Error: missing submit button`);
            return;
        }

        // check password == password-confirm
        if (data['password'] !== data['password-confirm']) {
            flashMsg("warning", `两次输入密码不一致`);
            inputPwd.classList.add('input-warning-border');
            inputPwdCfm.classList.add('input-warning-border');
            setTimeout(() => {
                inputPwd.classList.remove('input-warning-border');
                inputPwdCfm.classList.remove('input-warning-border');
            }, 2000);
            return;
        }

        await submitAuthForm(event, data, "注册中...");
    })
})


// reset-password-form
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('reset-password-form');
    if (!form) return;

    const inputPwd = document.getElementById('auth-form-password');
    const inputPwdCfm = document.getElementById('auth-form-password-confirm');

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        // make submit json
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        if (!event.submitter) {
            console.error(`Error: missing submit button`);
            return;
        }

        await submitAuthForm(event, data, "验证中...");
    })
})


// new-password-form
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('new-password-form');
    if (!form) return;

    const inputPwd = document.getElementById('auth-form-password');
    const inputPwdCfm = document.getElementById('auth-form-password-confirm');

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        // make submit json
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        if (!event.submitter) {
            console.error(`Error: missing submit button`);
            return;
        }

        // check password == password-confirm
        if (data['password'] !== data['password-confirm']) {
            flashMsg("warning", `两次输入密码不一致`);
            inputPwd.classList.add('input-warning-border');
            inputPwdCfm.classList.add('input-warning-border');
            setTimeout(() => {
                inputPwd.classList.remove('input-warning-border');
                inputPwdCfm.classList.remove('input-warning-border');
            }, 2000);
            return;
        }

        await submitAuthForm(event, data, "处理中...");
    })
})


// renew-username-form
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('renew-username-form');
    if (!form) return;

    const inputUsr = document.getElementById('auth-form-username');

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        // make submit json
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        if (!event.submitter) {
            console.error(`Error: missing submit button`);
            return;
        }

        await submitAuthForm(event, data, "更新中...");
    })
})


// renew-password-form
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('renew-password-form');
    if (!form) return;

    const inputPwd = document.getElementById('auth-form-password');
    const inputPwdCfm = document.getElementById('auth-form-password-confirm');

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        // make submit json
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        if (!event.submitter) {
            console.error(`Error: missing submit button`);
            return;
        }

        // check password == password-confirm
        if (data['password'] !== data['password-confirm']) {
            flashMsg("warning", `两次输入密码不一致`);
            inputPwd.classList.add('input-warning-border');
            inputPwdCfm.classList.add('input-warning-border');
            setTimeout(() => {
                inputPwd.classList.remove('input-warning-border');
                inputPwdCfm.classList.remove('input-warning-border');
            }, 2000);
            return;
        }

        await submitAuthForm(event, data, "更新中...");
    })
})