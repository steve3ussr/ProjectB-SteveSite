const mql = window.matchMedia("(max-width: 768px)");

/* main-nav mouse enter/leave */
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
            if(subNav) subNav.style.pointerEvents = "none";
            mainNavEntryWrapperArr.forEach((item) => { if(element != item) item.style.pointerEvents = "none"; });

            /* add underline */
            mainA.style.borderBottom = "2px solid rgba(102, 103, 171, 0.3)";

            if (!subNav) return;

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
            mainA.style.borderBottom = "2px solid rgba(102, 103, 171, 0)";

            if (!subNav) return;

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

/* side-nav open/close */
document.addEventListener("DOMContentLoaded", () => {
    const hamburger = document.getElementById("side-nav-hamburger");
    const closeBtn = document.getElementById("side-nav-close-btn");
    const drawer = document.querySelector(".side-nav-drawer");
    const cloak = document.querySelector(".side-nav-cloak");
    const wrapperArray = document.querySelectorAll(".side-nav-entry-wrapper");

    wrapperArray.forEach((item) => {item.setAttribute("state", "close");});

    function closeDrawer() {
        drawer.classList.remove("active");
        cloak.classList.remove("active");

        wrapperArray.forEach((item) => {
            item.classList.remove("expand");
            let subList = item.querySelector(".side-nav-sub-list");
            if (subList) subList.classList.remove("expand");
            item.setAttribute("state", "close");
        });
    }

    hamburger.addEventListener("click", () => {
        drawer.classList.add("active");
        cloak.classList.add("active");
    });

    closeBtn.addEventListener("click", closeDrawer);
    cloak.addEventListener("click", closeDrawer);

    drawer.addEventListener("click", (e) => {
        let wrapper = e.target.closest(".side-nav-entry-wrapper");
        if (!wrapper) return;

        let state = wrapper.getAttribute("state");
        if (state === "close") {

            wrapperArray.forEach((item) => {
                item.classList.remove("expand");
                let subList = item.querySelector(".side-nav-sub-list");
                if (subList) subList.classList.remove("expand");
                item.setAttribute("state", "close");
            });

            wrapper.classList.add("expand");
            let subList = wrapper.querySelector(".side-nav-sub-list");
            if (subList) subList.classList.add("expand");
            wrapper.setAttribute("state", "open");
        } else {
            wrapper.classList.remove("expand");
            let subList = wrapper.querySelector(".side-nav-sub-list");
            if (subList) subList.classList.remove("expand");
            wrapper.setAttribute("state", "close");
        }
    });

});
