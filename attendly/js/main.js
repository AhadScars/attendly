const toggle = document.getElementById("navToggle");
const menu = document.getElementById("navLinks");
const form = document.getElementById("demoForm");
const formOk = document.getElementById("formOk");
const year = document.getElementById("year");

if (year) year.textContent = String(new Date().getFullYear());

toggle?.addEventListener("click", () => {
  const open = toggle.getAttribute("aria-expanded") === "true";
  toggle.setAttribute("aria-expanded", String(!open));
  toggle.setAttribute("aria-label", open ? "Menu" : "Close menu");
  menu?.classList.toggle("open", !open);
});

menu?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => {
    toggle?.setAttribute("aria-expanded", "false");
    toggle?.setAttribute("aria-label", "Menu");
    menu.classList.remove("open");
  });
});

form?.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }
  const product = form.querySelector('[name="product"]');
  form.reset();
  if (product) product.value = product.defaultValue;
  if (formOk) formOk.hidden = false;
});

const pin = document.getElementById("busPin");
const path = document.getElementById("routePath");
if (pin && path && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  const length = path.getTotalLength();
  let t = 0.28;
  const tick = () => {
    t += 0.00055;
    if (t > 0.92) t = 0.22;
    const pt = path.getPointAtLength(length * t);
    const box = path.closest("svg").viewBox.baseVal;
    pin.style.left = `${(pt.x / box.width) * 100}%`;
    pin.style.top = `${(pt.y / box.height) * 100}%`;
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}
