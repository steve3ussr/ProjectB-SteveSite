document.addEventListener("DOMContentLoaded", () => {
    /* mouse enter */
    function hdlMainNavEntryWrapperEnter(element) {
        let subNav = element.querySelector(".sub-nav");
        let mainA = element.querySelector("a");

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
        element.style.width = `${element.clientWidth + subNavWidth + 15}px`;  //

        /* restore sub-nav pointer event */
        subNav.style.pointerEvents = "auto";
    }

    /* mouse leave */
    function hdlMainNavEntryWrapperLeave(element) {
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

    /* add event listener foreach wrapper */
    var mainNavEntryWrapperArr = document.querySelectorAll(".main-nav-entry-wrapper");
    mainNavEntryWrapperArr.forEach((entry) => {
        entry.addEventListener("mouseenter", () => {hdlMainNavEntryWrapperEnter(entry)});
        entry.addEventListener("mouseleave", () => {hdlMainNavEntryWrapperLeave(entry)});
        entry.setAttribute("originalWidth", entry.clientWidth);
    });

    /* add event listener foreach sub-nav */
    var subNavArr = document.querySelectorAll(".sub-nav");
    subNavArr.forEach((entry) => {
        entry.setAttribute("active", false);
    });
});