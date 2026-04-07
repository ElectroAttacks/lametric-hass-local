(function () {
    "use strict";

    const sections = Array.from(document.querySelectorAll("main section[id]"));
    const navLinks = Array.from(document.querySelectorAll("nav a[href]"));

    if (!sections.length || !navLinks.length) return;

    const currentFile =
        window.location.pathname.split("/").pop() || "index.html";

    function setActive(id) {
        navLinks.forEach(function (link) {
            const href = link.getAttribute("href");
            const matches =
                href === "#" + id || href === currentFile + "#" + id;
            link.classList.toggle("active", matches);
        });
    }

    function updateActive() {
        // At the bottom of the page always activate the last section,
        // because short final sections may never cross the scroll threshold.
        if (
            Math.ceil(window.scrollY + window.innerHeight) >=
            document.documentElement.scrollHeight
        ) {
            setActive(sections[sections.length - 1].id);
            return;
        }

        // The active section is the last one whose top edge is above 40 % of
        // the viewport (i.e. it is already well into view from the top).
        const threshold = window.innerHeight * 0.4;
        let current = null;
        for (var i = 0; i < sections.length; i++) {
            if (sections[i].getBoundingClientRect().top <= threshold) {
                current = sections[i];
            }
        }

        // Fallback: nothing crossed threshold yet — use the first section
        // that actually has a corresponding nav link (e.g. at page top).
        if (!current) {
            for (var j = 0; j < sections.length; j++) {
                var fid = sections[j].id;
                var hasLink = navLinks.some(function (l) {
                    var h = l.getAttribute("href");
                    return h === "#" + fid || h === currentFile + "#" + fid;
                });
                if (hasLink) { current = sections[j]; break; }
            }
        }

        if (current) {
            setActive(current.id);
        }
    }

    window.addEventListener("scroll", updateActive, { passive: true });
    updateActive();
})();
