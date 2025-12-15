/* main-nav-entry-wrapper array */
var mainNavEntryWrapperArr = document.querySelectorAll(".main-nav-entry-wrapper");


function hdlMainNavEntryWrapperEnter(element) {
    let subNav = element.querySelector(".sub-nav");
    let a = element.querySelector("a");

    /* add underline for main-nav a */
    a.style.borderBottom = "2px solid rgba(155, 144, 233, 0.7)";

    /* calculate offset value */
    let aWidth = a.clientWidth;
    let subNavWidth = subNav.clientWidth;

    /* 
        translate subNav by aWidth, opacity=1
        adjust wrapper size
     */
    subNav.style.opacity = 1;
    subNav.style.transform = `translateX(${aWidth+15}px)`;
    element.style.pointerEvents = "auto";
    element.style.width = `${element.clientWidth+subNavWidth}px`;

    // /* translate all main-nav-entry-wrapper behind */
    // let behindingMainNavEntryWrapperArr = document.querySelectorAll(`#${element.id} ~ .main-nav-entry-wrapper`);
    // behindingMainNavEntryWrapperArr.forEach((behindElement) => {
    //     behindElement.style.transform = `translateX(${subNavWidth-40}px)`;
    // });

}

function hdlMainNavEntryWrapperLeave(element) {
    let subNav = element.querySelector(".sub-nav");
    let a = element.querySelector("a");

    /* remove underline for main-nav a */
    a.style.borderBottom = "2px solid rgba(155, 144, 233, 0)";

    /* calculate offset value */
    let aWidth = a.clientWidth;
    let subNavWidth = subNav.clientWidth;

    /* translate subNav by aWidth, opacity=0 */
    subNav.style.opacity = 0;
    subNav.style.transform = "translateX(0)";
    element.style.pointerEvents = "none";
    element.style.width = `${element.getAttribute("originalWidth")}px`;

    // /* translate all main-nav-entry-wrapper behind */
    // let behindingMainNavEntryWrapperArr = document.querySelectorAll(`#${element.id} ~ .main-nav-entry-wrapper`);
    // behindingMainNavEntryWrapperArr.forEach((behindElement) => {
    //     behindElement.style.transform = "translateX(0)";
    // });
}

function hdlSubNavTransEnd(element) {
    element.style.pointerEvents = "auto";
}

/* add event listener for each main-nav-entry-wrapper */
mainNavEntryWrapperArr.forEach((entry) => {
    entry.addEventListener('mouseenter', () => {hdlMainNavEntryWrapperEnter(entry)});
    entry.addEventListener('mouseleave', () => {hdlMainNavEntryWrapperLeave(entry)});
    entry.setAttribute("originalWidth", entry.clientWidth);
});

document.querySelectorAll(".sub-nav").forEach((subNavElement) => {
    subNavElement.addEventListener("transitionend", () => {hdlSubNavTransEnd(subNavElement)});
});
