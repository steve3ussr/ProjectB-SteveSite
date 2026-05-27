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