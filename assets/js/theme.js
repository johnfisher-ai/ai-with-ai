/* Light and dark themes. A page follows the device setting until the reader uses the switch in the
   top bar, and the choice is remembered in this browser. Loaded in <head>, before the page is drawn,
   so a dark page never flashes light. theme.css holds the colors. */
(function () {
  var KEY = "vb-theme", root = document.documentElement;
  var media = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  var choice = null;
  try { choice = localStorage.getItem(KEY); } catch (e) { /* storage blocked: follow the device */ }
  function device() { return media && media.matches ? "dark" : "light"; }
  function current() { return choice === "dark" || choice === "light" ? choice : device(); }
  function show() {
    var t = current();
    root.setAttribute("data-theme", t);
    var b = document.getElementById("theme-toggle");
    if (b) b.setAttribute("aria-pressed", t === "dark" ? "true" : "false");
  }
  show();
  if (media && media.addEventListener) media.addEventListener("change", show);

  document.addEventListener("DOMContentLoaded", function () {
    var bar = document.querySelector(".topnav .nav-links");
    if (!bar) return;
    var b = document.createElement("button");
    b.type = "button";
    b.id = "theme-toggle";
    b.className = "theme-toggle";
    b.setAttribute("aria-label", "Dark theme");
    b.title = "Dark theme";
    b.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
      '<circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" stroke-width="2"/>' +
      '<path d="M12 3.5a8.5 8.5 0 0 1 0 17z" fill="currentColor"/></svg>';
    b.addEventListener("click", function () {
      var next = current() === "dark" ? "light" : "dark";
      // a choice that matches the device is forgotten, so the page follows the device again
      choice = next === device() ? null : next;
      try {
        if (choice) localStorage.setItem(KEY, choice); else localStorage.removeItem(KEY);
      } catch (e) { /* storage blocked: the choice lasts for this page */ }
      show();
    });
    bar.appendChild(b);
    show();
  });
})();
