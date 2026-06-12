(function () {
    "use strict";

    // --- Copy run id to clipboard -------------------------------------
    document.querySelectorAll(".run-id[data-copy]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var value = btn.getAttribute("data-copy");
            var done = function () {
                btn.classList.add("copied");
                setTimeout(function () { btn.classList.remove("copied"); }, 1200);
            };
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(value).then(done).catch(function () {});
            }
        });
    });

    // --- Reveal bars from zero on load (skip if reduced motion) --------
    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;

    var bars = document.querySelectorAll(".gantt-bar, .stack-seg");
    bars.forEach(function (bar) {
        var target = bar.style.width;
        bar.style.width = "0";
        bar.dataset.target = target;
    });
    requestAnimationFrame(function () {
        requestAnimationFrame(function () {
            bars.forEach(function (bar) { bar.style.width = bar.dataset.target; });
        });
    });
})();
