(function () {
    "use strict";

    // ── Active section tracking via IntersectionObserver ──────────────────
    const sections = Array.from(document.querySelectorAll("main [id]"));
    const navLinks = Array.from(document.querySelectorAll("nav a[href]"));

    if (!sections.length || !navLinks.length) return;

    const currentFile =
        window.location.pathname.split("/").pop() || "index.html";

    /**
     * Given a section id, mark the matching nav link as active and clear
     * the active class from all other links.
     */
    function setActive(id) {
        navLinks.forEach(function (link) {
            const href = link.getAttribute("href");
            const matches =
                href === "#" + id || href === currentFile + "#" + id;
            link.classList.toggle("active", matches);
        });
    }

    // IntersectionObserver fires when a section crosses the upper 30 % of
    // the viewport. rootMargin pushes the detection line down so the label
    // changes only once the heading is clearly visible.
    const observer = new IntersectionObserver(
        function (entries) {
            // Find the topmost section that is currently intersecting.
            const visible = entries
                .filter(function (e) {
                    return e.isIntersecting;
                })
                .sort(function (a, b) {
                    return (
                        a.boundingClientRect.top - b.boundingClientRect.top
                    );
                });

            if (visible.length) {
                setActive(visible[0].target.id);
            }
        },
        {
            rootMargin: "-80px 0px -60% 0px",
            threshold: 0,
        }
    );

    sections.forEach(function (s) {
        observer.observe(s);
    });
})();
