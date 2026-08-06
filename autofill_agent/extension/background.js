console.log("[MEW Extension] Background service worker initialized.");

async function safeFetch(endpointPath, options = {}) {
  const bases = ["http://127.0.0.1:8000", "http://localhost:8000"];
  let lastErr = null;

  for (const base of bases) {
    try {
      const fullUrl = `${base}${endpointPath}`;
      const res = await fetch(fullUrl, {
        ...options,
        mode: "cors"
      });
      return res;
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr || new Error("Failed to connect to MEW backend on 127.0.0.1:8000 or localhost:8000");
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "MEW_AUTH_SYNC" && message.apiKey) {
    chrome.storage.local.set({ mewApiKey: message.apiKey }, () => {
      console.log("[MEW Extension] API Key auto-synced successfully:", message.apiKey);
      sendResponse({ status: "success", syncedKey: message.apiKey });
    });
    return true;
  }
  
  if (message.type === "GET_MEW_STATUS") {
    chrome.storage.local.get(["mewApiKey"], (data) => {
      sendResponse({ apiKey: data.mewApiKey || null });
    });
    return true;
  }

  if (message.type === "FETCH_MEW_PAYLOAD") {
    chrome.storage.local.get(["mewApiKey"], async (stored) => {
      const apiKey = stored.mewApiKey || "";
      let headers = apiKey ? { "X-MEW-Api-Key": apiKey } : {};
      let path = apiKey ? "/api/v1/autofill-payload" : "/autofill/preview";
      
      try {
        let res = await safeFetch(path, { headers });
        if (res.status === 401 && apiKey) {
          path = "/autofill/preview";
          res = await safeFetch(path);
        }
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        const json = await res.json();
        const profileData = json.data?.active_profile || json.data;

        // Store into Browser Cache Memory
        chrome.storage.local.set({
          mewCachedProfile: profileData,
          mewCachedAt: new Date().toISOString()
        });

        sendResponse({ status: "success", data: profileData, apiKey });
      } catch (err) {
        console.error("[MEW Background] Fetch payload error:", err);
        // Fallback to cached profile if network fails
        chrome.storage.local.get(["mewCachedProfile"], (cached) => {
          if (cached.mewCachedProfile) {
            sendResponse({ status: "success", data: cached.mewCachedProfile, fromCache: true });
          } else {
            sendResponse({ status: "error", error: err.toString() });
          }
        });
      }
    });
    return true;
  }

  if (message.type === "GET_CACHED_PROFILE") {
    chrome.storage.local.get(["mewCachedProfile", "mewCachedAt"], (cached) => {
      sendResponse({
        status: "success",
        profile: cached.mewCachedProfile || null,
        cachedAt: cached.mewCachedAt || null
      });
    });
    return true;
  }

  if (message.type === "SYNC_PROFILE_CACHE" && message.profile) {
    chrome.storage.local.set({
      mewCachedProfile: message.profile,
      mewCachedAt: new Date().toISOString()
    }, () => {
      console.log("[MEW Extension] Browser memory cache synced with profile:", message.profile);
      sendResponse({ status: "success" });
    });
    return true;
  }

  if (message.type === "MATCH_MEW_FIELDS") {
    chrome.storage.local.get(["mewApiKey"], async (stored) => {
      const apiKey = stored.mewApiKey || "";
      if (!message.fields || message.fields.length === 0) {
        sendResponse({ status: "skipped" });
        return;
      }
      try {
        const headers = { "Content-Type": "application/json" };
        if (apiKey) {
          headers["X-MEW-Api-Key"] = apiKey;
        }
        let res = await safeFetch("/api/v1/autofill-payload/match", {
          method: "POST",
          headers: headers,
          body: JSON.stringify({ fields: message.fields })
        });
        if (res.status === 401) {
          res = await safeFetch("/api/v1/autofill-payload/match", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ fields: message.fields })
          });
        }
        const json = await res.json();
        sendResponse(json);
      } catch (err) {
        console.error("[MEW Background] Match error:", err);
        sendResponse({ status: "error", error: err.toString() });
      }
    });
    return true;
  }
  if (message.type === "FETCH_RESUME_BLOB") {
    // Fetch resume PDF from the local backend using extension's trusted context (no CORS restriction)
    (async () => {
      const bases = ["http://127.0.0.1:8000", "http://localhost:8000"];
      for (const base of bases) {
        try {
          const res = await fetch(`${base}/api/v1/resume/download-latest`);
          if (res.ok) {
            const contentDisposition = res.headers.get("Content-Disposition") || "";
            let filename = "Resume.pdf";
            if (contentDisposition.includes("filename=")) {
              filename = contentDisposition.split("filename=")[1].replace(/["']/g, "").trim();
            }
            const blob = await res.blob();
            // Convert blob to base64 data URL via FileReader
            const reader = new FileReaderSync ? new FileReaderSync() : await new Promise((resolve) => {
              const fr = new FileReader();
              fr.onloadend = () => resolve({ result: fr.result });
              fr.readAsDataURL(blob);
            });
            // Service workers don't have FileReader, so use arrayBuffer → base64
            const arrayBuffer = await blob.arrayBuffer();
            const uint8Array = new Uint8Array(arrayBuffer);
            let binary = '';
            for (let i = 0; i < uint8Array.byteLength; i++) {
              binary += String.fromCharCode(uint8Array[i]);
            }
            const base64 = btoa(binary);
            const mimeType = blob.type || "application/pdf";
            const dataUrl = `data:${mimeType};base64,${base64}`;
            sendResponse({ status: "success", dataUrl, filename, mimeType });
            return;
          }
        } catch (err) {
          console.warn("[MEW Background] Resume fetch attempt failed:", err);
        }
      }
      sendResponse({ status: "error", error: "Could not fetch resume from backend" });
    })();
    return true; // Keep message channel open for async response
  }
});
