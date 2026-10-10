function activateMode(modeName, targetUrl) {
    let modeBadge = document.getElementById("activeMode");
    if (modeBadge) {
        modeBadge.innerText = modeName;
    }
    if (targetUrl) {
        window.location.href = targetUrl;
    }
}

function loadPage(page) {
    let urlMap = {
        "home": "/dashboard/home/",
        "eye": "/dashboard/eye/",
    };

    if (urlMap[page]) {
        fetch(urlMap[page])
            .then(response => response.text())
            .then(html => {
                let contentArea = document.getElementById("content-area");
                if (contentArea) {
                    contentArea.innerHTML = html;
                }
            });
    }

    document.querySelectorAll(".nav-item").forEach(item => {
        item.classList.remove("active");
    });

    if (window.event && window.event.target) {
        window.event.target.classList.add("active");
    }
}

function toggleSidebar(){
    let sidebar = document.getElementById("sidebar");
    if (sidebar) {
        sidebar.classList.toggle("collapsed");
    }
}