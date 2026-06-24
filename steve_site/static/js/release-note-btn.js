document.addEventListener("DOMContentLoaded", () => {
    const btn = document.querySelector(".release-note-btn");
    const timeline = document.querySelector(".release-note-timeline");

    btn.addEventListener("click", (e) => {
        const currHeight = window.getComputedStyle(timeline).maxHeight;
        const originalHeight = timeline.scrollHeight;
        if (currHeight === "170px" && btn.innerText === "展示更多 ▼") {
            timeline.style.maxHeight = originalHeight + 'px';
            btn.innerText = "查看全部 »"
        } else if (btn.innerText === "查看全部 »") {
            window.location.href = "/release-note/";
        }
    })
})