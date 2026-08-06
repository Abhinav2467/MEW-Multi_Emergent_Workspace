document.addEventListener("DOMContentLoaded", () => {
  const statusEl = document.getElementById("backend-status");
  const userInfoEl = document.getElementById("user-info");
  const cacheInfoEl = document.getElementById("cache-info");
  const syncCacheBtn = document.getElementById("sync-cache-btn");
  const keyInput = document.getElementById("api-key-input");
  const saveBtn = document.getElementById("save-key-btn");
  const triggerBtn = document.getElementById("trigger-autofill-btn");

  chrome.storage.local.get(["mewApiKey"], async (data) => {
    if (data.mewApiKey) {
      keyInput.value = data.mewApiKey;
      checkHealth(data.mewApiKey);
    } else {
      checkHealth(null);
    }
  });

  function renderCacheInfo() {
    chrome.storage.local.get(["mewCachedProfile", "mewCachedAt"], (data) => {
      if (!data.mewCachedProfile) {
        cacheInfoEl.innerHTML = `<i>No candidate data cached in browser memory yet. Click 'Sync Memory Cache Now' or upload a resume.</i>`;
        return;
      }
      const prof = data.mewCachedProfile;
      const p = prof.personal || prof;
      const pro = prof.professional || prof;
      const timeStr = data.mewCachedAt ? new Date(data.mewCachedAt).toLocaleTimeString() : "Just now";

      const name = p.full_name || `${p.first_name || ""} ${p.last_name || ""}`.trim() || "N/A";
      const email = p.email || "N/A";
      const phone = p.phone || "N/A";
      const location = p.location || "N/A";
      const linkedin = p.linkedin_url || p.linkedin || "N/A";
      const github = p.github_url || p.github || "N/A";
      const skills = Array.isArray(pro.primary_skills) ? pro.primary_skills.join(", ") : (pro.primary_skills || "N/A");
      const resumeFile = prof.resume_file_path ? prof.resume_file_path.split("/").pop() : "Available (API Download)";

      cacheInfoEl.innerHTML = `
        <b>Name:</b> ${name}<br>
        <b>Email:</b> ${email}<br>
        <b>Phone:</b> ${phone}<br>
        <b>Location:</b> ${location}<br>
        <b>LinkedIn:</b> ${linkedin}<br>
        <b>GitHub:</b> ${github}<br>
        <b>Skills:</b> ${skills}<br>
        <b>Resume File:</b> ${resumeFile}<br>
        <small style="color: #4ade80;">Cached in Browser Memory (${timeStr})</small>
      `;
    });
  }

  renderCacheInfo();

  async function checkHealth(key) {
    try {
      const headers = key ? { "X-MEW-Api-Key": key } : {};
      const url = key ? "http://localhost:8000/api/v1/profile" : "http://localhost:8000/autofill/preview";
      const res = await fetch(url, { headers });
      if (res.ok) {
        const json = await res.json();
        statusEl.className = "status-online";
        statusEl.textContent = "Online 🟢";
        const name = json.data?.personal?.full_name || json.data?.active_profile?.personal?.full_name || "Candidate Profile Loaded";
        userInfoEl.textContent = `Candidate: ${name}`;

        // Auto sync into browser cache memory
        const profileData = json.data?.active_profile || json.data;
        if (profileData) {
          chrome.storage.local.set({
            mewCachedProfile: profileData,
            mewCachedAt: new Date().toISOString()
          }, () => {
            renderCacheInfo();
          });
        }
      } else {
        statusEl.className = "status-offline";
        statusEl.textContent = "Unauthorized (401)";
      }
    } catch (e) {
      statusEl.className = "status-offline";
      statusEl.textContent = "Offline 🔴 (Start Server)";
    }
  }

  syncCacheBtn.addEventListener("click", () => {
    chrome.runtime.sendMessage({ type: "FETCH_MEW_PAYLOAD" }, (res) => {
      if (res && res.status === "success") {
        renderCacheInfo();
        alert("Browser Memory Cache successfully synchronized!");
      } else {
        alert("Failed to sync memory cache. Make sure backend server is running on port 8000.");
      }
    });
  });

  saveBtn.addEventListener("click", () => {
    const key = keyInput.value.trim();
    chrome.storage.local.set({ mewApiKey: key }, () => {
      alert("API Key saved to Chrome Extension Storage!");
      checkHealth(key);
    });
  });

  triggerBtn.addEventListener("click", () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.scripting.executeScript({
          target: { tabId: tabs[0].id },
          func: () => {
            const badge = document.getElementById("mew-autofill-badge");
            if (badge) badge.click();
          }
        });
      }
    });
  });
});
