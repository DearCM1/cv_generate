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

    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // --- Proximity glow on Job-understanding chips --------------------
    if (!reduce) {
        var GLOW_RADIUS = 130; // px from chip centre at which the glow fades out
        document.querySelectorAll(".chip-group .chips").forEach(function (group) {
            var chips = Array.prototype.slice.call(group.querySelectorAll(".chip"));
            if (!chips.length) return;
            var px = 0, py = 0, frame = null;

            var paint = function () {
                frame = null;
                chips.forEach(function (chip) {
                    var r = chip.getBoundingClientRect();
                    var dx = px - (r.left + r.width / 2);
                    var dy = py - (r.top + r.height / 2);
                    var near = Math.max(0, 1 - Math.hypot(dx, dy) / GLOW_RADIUS);
                    chip.style.setProperty("--glow", (near * near).toFixed(3));
                });
            };

            group.addEventListener("pointermove", function (e) {
                px = e.clientX;
                py = e.clientY;
                if (frame === null) frame = requestAnimationFrame(paint);
            });
            group.addEventListener("pointerleave", function () {
                if (frame !== null) { cancelAnimationFrame(frame); frame = null; }
                chips.forEach(function (chip) { chip.style.setProperty("--glow", "0"); });
            });
        });
    }

    // --- Cost pies: token + dollar donuts with hover breakdown -------
    (function () {
        var dataEl = document.getElementById("costs-data");
        if (!dataEl) return;
        var charts;
        try { charts = JSON.parse(dataEl.textContent); } catch (e) { return; }

        var NS = "http://www.w3.org/2000/svg";
        var CX = 50, CY = 50, R = 44, HOLE = 27, EXPLODE = 4;

        var fmt = {
            int: function (n) { return n.toLocaleString("en-US"); },
            usd: function (n) { return "$" + n.toFixed(4); }
        };

        var TOKEN_COLORS = {
            "Input": "#6ea8fe",
            "Output": "#8b7cf6",
            "Cache write": "#f59e6b",
            "Cache read": "#4ade80"
        };
        var STAGE_COLORS = ["#6ea8fe", "#8b7cf6", "#f59e6b", "#4ade80", "#fbbf24"];

        function sliceColor(chart, seg, i) {
            if (chart.id === "tokens" && TOKEN_COLORS[seg.label]) return TOKEN_COLORS[seg.label];
            return STAGE_COLORS[i % STAGE_COLORS.length];
        }
        function rowColor(chart, row, seg) {
            if (chart.id === "cost" && TOKEN_COLORS[row.label]) return TOKEN_COLORS[row.label];
            return seg._color;
        }

        function polar(angle, r) {
            var a = (angle - 90) * Math.PI / 180;
            return [CX + r * Math.cos(a), CY + r * Math.sin(a)];
        }
        function wedge(start, end) {
            var s = polar(start, R), e = polar(end, R);
            var large = (end - start) > 180 ? 1 : 0;
            return "M " + CX + " " + CY +
                " L " + s[0].toFixed(3) + " " + s[1].toFixed(3) +
                " A " + R + " " + R + " 0 " + large + " 1 " + e[0].toFixed(3) + " " + e[1].toFixed(3) + " Z";
        }

        var mql = window.matchMedia("(max-width: 560px)");
        var instances = [];
        function closeAll() { instances.forEach(function (off) { off(); }); }

        var backdrop = document.createElement("div");
        backdrop.className = "pie-backdrop";
        document.body.appendChild(backdrop);
        backdrop.addEventListener("click", closeAll);

        charts.forEach(function (chart) {
            var card = document.querySelector('.pie[data-chart="' + chart.id + '"]');
            if (!card) return;
            var wrap = card.querySelector(".pie-wrap");
            var center = card.querySelector(".pie-center");
            var modal = card.querySelector(".pie-modal");
            var legend = card.querySelector(".pie-legend");
            var fmtVal = fmt[chart.format] || fmt.int;

            var segs = chart.segments.filter(function (s) { return s.value > 0; });
            var total = segs.reduce(function (sum, s) { return sum + s.value; }, 0);
            if (!segs.length || total <= 0) return;

            center.innerHTML =
                '<span class="pc-value">' + fmtVal(total) + "</span>" +
                '<span class="pc-label">' + (chart.centerLabel || "total") + "</span>";

            var svg = document.createElementNS(NS, "svg");
            svg.setAttribute("viewBox", "0 0 100 100");
            svg.setAttribute("class", "pie-svg");
            svg.setAttribute("role", "img");
            svg.setAttribute("aria-label", chart.title || chart.id);

            var paths = [];
            var angle = 0;
            segs.forEach(function (seg, i) {
                var end = angle + (seg.value / total) * 360;
                var p = document.createElementNS(NS, "path");
                p.setAttribute("d", wedge(angle, end));
                seg._color = sliceColor(chart, seg, i);
                p.setAttribute("fill", seg._color);
                p.setAttribute("class", "seg");
                var mid = polar((angle + end) / 2, 1);          // explode direction
                var dx = mid[0] - CX, dy = mid[1] - CY;
                var len = Math.hypot(dx, dy) || 1;
                seg._dx = dx / len; seg._dy = dy / len;
                svg.appendChild(p);
                paths.push(p);
                angle = end;
            });

            var hole = document.createElementNS(NS, "circle");
            hole.setAttribute("cx", CX); hole.setAttribute("cy", CY);
            hole.setAttribute("r", HOLE); hole.setAttribute("class", "pie-hole");
            svg.appendChild(hole);
            wrap.appendChild(svg);

            segs.forEach(function (seg) {
                var li = document.createElement("li");
                li.innerHTML =
                    '<span class="lg-swatch" style="background:' + seg._color + '"></span>' +
                    '<span class="lg-label">' + seg.label + "</span>" +
                    '<span class="lg-value">' + fmtVal(seg.value) + " · " +
                    (seg.value / total * 100).toFixed(1) + "%</span>";
                legend.appendChild(li);
            });
            var legendItems = Array.prototype.slice.call(legend.children);

            function renderModal(seg) {
                var pct = (seg.value / total * 100).toFixed(1) + "%";
                var html =
                    '<button type="button" class="pm-close" aria-label="Close">&times;</button>' +
                    '<div class="pm-head"><span class="pm-title">' + seg.label + "</span>" +
                    '<span class="pm-sub">' + fmtVal(seg.value) + " · " + pct + "</span></div>";
                if (seg.model) html += '<p class="pm-model">' + seg.model + "</p>";
                var rows = (seg.breakdown || []).filter(function (b) { return b.value > 0; });
                if (rows.length) {
                    var max = rows.reduce(function (m, b) { return Math.max(m, b.value); }, 0) || 1;
                    html += '<ul class="pm-rows">';
                    rows.forEach(function (b) {
                        html += '<li class="pm-row">' +
                            '<span class="pm-k">' + b.label + "</span>" +
                            '<span class="pm-v">' + fmtVal(b.value) + " · " +
                            (b.value / seg.value * 100).toFixed(1) + "%</span>" +
                            '<span class="pm-bar"><span style="width:' +
                            (b.value / max * 100).toFixed(1) + "%;background:" + rowColor(chart, b, seg) +
                            '"></span></span></li>';
                    });
                    html += "</ul>";
                } else {
                    html += '<p class="pm-model">No further breakdown.</p>';
                }
                modal.innerHTML = html;
            }

            var activeIndex = null;

            // Desktop: stick the modal to the bottom-right of the cursor,
            // flipping back across the cursor near a viewport edge.
            function place(x, y) {
                var pad = 8, gap = 16;
                var mw = modal.offsetWidth, mh = modal.offsetHeight;
                var left = x + gap, top = y + gap;
                if (left + mw > window.innerWidth - pad) left = x - gap - mw;
                if (top + mh > window.innerHeight - pad) top = y - gap - mh;
                modal.style.left = Math.max(pad, left) + "px";
                modal.style.top = Math.max(pad, top) + "px";
            }

            function activate(i, x, y) {
                closeAll();                                   // only one modal open at a time
                activeIndex = i;
                var seg = segs[i];
                svg.classList.add("is-hovering");
                paths.forEach(function (p, j) {
                    if (j === i) {
                        p.classList.add("active");
                        p.style.transform = "translate(" + (seg._dx * EXPLODE).toFixed(2) + "px," +
                            (seg._dy * EXPLODE).toFixed(2) + "px)";
                    } else {
                        p.classList.remove("active");
                        p.style.transform = "";
                    }
                });
                legendItems.forEach(function (li, j) { li.classList.toggle("active", j === i); });
                renderModal(seg);
                modal.setAttribute("data-show", "1");
                if (mql.matches) {
                    backdrop.setAttribute("data-show", "1");  // mobile: dim + dismiss layer
                } else {
                    place(x, y);                              // desktop: follow the cursor
                }
            }

            function deactivate() {
                if (activeIndex === null) return;
                activeIndex = null;
                svg.classList.remove("is-hovering");
                paths.forEach(function (p) { p.classList.remove("active"); p.style.transform = ""; });
                legendItems.forEach(function (li) { li.classList.remove("active"); });
                modal.removeAttribute("data-show");
                modal.style.left = ""; modal.style.top = "";
                backdrop.removeAttribute("data-show");
            }
            instances.push(deactivate);

            // Desktop hover: open at the cursor, follow it, close on leave.
            svg.addEventListener("mouseover", function (e) {
                if (mql.matches) return;
                var idx = paths.indexOf(e.target);
                if (idx !== -1) activate(idx, e.clientX, e.clientY);
            });
            svg.addEventListener("mousemove", function (e) {
                if (!mql.matches && activeIndex !== null) place(e.clientX, e.clientY);
            });
            svg.addEventListener("mouseleave", function () {
                if (!mql.matches) deactivate();
            });

            // Mobile tap: toggle the centred modal; close button / backdrop dismiss.
            svg.addEventListener("click", function (e) {
                if (!mql.matches) return;
                var idx = paths.indexOf(e.target);
                if (idx === -1) return;
                if (activeIndex === idx) deactivate(); else activate(idx);
            });
            modal.addEventListener("click", function (e) {
                if (e.target.closest && e.target.closest(".pm-close")) deactivate();
            });
        });

        mql.addEventListener("change", closeAll); // reset cleanly when crossing the breakpoint
    })();

    // --- Reveal bars from zero on load (skip if reduced motion) --------
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
