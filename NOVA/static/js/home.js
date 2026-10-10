function toggleBox(element) {
    element.classList.toggle("active");
}

function scrollToSection(id) {
    document.getElementById(id).scrollIntoView({
        behavior: "smooth"
    });
}
