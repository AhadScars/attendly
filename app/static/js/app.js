(() => {
  const flash = (el, ok, message) => {
    if (!el) return;
    el.className = "tap-box " + (ok ? "success" : "fail");
    const title = el.querySelector("[data-title]");
    const body = el.querySelector("[data-body]");
    if (title) title.textContent = ok ? "Tap recorded" : "Not recorded";
    if (body) body.textContent = message;
  };

  const form = document.getElementById("gate-form");
  if (form) {
    const box = document.getElementById("tap-status");
    const input = form.querySelector("[name=query]");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const direction = form.querySelector("[name=direction], [name=action]");
      const payload = {
        query: input.value,
        action: direction ? direction.value : "auto",
      };
      const url = form.getAttribute("action") || "/school/gate/tap";
      try {
        const res = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "fetch",
          },
          body: JSON.stringify(payload),
        });
        const data = await res.json().catch(() => ({
          ok: false,
          message: "Server did not reply correctly. Refresh and try again.",
        }));
        flash(box, data.ok, data.message || "");
        if (data.ok) {
          input.value = "";
          input.focus();
          if (data.taps) renderTaps(data.taps);
        }
      } catch (err) {
        flash(box, false, "Could not reach the school server. Is Attendly still running?");
      }
    });
    input && input.focus();
  }

  function renderTaps(taps) {
    const list = document.getElementById("tap-list");
    if (!list) return;
    list.innerHTML = taps
      .map((t) => {
        const when = t.time_out_display || t.time_in_display || "";
        const kind = t.time_out ? "Left" : "Arrived";
        return `<tr>
          <td><strong>${t.name}</strong><div class="hint">${t.class_name} · ${t.student_id}</div></td>
          <td><span class="pill present">${kind}</span></td>
          <td>${when}</td>
        </tr>`;
      })
      .join("");
  }

  document.querySelectorAll("[data-template]").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll("[data-template]").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      const title = document.querySelector("[name=title]");
      const body = document.querySelector("[name=body]");
      const key = document.querySelector("[name=template_key]");
      if (title) title.value = chip.dataset.title || "";
      if (body) body.value = chip.dataset.body || "";
      if (key) key.value = chip.dataset.template || "";
    });
  });

  document.querySelectorAll("[data-copy]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(btn.dataset.copy);
        btn.textContent = "Copied";
        setTimeout(() => (btn.textContent = "Copy"), 1200);
      } catch (_) {}
    });
  });

  document.querySelectorAll("form[data-confirm]").forEach((f) => {
    f.addEventListener("submit", (e) => {
      if (!confirm(f.dataset.confirm)) e.preventDefault();
    });
  });
})();
