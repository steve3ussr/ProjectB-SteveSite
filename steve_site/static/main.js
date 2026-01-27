const mql = window.matchMedia("(max-width: 768px)");

document.addEventListener("DOMContentLoaded", () => {
    /* mouse enter */
    function hdlMainNavEntryWrapperEnter(element, e) {
        if (e.matches) {
            return;
        } else {
            let subNav = element.querySelector(".sub-nav");
            let mainA = element.querySelector("a");
            let originalWidth = Number(element.getAttribute("originalWidth"));

            /* forced restore status before execute enter */
            element.style.width = `${element.getAttribute("originalWidth")}px`;
            subNav.style.pointerEvents = "none";
            mainNavEntryWrapperArr.forEach((item) => { if(element != item) item.style.pointerEvents = "none"; });

            /* add underline */
            mainA.style.borderBottom = "2px solid rgba(155, 144, 233, 0.7)";

            /* calculate offset value */
            let aWidth = mainA.clientWidth;
            let subNavWidth = subNav.clientWidth;

            /* translate subNav */
            subNav.style.opacity = 1;
            subNav.style.transform = `translateX(${aWidth + 15}px)`;
            element.style.width = `${originalWidth + subNavWidth + 15}px`;  //

            /* restore sub-nav pointer event */
            subNav.style.pointerEvents = "auto";
        }
    }

    /* mouse leave */
    function hdlMainNavEntryWrapperLeave(element, e) {
        if (e.matches) {
            return;
        } else {
            let subNav = element.querySelector(".sub-nav");
            let mainA = element.querySelector("a");

            /* forced restore status before execute enter */
            mainNavEntryWrapperArr.forEach((item) => { if(element != item) item.style.pointerEvents = "auto"; });

            /* remove underline */
            mainA.style.borderBottom = "2px solid rgba(155, 144, 233, 0)";

            /* calculate offset value */
            let aWidth = mainA.clientWidth;
            let subNavWidth = subNav.clientWidth;

            /* restore sub-nav pointer event */
            subNav.style.pointerEvents = "none";

            /* translate subNav */
            subNav.style.opacity = 0;
            subNav.style.transform = "translateX(0)";
            element.style.width = `${element.getAttribute("originalWidth")}px`;
        }
    }

    /* add event listener foreach wrapper */
    var mainNavEntryWrapperArr = document.querySelectorAll(".main-nav-entry-wrapper");
    mainNavEntryWrapperArr.forEach((entry) => {
        entry.addEventListener("mouseenter", () => {hdlMainNavEntryWrapperEnter(entry, mql)});
        entry.addEventListener("mouseleave", () => {hdlMainNavEntryWrapperLeave(entry, mql)});
        entry.setAttribute("originalWidth", entry.clientWidth);
    });

    /* add event listener foreach sub-nav */
    var subNavArr = document.querySelectorAll(".sub-nav");
    subNavArr.forEach((entry) => {
        entry.setAttribute("active", false);
    });
});

document.addEventListener("DOMContentLoaded", () => {
    const menuBtn = document.querySelector(".side-nav-hamburger");
    const sidebar = document.querySelector(".side-nav-drawer");
    const overlay = document.querySelector(".side-nav-cloak");
    const wrapperArray = document.querySelectorAll(".side-nav-entry-wrapper");

    menuBtn.setAttribute("state", "close");

    function toggleSidebar(btn) {
        let state = btn.getAttribute("state");

        if (state === "close") {
            sidebar.classList.add("active");
            overlay.classList.add("active");
            document.body.style.overflow = "hidden";
            btn.setAttribute("state", "open");
        } else {
            sidebar.classList.remove("active");
            overlay.classList.remove("active");
            document.body.style.overflow = "auto";
            btn.setAttribute("state", "close");
        }
    }

    wrapperArray.forEach((item) => item.setAttribute("state", "close"));

    menuBtn.addEventListener("click", () => { toggleSidebar(menuBtn) });
    sidebar.addEventListener("click", (e) => {
        let wrapper = e.target.closest(".side-nav-entry-wrapper");
        if (!wrapper) return;

        let state = wrapper.getAttribute("state");
        if (state === "close") {
            wrapper.classList.add("expand");
            wrapper.querySelector(".side-nav-sub-list").classList.add("expand");
            wrapper.setAttribute("state", "open");
        } else {
            wrapper.classList.remove("expand");
            wrapper.querySelector(".side-nav-sub-list").classList.remove("expand");
            wrapper.setAttribute("state", "close");
        }
    });

});
