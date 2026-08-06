(function () {
  const isTopWindow = window.self === window.top;
  const elementMap = new Map();
  let cachedResumeFile = null;
  let cachedResumeDataUrl = null;

  // Render main badge and PERMANENT floating drag pill only on top-level window
  if (isTopWindow && !document.getElementById("mew-autofill-badge")) {
    const badge = document.createElement("div");
    badge.id = "mew-autofill-badge";
    badge.innerHTML = `✨ MEW Autofill`;
    document.body.appendChild(badge);

    badge.addEventListener("click", () => {
      triggerAutofillProcess();
      broadcastAutofillToIframes();
    });

    createPermanentResumePill();
  }

  function broadcastAutofillToIframes() {
    const iframes = document.querySelectorAll("iframe");
    iframes.forEach(iframe => {
      try {
        iframe.contentWindow.postMessage({
          type: "MEW_TRIGGER_AUTOFILL",
          resumeDataUrl: cachedResumeDataUrl,
          filename: cachedResumeFile ? cachedResumeFile.name : "Resume.pdf"
        }, "*");
      } catch(e){}
    });
  }

  let isDraggingMewPill = false;

  // Create permanent floating drag/click resume pill immediately on page load
  function createPermanentResumePill() {
    if (document.getElementById("mew-resume-pill")) return;

    const pill = document.createElement("div");
    pill.id = "mew-resume-pill";
    pill.draggable = true;
    pill.innerHTML = `📄 Drag / Attach Resume PDF`;
    pill.title = "Drag this badge onto any 'Choose File' button or click it to attach resume PDF";

    pill.addEventListener("dragstart", (evt) => {
      isDraggingMewPill = true;
      evt.dataTransfer.effectAllowed = "copy";
      evt.dataTransfer.setData("text/plain", "MEW_RESUME_PDF");
      evt.dataTransfer.setData("application/x-mew-resume", "true");
      if (cachedResumeFile) {
        try {
          evt.dataTransfer.items.add(cachedResumeFile);
        } catch (e) {}
      }
      pill.style.opacity = "0.5";
    });

    pill.addEventListener("dragend", () => {
      isDraggingMewPill = false;
      pill.style.opacity = "1";
    });

    pill.addEventListener("click", async () => {
      pill.innerHTML = `⏳ Attaching Resume...`;
      broadcastAutofillToIframes();
      const count = await autofillResumeFileInputs();
      const filenameStr = cachedResumeFile ? ` (${cachedResumeFile.name})` : "";
      if (count > 0) {
        pill.innerHTML = `✅ Attached Resume PDF${filenameStr}`;
      } else {
        pill.innerHTML = `📄 Drag / Attach Resume PDF${filenameStr}`;
      }
      setTimeout(() => {
        pill.innerHTML = `📄 Drag / Attach Resume PDF${filenameStr}`;
      }, 3000);
    });

    document.body.appendChild(pill);
  }

  // Helper: find the best drop target element near a point or element
  function findDropTargetNear(el) {
    if (!el || el.nodeType !== 1) return null;
    if (el.tagName === "INPUT" && el.type === "file") return el.parentElement || el;
    const nearestInput = el.querySelector("input[type='file']") ||
      el.closest("form, section, [class*='drop'], [class*='upload'], [class*='file']")?.querySelector("input[type='file']") ||
      document.querySelector("input[type='file']");
    if (nearestInput) return nearestInput.parentElement || nearestInput;
    return el.closest("[class*='drop'], [class*='upload'], [class*='file']") || el;
  }

  let lastHighlightedDropTarget = null;

  function highlightDropTarget(el) {
    clearDropHighlight();
    const t = findDropTargetNear(el);
    if (t && t !== document.body && t !== document.documentElement) {
      t.classList.add("mew-drop-target");
      lastHighlightedDropTarget = t;
    }
  }

  function clearDropHighlight() {
    if (lastHighlightedDropTarget) {
      lastHighlightedDropTarget.classList.remove("mew-drop-target");
      lastHighlightedDropTarget = null;
    }
    document.querySelectorAll(".mew-drop-target").forEach(el => el.classList.remove("mew-drop-target"));
  }

  // Global Page-Wide Dragover & Drop Interceptors for 100% Reliable Drop-to-Autofill
  window.addEventListener("dragover", (evt) => {
    if (isDraggingMewPill) {
      evt.preventDefault();
      evt.dataTransfer.dropEffect = "copy";
      highlightDropTarget(evt.target);
    }
  }, true);

  window.addEventListener("dragenter", (evt) => {
    if (isDraggingMewPill) {
      evt.preventDefault();
      highlightDropTarget(evt.target);
    }
  }, true);

  window.addEventListener("dragleave", (evt) => {
    if (isDraggingMewPill && evt.target === lastHighlightedDropTarget) {
      // only clear if leaving the highlighted element, not its children
      const rel = evt.relatedTarget;
      if (!rel || !lastHighlightedDropTarget.contains(rel)) {
        clearDropHighlight();
      }
    }
  }, true);

  window.addEventListener("drop", async (evt) => {
    const isMewDrag = isDraggingMewPill || (
      evt.dataTransfer && (
        evt.dataTransfer.getData("text/plain") === "MEW_RESUME_PDF" ||
        evt.dataTransfer.getData("application/x-mew-resume") === "true"
      )
    );

    if (!isMewDrag) return;

    evt.preventDefault();
    evt.stopPropagation();
    isDraggingMewPill = false;
    clearDropHighlight();

    const pill = document.getElementById("mew-resume-pill");
    if (pill) pill.style.opacity = "1";

    if (!cachedResumeFile) {
      await initResumeFile();
    }

    if (!cachedResumeFile) {
      console.warn("[MEW Extension] No cached resume PDF file available to attach.");
      return;
    }

    const targetEl = evt.target || document.elementFromPoint(evt.clientX, evt.clientY);
    attachFileToTargetOrDocument(targetEl, cachedResumeFile);

    const nameStr = cachedResumeFile ? ` (${cachedResumeFile.name})` : "";
    if (pill) {
      pill.innerHTML = `✅ Attached Resume PDF${nameStr}`;
      setTimeout(() => {
        pill.innerHTML = `📄 Drag / Attach Resume PDF${nameStr}`;
      }, 3000);
    }

    triggerAutofillProcess();
  }, true);

  // Pre-fetch candidate resume PDF file — routes through background service worker to bypass CORS
  async function initResumeFile() {
    // Strategy 1: Ask background service worker to fetch (runs in extension context, no CORS)
    if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.sendMessage) {
      try {
        await new Promise((resolve) => {
          chrome.runtime.sendMessage({ type: "FETCH_RESUME_BLOB" }, (response) => {
            if (chrome.runtime.lastError) {
              console.warn("[MEW Extension] Background fetch error:", chrome.runtime.lastError.message);
              resolve(false);
              return;
            }
            if (response && response.status === "success" && response.dataUrl) {
              const mimeType = response.mimeType || "application/pdf";
              const filename = response.filename || "Resume.pdf";
              // Convert base64 data URL back to File object
              fetch(response.dataUrl)
                .then(r => r.blob())
                .then(blob => {
                  cachedResumeFile = new File([blob], filename, { type: mimeType });
                  cachedResumeDataUrl = response.dataUrl;
                  const pill = document.getElementById("mew-resume-pill");
                  if (pill) pill.innerHTML = `📄 Drag / Attach Resume PDF (${filename})`;
                })
                .catch(e => console.warn("[MEW Extension] Blob reconstruction failed:", e));
              resolve(true);
            } else {
              console.warn("[MEW Extension] Background fetch returned error:", response?.error);
              resolve(false);
            }
          });
        });
        if (cachedResumeFile) return; // Successfully loaded via background worker
      } catch (e) {
        console.warn("[MEW Extension] Background worker unavailable, trying direct fetch:", e);
      }
    }

    // Strategy 2: Direct fetch fallback (works after CORS fix in backend/main.py)
    try {
      const bases = ["http://127.0.0.1:8000", "http://localhost:8000"];
      for (const base of bases) {
        try {
          const res = await fetch(`${base}/api/v1/resume/download-latest`, { mode: "cors" });
          if (res.ok) {
            const blob = await res.blob();
            let filename = "Resume.pdf";
            const disposition = res.headers.get("Content-Disposition");
            if (disposition && disposition.includes("filename=")) {
              filename = disposition.split("filename=")[1].replace(/["']/g, "").trim();
            }
            cachedResumeFile = new File([blob], filename, { type: blob.type || "application/pdf" });

            const reader = new FileReader();
            reader.onloadend = () => {
              cachedResumeDataUrl = reader.result;
            };
            reader.readAsDataURL(blob);

            const pill = document.getElementById("mew-resume-pill");
            if (pill) pill.innerHTML = `📄 Drag / Attach Resume PDF (${filename})`;
            return;
          }
        } catch (e) {
          console.warn("[MEW Extension] Direct fetch failed for", base, e);
        }
      }
    } catch (err) {
      console.warn("[MEW Extension] Failed to pre-fetch candidate resume PDF:", err);
    }
  }

  initResumeFile();

  // Listen for window postMessages (Auth sync, Profile cache sync, or iframe trigger)
  window.addEventListener("message", (event) => {
    if (!event.data) return;

    if (event.data.type === "MEW_AUTH_SYNC" && event.data.apiKey) {
      try {
        if (chrome.runtime?.id) {
          chrome.runtime.sendMessage({ type: "MEW_AUTH_SYNC", apiKey: event.data.apiKey });
        }
      } catch (e) {}
    }

    if (event.data.type === "MEW_PROFILE_SYNC" && event.data.profile) {
      try {
        if (chrome.runtime?.id) {
          chrome.runtime.sendMessage({ type: "SYNC_PROFILE_CACHE", profile: event.data.profile });
        }
      } catch (e) {}
    }

    if (event.data.type === "MEW_TRIGGER_AUTOFILL") {
      if (event.data.resumeDataUrl && (!cachedResumeFile || !isTopWindow)) {
        fetch(event.data.resumeDataUrl)
          .then(res => res.blob())
          .then(blob => {
            cachedResumeFile = new File([blob], event.data.filename || "Resume.pdf", { type: blob.type || "application/pdf" });
            autofillResumeFileInputs();
          })
          .catch(e => console.warn("Failed to reconstruct blob in iframe:", e));
      }
      triggerAutofillProcess();
    }
  });

  function fillAndDispatch(el, val) {
    if (!el || val === undefined || val === null || val === "") return;
    el.focus();

    let targetValue = String(val);
    const isPhoneField = el.id?.toLowerCase().includes("phone") ||
                         el.name?.toLowerCase().includes("phone") ||
                         el.placeholder?.toLowerCase().includes("phone") ||
                         el.type === "tel";

    if (el.type === "number" || el.getAttribute("inputmode") === "numeric" || el.getAttribute("type") === "number") {
      targetValue = targetValue.replace(/\D/g, "");
      // Remove country code 91 prefix if present for 10-digit national number fields (e.g., 917892568001 -> 7892568001)
      if (targetValue.length === 12 && targetValue.startsWith("91")) {
        targetValue = targetValue.slice(2);
      }
    } else if (isPhoneField) {
      let digits = targetValue.replace(/\D/g, "");
      if (digits.length === 12 && digits.startsWith("91")) {
        targetValue = digits.slice(2);
      }
    }

    el.value = targetValue;

    const isCombobox = el.getAttribute("role") === "combobox" ||
                       el.getAttribute("aria-autocomplete") ||
                       el.classList.contains("select2-search__field") ||
                       (el.id && el.id.toLowerCase().includes("location"));

    ["focus", "input", "change"].forEach((evtType) => {
      el.dispatchEvent(new Event(evtType, { bubbles: true, cancelable: true }));
    });

    if (isCombobox) {
      el.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", code: "ArrowDown", keyCode: 40, bubbles: true }));
      setTimeout(() => {
        const option = document.querySelector('[role="option"], .pac-container .pac-item, .select2-results__option--highlighted, .select2-results__option');
        if (option) {
          option.click();
        } else {
          el.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", code: "Enter", keyCode: 13, bubbles: true }));
        }
        el.dispatchEvent(new Event("blur", { bubbles: true, cancelable: true }));
      }, 150);
    } else {
      el.dispatchEvent(new Event("blur", { bubbles: true, cancelable: true }));
    }
  }

  // Client-side local browser cache matching fallback with enhanced Phone and Location detection
  function matchFieldsLocally(domFields, cachedProfile) {
    if (!cachedProfile) return [];
    const p = cachedProfile.personal || cachedProfile;
    const prof = cachedProfile.professional || cachedProfile;
    const qa = cachedProfile.custom_qa || {};

    const matches = [];
    for (const field of domFields) {
      const labelLower = (field.label || "").toLowerCase();
      const placeholderLower = (field.placeholder || "").toLowerCase();
      const elemIdLower = (field.element_id || "").toLowerCase();
      const inputTypeLower = (field.input_type || "").toLowerCase();
      const combined = `${labelLower} ${placeholderLower} ${elemIdLower} ${inputTypeLower}`;

      let val = "";
      let matchedKey = "unknown";

      if (["first_name", "first name", "firstname", "fname", "given-name"].some(k => combined.includes(k))) {
        val = p.first_name || (p.full_name ? p.full_name.split(" ")[0] : "");
        matchedKey = "personal.first_name";
      } else if (["last_name", "last name", "lastname", "lname", "family-name"].some(k => combined.includes(k))) {
        val = p.last_name || (p.full_name ? p.full_name.split(" ").slice(1).join(" ") : "");
        matchedKey = "personal.last_name";
      } else if (["full_name", "full name", "fullname", "your name"].some(k => combined.includes(k))) {
        val = p.full_name || `${p.first_name || ""} ${p.last_name || ""}`.trim();
        matchedKey = "personal.full_name";
      } else if (["email", "e-mail"].some(k => combined.includes(k))) {
        val = p.email || "";
        matchedKey = "personal.email";
      } else if (inputTypeLower === "tel" || inputTypeLower === "number" || labelLower === "phone" || placeholderLower === "phone" || ["phone", "mobile", "cell", "telephone", "contact"].some(k => combined.includes(k))) {
        val = p.phone || "";
        matchedKey = "personal.phone";
      } else if (combined.includes("linkedin")) {
        val = p.linkedin_url || p.linkedin || "";
        matchedKey = "personal.linkedin_url";
      } else if (combined.includes("github")) {
        val = p.github_url || p.github || "";
        matchedKey = "personal.github_url";
      } else if (["portfolio", "website"].some(k => combined.includes(k))) {
        val = p.portfolio_url || p.portfolio || "";
        matchedKey = "personal.portfolio_url";
      } else if (["location", "city", "address", "state", "residence"].some(k => combined.includes(k))) {
        val = p.location || "";
        matchedKey = "personal.location";
      } else if (["title", "headline", "position", "role"].some(k => combined.includes(k))) {
        val = prof.current_title || "";
        matchedKey = "professional.current_title";
      } else if (["skill", "technolog"].some(k => combined.includes(k))) {
        const skills = prof.primary_skills || prof.skills || [];
        val = Array.isArray(skills) ? skills.join(", ") : String(skills);
        matchedKey = "professional.primary_skills";
      } else if (["experience", "years"].some(k => combined.includes(k))) {
        val = String(prof.years_experience || 0);
        matchedKey = "professional.years_experience";
      } else if (combined.includes("relocate")) {
        val = qa.willing_to_relocate || "Yes";
        matchedKey = "custom_qa.willing_to_relocate";
      }

      if (val) {
        matches.push({ element_id: field.element_id, matched_key: matchedKey, value: val, confidence: 0.9 });
      }
    }
    return matches;
  }

  // Extract fields from current document and map direct DOM element references
  function extractFieldsFromCurrentDocument() {
    const fields = [];
    elementMap.clear();

    document.querySelectorAll("input, textarea, select, [role='combobox']").forEach((el, index) => {
      if (el.type === "hidden" || el.type === "submit" || el.type === "button" || el.type === "file") return;
      const elementId = el.id || el.name || `mew-field-${index}`;
      if (!el.id && !el.name) el.id = elementId;

      elementMap.set(elementId, el);

      const labelEl = document.querySelector(`label[for='${el.id}']`) || el.closest("label");
      const labelText = labelEl ? labelEl.innerText.trim() : (el.placeholder || el.name || el.getAttribute("aria-label") || "");

      fields.push({
        element_id: elementId,
        label: labelText || elementId,
        placeholder: el.placeholder || "",
        tag_name: el.tagName.toLowerCase(),
        input_type: el.type || "text",
        autocomplete: el.autocomplete || ""
      });
    });

    return fields;
  }

  // Targeted File & Dropzone Injection Handler (Works on Rippling, Greenhouse, Lever, Workday, etc.)
  function attachFileToTargetOrDocument(targetEl, file) {
    if (!file) return false;

    const dt = new DataTransfer();
    dt.items.add(file);

    let fileInput = null;

    if (targetEl) {
      if (targetEl.tagName === "INPUT" && targetEl.type === "file") {
        fileInput = targetEl;
      } else {
        fileInput = targetEl.querySelector("input[type='file']") ||
                    targetEl.closest(".dropzone, [class*='drop'], [class*='upload'], [class*='file'], [class*='attach'], form, section, main, body")?.querySelector("input[type='file']");
      }
    }

    if (!fileInput) {
      fileInput = document.querySelector("input[type='file']");
    }

    let success = false;

    if (fileInput) {
      try {
        fileInput.files = dt.files;
        ["focus", "input", "change", "blur"].forEach(evtName => {
          fileInput.dispatchEvent(new Event(evtName, { bubbles: true, cancelable: true }));
        });
        success = true;
      } catch (e) {
        console.warn("[MEW Extension] Error setting fileInput.files:", e);
      }
    }

    // Synthesize 'drop' DragEvent for custom Dropzones (React-Dropzone, Dropzone.js, etc.)
    const dropTargets = [];
    if (targetEl && targetEl.nodeType === 1) dropTargets.push(targetEl);
    if (fileInput && fileInput.parentElement && !dropTargets.includes(fileInput.parentElement)) {
      dropTargets.push(fileInput.parentElement);
    }
    const closestDropzone = targetEl?.closest(".dropzone, [class*='drop'], [class*='upload'], [class*='file']");
    if (closestDropzone && !dropTargets.includes(closestDropzone)) {
      dropTargets.push(closestDropzone);
    }

    dropTargets.forEach(dropEl => {
      try {
        const dropEvt = new DragEvent("drop", {
          bubbles: true,
          cancelable: true,
          dataTransfer: dt
        });
        dropEl.dispatchEvent(dropEvt);
      } catch (e) {}
    });

    autofillResumeFileInputs();

    return success;
  }

  // Automated Synthetic DataTransfer file injection into input[type="file"]
  async function autofillResumeFileInputs() {
    const fileInputs = Array.from(document.querySelectorAll("input[type='file']"));

    if (!cachedResumeFile) {
      await initResumeFile();
    }

    if (!cachedResumeFile) return 0;

    let uploadedCount = 0;
    const dt = new DataTransfer();
    dt.items.add(cachedResumeFile);

    for (const input of fileInputs) {
      try {
        input.files = dt.files;
        ["focus", "input", "change", "blur"].forEach((evtType) => {
          input.dispatchEvent(new Event(evtType, { bubbles: true, cancelable: true }));
        });

        // Trigger synthetic drop on container for React-Dropzone
        const dropzoneParent = input.closest(".dropzone, [class*='drop'], [class*='upload']") || input.parentElement;
        if (dropzoneParent) {
          try {
            dropzoneParent.dispatchEvent(new DragEvent("drop", { bubbles: true, cancelable: true, dataTransfer: dt }));
          } catch(e){}
        }

        uploadedCount++;
      } catch(e){}
    }

    // If no file input found but there are dropzones on page, dispatch synthetic drop to them
    if (uploadedCount === 0) {
      const dropzones = document.querySelectorAll(".dropzone, [class*='drop'], [class*='upload']");
      dropzones.forEach(dz => {
        try {
          dz.dispatchEvent(new DragEvent("drop", { bubbles: true, cancelable: true, dataTransfer: dt }));
          uploadedCount++;
        } catch(e){}
      });
    }

    return uploadedCount;
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

  async function triggerAutofillProcess() {
    const badge = document.getElementById("mew-autofill-badge");
    if (badge) badge.innerHTML = `⏳ AI Matching Form...`;

    // 1. First autofill any Resume PDF file upload inputs on current document
    const fileCount = await autofillResumeFileInputs();

    // 2. Extract DOM form fields from current document & store direct element references
    const domFields = extractFieldsFromCurrentDocument();

    let filledCount = fileCount;
    const filledElements = new Set();

    const finishAutofill = (count) => {
      if (badge) {
        badge.classList.add("mew-success");
        badge.innerHTML = `✅ ${count} Fields AI-Filled`;
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

      if (badge) {
        setTimeout(() => {
          badge.classList.remove("mew-success");
          badge.innerHTML = `✨ MEW Autofill`;
        }, 3000);
      }
    };

    if (domFields.length > 0) {
      // Direct live fetch from backend to ensure Save & Sync Memory is immediately active
      const fetchLiveProfile = async () => {
        try {
          const res = await fetch("http://127.0.0.1:8000/api/v1/profile");
          if (res.ok) {
            const json = await res.json();
            if (json.data) return json.data;
          }
        } catch (e) {}
        return null;
      };

      fetchLiveProfile().then((liveProf) => {
        chrome.storage.local.get(["mewCachedProfile"], (cached) => {
          const profileToUse = liveProf || cached.mewCachedProfile;

          try {
            chrome.runtime.sendMessage({ type: "MATCH_MEW_FIELDS", fields: domFields }, (matchJson) => {
              let matches = (matchJson && matchJson.status === "success" && matchJson.data?.matches) ? matchJson.data.matches : [];

              if (matches.length === 0 && profileToUse) {
                matches = matchFieldsLocally(domFields, profileToUse);
              }

              matches.forEach(m => {
                const el = elementMap.get(m.element_id) || document.getElementById(m.element_id) || document.querySelector(`[name='${m.element_id}']`);
                if (el && m.value && m.confidence >= 0.5 && !filledElements.has(el)) {
                  fillAndDispatch(el, m.value);
                  filledElements.add(el);
                  filledCount++;
                }
              });

              finishAutofill(filledCount);
            });
          } catch (e) {
            console.error("[MEW Extension] Match exception:", e);
            const fallbackMatches = matchFieldsLocally(domFields, profileToUse);
            fallbackMatches.forEach(m => {
              const el = elementMap.get(m.element_id) || document.getElementById(m.element_id) || document.querySelector(`[name='${m.element_id}']`);
              if (el && m.value && !filledElements.has(el)) {
                fillAndDispatch(el, m.value);
                filledElements.add(el);
                filledCount++;
              }
            });
            finishAutofill(fileCount + fallbackMatches.length);
          }
        });
      });
    } else {
      finishAutofill(fileCount);
    }
  }
})();
