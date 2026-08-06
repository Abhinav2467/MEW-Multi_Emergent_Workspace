(function () {
  if (document.getElementById("mew-autofill-badge")) {
    const existing = document.getElementById("mew-autofill-badge");
    existing.click();
    return;
  }

  const style = document.createElement("style");
  style.textContent = `
    #mew-autofill-badge {
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 999999;
      background: #0f172a;
      color: #38bdf8;
      border: 1px solid #38bdf8;
      padding: 10px 18px;
      border-radius: 30px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 13px;
      font-weight: 600;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s ease-in-out;
      user-select: none;
    }
    #mew-autofill-badge:hover {
      background: #38bdf8;
      color: #0f172a;
      transform: translateY(-2px);
      box-shadow: 0 12px 28px rgba(56, 189, 248, 0.4);
    }
    #mew-autofill-badge.mew-success {
      border-color: #4ade80;
      color: #4ade80;
    }
  `;
  document.head.appendChild(style);

  const badge = document.createElement("div");
  badge.id = "mew-autofill-badge";
  badge.innerHTML = `✨ MEW Autofill`;
  document.body.appendChild(badge);

  function fillAndDispatch(el, val) {
    if (!el || val === undefined || val === null || val === "") return;
    el.focus();
    el.value = val;
    ["focus", "input", "change", "blur"].forEach((evtType) => {
      el.dispatchEvent(new Event(evtType, { bubbles: true, cancelable: true }));
    });
  }

  function findSubmitOrNextButton() {
    const candidates = Array.from(document.querySelectorAll("button, input[type='submit'], a.btn, div[role='button']"));
    for (const btn of candidates) {
      const txt = (btn.innerText || btn.value || "").trim().toLowerCase();
      if (txt.includes("submit") || txt.includes("next") || txt.includes("continue") || txt.includes("apply now") || txt.includes("review")) {
        return btn;
      }
    }
    return null;
  }

  async function logApplicationToBackend(companyName, jobTitle) {
    const bases = ["http://127.0.0.1:8000", "http://localhost:8000"];
    for (const base of bases) {
      try {
        await fetch(`${base}/api/v1/applications/log`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            company: companyName || document.title.split("-")[0] || "Career Portal",
            job_title: jobTitle || document.title || "Job Application",
            url: window.location.href,
            status: "Submitted"
          })
        });
        break;
      } catch (e) {}
    }
  }

  badge.addEventListener("click", async () => {
    badge.innerHTML = `⏳ AI Matching Form...`;

    const domFields = [];
    document.querySelectorAll("input, textarea, select").forEach((el, index) => {
      if (el.type === "hidden" || el.type === "submit" || el.type === "button") return;
      const elementId = el.id || el.name || `mew-field-${index}`;
      if (!el.id && !el.name) el.id = elementId;

      const labelEl = document.querySelector(`label[for='${el.id}']`) || el.closest("label");
      const labelText = labelEl ? labelEl.innerText.trim() : (el.placeholder || el.name || el.ariaLabel || "");

      domFields.push({
        element_id: elementId,
        label: labelText || elementId,
        placeholder: el.placeholder || "",
        tag_name: el.tagName.toLowerCase(),
        input_type: el.type || "text",
        autocomplete: el.autocomplete || ""
      });
    });

    let filledCount = 0;
    const filledElements = new Set();
    const bases = ["http://127.0.0.1:8000", "http://localhost:8000"];
    let matchData = null;

    for (const base of bases) {
      try {
        const res = await fetch(`${base}/api/v1/autofill-payload/match`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ fields: domFields.slice(0, 25) })
        });
        if (res.ok) {
          const json = await res.json();
          matchData = json.data?.matches || [];
          break;
        }
      } catch (e) {}
    }

    if (matchData && matchData.length > 0) {
      matchData.forEach(m => {
        const el = document.getElementById(m.element_id) || document.querySelector(`[name='${m.element_id}']`);
        if (el && m.value && m.confidence >= 0.5 && !filledElements.has(el)) {
          fillAndDispatch(el, m.value);
          filledElements.add(el);
          filledCount++;
        }
      });
    }

    const targetBtn = findSubmitOrNextButton();
    if (targetBtn) {
      targetBtn.style.boxShadow = "0 0 15px #38bdf8";
      targetBtn.style.border = "2px solid #38bdf8";
      targetBtn.style.transition = "all 0.3s ease-in-out";
      targetBtn.addEventListener("click", () => {
        logApplicationToBackend();
      }, { once: true });
    }

    badge.classList.add("mew-success");
    badge.innerHTML = `✅ ${filledCount} Fields AI-Filled`;
    setTimeout(() => {
      badge.classList.remove("mew-success");
      badge.innerHTML = `✨ MEW Autofill`;
    }, 3000);
  });

  badge.click();
})();
