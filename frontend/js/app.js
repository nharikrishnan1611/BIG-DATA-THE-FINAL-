/**
 * AI Fake News Verification Dashboard - Frontend Logic
 * Differentiating Feature: Evidence & Source Verification with traceable links.
 */

// Sample quick test claims for rapid live evaluation
const SAMPLE_CLAIMS = {
  school_closure: "Government secretly announces that all public schools will remain closed for three months.",
  nasa_space: "NASA successfully completed optical deep space laser communications experiment from 19 million miles away.",
  garlic_cure: "URGENT: Drinking boiled garlic water completely immunizes against viral respiratory infections, doctors reveal!",
  bank_collapse: "Secret decree leaks revealing plans to replace national currency with mandatory global digital barcode.",
  who_guidelines: "The World Health Organization published updated clinical guidelines on the treatment of respiratory illnesses worldwide."
};

let currentInputMode = "text";
let ocrUsedFlag = false;
let ocrConfidenceScore = null;
let currentSourceUrl = "";

document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  initInputModes();
  initSampleChips();
  initUrlScraper();
  initImageOcr();
  initVerifyButton();
  initHistoryTab();
  initBigDataTab();

  // Load initial demo verification result
  runInitialDemoVerification();
});

// =============================================================================
// Top Navigation Tab Switching
// =============================================================================
function initNavigation() {
  const navBtns = document.querySelectorAll(".nav-btn");
  const tabPanes = document.querySelectorAll(".tab-pane");

  navBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      navBtns.forEach(b => b.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const targetTabId = btn.getAttribute("data-tab");
      const targetPane = document.getElementById(targetTabId);
      if (targetPane) {
        targetPane.classList.add("active");
      }

      if (targetTabId === "tab-history") {
        loadHistoryList();
      } else if (targetTabId === "tab-bigdata") {
        loadBigDataStats();
      }
    });
  });
}

// =============================================================================
// Input Mode Switching (Text / URL / Image)
// =============================================================================
function initInputModes() {
  const modeBtns = document.querySelectorAll(".input-tab-btn");
  const textBox = document.getElementById("mode-text-box");
  const urlBox = document.getElementById("mode-url-box");
  const imageBox = document.getElementById("mode-image-box");

  modeBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      modeBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      currentInputMode = btn.getAttribute("data-mode");
      textBox.style.display = currentInputMode === "text" ? "block" : "none";
      urlBox.style.display = currentInputMode === "url" ? "block" : "none";
      imageBox.style.display = currentInputMode === "image" ? "block" : "none";
    });
  });
}

// =============================================================================
// Sample Quick Chips
// =============================================================================
function initSampleChips() {
  const chips = document.querySelectorAll(".chip-btn[data-sample]");
  const textArea = document.getElementById("input-text-area");

  chips.forEach(chip => {
    chip.addEventListener("click", () => {
      const sampleKey = chip.getAttribute("data-sample");
      if (SAMPLE_CLAIMS[sampleKey]) {
        textArea.value = SAMPLE_CLAIMS[sampleKey];
        // Switch to text mode if not already active
        document.querySelector('.input-tab-btn[data-mode="text"]').click();
        ocrUsedFlag = false;
        ocrConfidenceScore = null;
        currentSourceUrl = "";
        document.getElementById("ocr-indicator-pill").style.display = "none";
      }
    });
  });
}

// =============================================================================
// URL Scraper Handler
// =============================================================================
function initUrlScraper() {
  const fetchBtn = document.getElementById("btn-fetch-url");
  const urlInput = document.getElementById("input-url-field");
  const statusDiv = document.getElementById("url-scrape-status");
  const textArea = document.getElementById("input-text-area");

  fetchBtn.addEventListener("click", async () => {
    const url = urlInput.value.trim();
    if (!url) {
      statusDiv.innerHTML = '<span style="color: #f43f5e;">Please enter an article URL.</span>';
      return;
    }

    statusDiv.innerHTML = '<span style="color: #60a5fa;">Extracting article content from URL...</span>';
    fetchBtn.disabled = true;

    try {
      const resp = await fetch("/api/extract-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });
      const data = await resp.json();

      if (resp.ok && data.success) {
        currentSourceUrl = url;
        textArea.value = data.title ? `${data.title}\n\n${data.body_text}` : data.body_text;
        statusDiv.innerHTML = `<span style="color: #10b981;">Successfully extracted article (${data.domain}). Switch to Text tab to inspect or click Verify.</span>`;
        // Switch back to text view
        document.querySelector('.input-tab-btn[data-mode="text"]').click();
      } else {
        statusDiv.innerHTML = `<span style="color: #f43f5e;">${data.detail || "Unable to extract URL."}</span>`;
      }
    } catch (err) {
      statusDiv.innerHTML = `<span style="color: #f43f5e;">Network error connecting to extractor.</span>`;
    } finally {
      fetchBtn.disabled = false;
    }
  });
}

// =============================================================================
// EasyOCR Image Handler
// =============================================================================
function initImageOcr() {
  const dropzone = document.getElementById("image-dropzone");
  const fileInput = document.getElementById("image-file-input");
  const previewStrip = document.getElementById("image-preview-strip");
  const filenameElem = document.getElementById("image-filename");
  const ocrStatusBadge = document.getElementById("ocr-badge-status");
  const textArea = document.getElementById("input-text-area");
  const ocrPill = document.getElementById("ocr-indicator-pill");

  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.style.borderColor = "#3b82f6";
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.style.borderColor = "rgba(255, 255, 255, 0.15)";
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.style.borderColor = "rgba(255, 255, 255, 0.15)";
    if (e.dataTransfer.files.length) {
      fileInput.files = e.dataTransfer.files;
      handleImageUpload(fileInput.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) {
      handleImageUpload(fileInput.files[0]);
    }
  });

  async function handleImageUpload(file) {
    previewStrip.style.display = "flex";
    filenameElem.textContent = file.name;
    ocrStatusBadge.textContent = "Processing OCR...";
    ocrStatusBadge.style.color = "#fcd34d";

    const formData = new FormData();
    formData.append("file", file);

    try {
      const resp = await fetch("/api/ocr", {
        method: "POST",
        body: formData
      });
      const data = await resp.json();

      if (resp.ok && data.extracted_text) {
        textArea.value = data.extracted_text;
        ocrUsedFlag = true;
        ocrConfidenceScore = data.confidence;
        ocrStatusBadge.textContent = `OCR Complete (${data.confidence}%)`;
        ocrStatusBadge.style.color = "#6ee7b7";
        ocrPill.style.display = "block";
        ocrPill.innerHTML = `🔍 <strong>OCR Notice:</strong> Content extracted via EasyOCR with PyTorch (Confidence: ${data.confidence}%, ${data.word_count} words)`;
        // Auto-switch to text view to show extracted words
        document.querySelector('.input-tab-btn[data-mode="text"]').click();
      } else {
        ocrStatusBadge.textContent = "OCR: No text found";
        ocrStatusBadge.style.color = "#f43f5e";
      }
    } catch (err) {
      ocrStatusBadge.textContent = "OCR Error";
      ocrStatusBadge.style.color = "#f43f5e";
    }
  }
}

// =============================================================================
// Main Claim Verification Trigger
// =============================================================================
function initVerifyButton() {
  const verifyBtn = document.getElementById("btn-verify-claim");
  const textArea = document.getElementById("input-text-area");

  verifyBtn.addEventListener("click", () => {
    const text = textArea.value.trim();
    if (!text) {
      alert("Please enter news content, headline, or claim to verify.");
      return;
    }
    executeVerification(text);
  });
}

async function executeVerification(text) {
  const verifyBtn = document.getElementById("btn-verify-claim");
  const spinner = document.getElementById("verification-spinner");
  const btnText = document.getElementById("btn-verify-text");

  verifyBtn.disabled = true;
  btnText.textContent = "VERIFYING EVIDENCE...";
  spinner.style.display = "flex";

  try {
    const payload = {
      text: text,
      input_type: currentInputMode,
      source_url: currentSourceUrl,
      ocr_used: ocrUsedFlag,
      ocr_confidence: ocrConfidenceScore
    };

    const resp = await fetch("/api/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await resp.json();

    if (resp.ok) {
      renderVerificationResults(data);
    } else {
      alert(data.detail || "Verification failed.");
    }
  } catch (err) {
    console.error("Verification error:", err);
    alert("Connection error occurred during verification.");
  } finally {
    verifyBtn.disabled = false;
    btnText.textContent = "VERIFY CLAIM";
    spinner.style.display = "none";
  }
}

// =============================================================================
// Render Verification Results on the Two-Column Dashboard
// =============================================================================
function renderVerificationResults(data) {
  // 1. LEFT SIDE - Submitted Content & Claim Inspection
  document.getElementById("display-submitted-content").textContent = data.original_input;
  document.getElementById("display-extracted-claim").textContent = data.extracted_claim;
  document.getElementById("display-language").textContent = data.detected_language || "English (en)";
  document.getElementById("display-source-origin").textContent = data.source_url || "Direct User Submission";

  // OCR Indicator
  const ocrPill = document.getElementById("ocr-indicator-pill");
  if (data.ocr_used) {
    ocrPill.style.display = "block";
    ocrPill.innerHTML = `🔍 <strong>OCR Notice:</strong> Content extracted via EasyOCR with PyTorch (Confidence: ${data.ocr_confidence || "92.0"}%)`;
  } else {
    ocrPill.style.display = "none";
  }

  // Model Stylistic Explanation ("Why did the model flag this?")
  const predPill = document.getElementById("model-pred-pill");
  const isMisleading = data.prediction === "MISLEADING";
  predPill.textContent = data.prediction;
  predPill.className = `model-pred-badge ${isMisleading ? "pred-misleading" : "pred-genuine"}`;

  document.getElementById("model-conf-text").textContent = `${data.model_confidence} (${data.confidence_score}%)`;

  const featurePillsContainer = document.getElementById("model-feature-pills");
  featurePillsContainer.innerHTML = "";
  if (data.stylistic_markers && data.stylistic_markers.length > 0) {
    data.stylistic_markers.forEach(marker => {
      const pill = document.createElement("span");
      pill.className = "feature-pill";
      pill.textContent = marker;
      featurePillsContainer.appendChild(pill);
    });
  } else {
    featurePillsContainer.innerHTML = '<span style="color: var(--text-dim); font-size: 0.75rem;">Standard vocabulary distribution</span>';
  }

  document.getElementById("model-explanation-narrative").textContent = data.explanation || "";

  // Rapid Spread / Burst Detection Indicator on Left
  const burstBox = document.getElementById("burst-alert-container");
  if (data.burst_detected) {
    burstBox.style.display = "flex";
    document.getElementById("burst-velocity-stat").textContent = `${data.mentions_velocity} mentions / 10 minutes`;
  } else {
    burstBox.style.display = "none";
  }

  // 2. RIGHT SIDE - SOURCE & SPREAD VERIFICATION
  const spreadData = data.source_and_spread;
  if (spreadData) {
    // Timestamp
    if (document.getElementById("data-retrieved-timestamp")) {
      document.getElementById("data-retrieved-timestamp").textContent = `Data retrieved: ${spreadData.retrieval_timestamp}`;
    }

    // Original Source Card
    const orig = spreadData.original_source || {};
    document.getElementById("orig-source-title").textContent = orig.title || "User Submitted Claim";
    document.getElementById("orig-source-author").textContent = orig.author || "Author information not publicly available";
    document.getElementById("orig-source-date").textContent = orig.publication_date || "Recent";
    const origUrlEl = document.getElementById("orig-source-url");
    if (orig.url && orig.url !== "#") {
      origUrlEl.href = orig.url;
      origUrlEl.textContent = orig.url;
    } else {
      origUrlEl.href = "#";
      origUrlEl.textContent = "Direct User Text Submission";
    }

    // Source Count & Platform Breakdown
    document.getElementById("breakdown-total-count").textContent = `Sources found: ${spreadData.sources_found_count}`;
    const chipsContainer = document.getElementById("platform-chips-container");
    chipsContainer.innerHTML = "";
    const breakdown = spreadData.platform_breakdown || {};
    for (const [platform, count] of Object.entries(breakdown)) {
      const chip = document.createElement("span");
      let chipClass = "chip-news";
      if (platform.includes("YouTube")) chipClass = "chip-yt";
      else if (platform.includes("Instagram") || platform.includes("Social")) chipClass = "chip-social";
      else if (platform.includes("Reference")) chipClass = "chip-ref";

      chip.className = `platform-chip ${chipClass}`;
      chip.textContent = `${platform}: ${count}`;
      chipsContainer.appendChild(chip);
    }

    // Spread Analytics Box
    const sInfo = spreadData.spread_info || {};
    const spreadBadge = document.getElementById("spread-status-badge");
    spreadBadge.textContent = sInfo.status || "Moderate propagation";
    spreadBadge.className = `badge-tag ${sInfo.badge_class || "badge-moderate-spread"}`;

    document.getElementById("spread-first-observed").textContent = sInfo.first_observed || "Recent";
    document.getElementById("spread-latest-observed").textContent = sInfo.latest_observed || "Just now";
    document.getElementById("spread-sources-count").textContent = sInfo.sources_found || spreadData.sources_found_count;
    document.getElementById("spread-platforms-count").textContent = sInfo.platforms_found || spreadData.platforms_count;

    // Render Source Cards
    renderPlatformSourceCards(spreadData.sources || []);

    // Summary Box
    document.getElementById("sum-pred").textContent = data.prediction;
    document.getElementById("sum-pred").style.color = "#ffffff";

    const sumStatus = document.getElementById("sum-status");
    sumStatus.textContent = data.evidence_status.split(" ")[0];
    sumStatus.style.color = "#ffffff";

    document.getElementById("sum-sources-count").textContent = spreadData.sources_found_count;
    document.getElementById("sum-primary-count").textContent = spreadData.platforms_count;
    document.getElementById("sum-human-verdict").textContent = data.human_verification;

  } else {
    // Fallback if source_and_spread not provided
    renderSourceCards(data.annotated_sources || []);
  }
}

// =============================================================================
// Render Individual Platform Source Cards
// =============================================================================
function renderPlatformSourceCards(sources) {
  const container = document.getElementById("source-cards-container");
  container.innerHTML = "";

  if (!sources || sources.length === 0) {
    container.innerHTML = `
      <div style="background: var(--bg-card); border: 1px dashed var(--border-hairline); border-radius: 6px; padding: 2rem; text-align: center; color: var(--text-dim);">
        <strong style="color: var(--text-muted); font-size: 0.95rem;">No sufficient external evidence found.</strong>
        <p style="font-size: 0.8rem; margin-top: 0.3rem;">
          Publicly accessible official registries and news archives do not contain matching verifiable records for this specific claim.
        </p>
      </div>
    `;
    return;
  }

  sources.forEach(src => {
    const card = document.createElement("div");
    card.className = "source-card";

    // Platform Badge Class
    let platChipClass = "chip-news";
    let platIcon = "•";
    if (src.platform.includes("YouTube")) {
      platChipClass = "chip-yt";
      platIcon = "▶";
    } else if (src.platform.includes("Instagram") || src.platform.includes("Social")) {
      platChipClass = "chip-social";
      platIcon = "◆";
    } else if (src.platform.includes("Reference")) {
      platChipClass = "chip-ref";
      platIcon = "◈";
    }

    // Stance Class
    let stanceLabel = src.relationship_label || "Relationship unclear";
    let stanceBadgeClass = src.badge_class || "badge-unclear";

    // Author display
    let authorDisplay = src.author ? escapeHtml(src.author) : "Author information not publicly available";

    card.innerHTML = `
      <div class="card-top-row">
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <span class="platform-chip ${platChipClass}" style="font-size: 0.72rem; padding: 0.2rem 0.6rem;">
            ${platIcon} ${escapeHtml(src.platform)}
          </span>
          <span class="card-type-pill" style="font-size: 0.7rem;">
            ${escapeHtml(src.source_type || "Public")}
          </span>
        </div>
        ${src.engagement ? `<span class="card-engagement-pill">${escapeHtml(src.engagement)}</span>` : ""}
      </div>

      <h3 class="card-source-title" style="margin: 0.5rem 0 0.3rem;">${escapeHtml(src.title)}</h3>

      <div class="card-meta-row" style="margin-bottom: 0.6rem;">
        <span>Author / Channel: <strong class="card-outlet-name">${authorDisplay}</strong></span>
        <span>•</span>
        <span>Date: ${escapeHtml(src.publication_date || "Date not publicly available")}</span>
      </div>

      <div class="card-evidence-extract">
        <strong style="color: #ffffff;">Evidence:</strong><br>
        "${escapeHtml(src.evidence_snippet || "No direct snippet available.")}"
      </div>

      <div class="card-bottom-row">
        <div>
          <span class="badge-relationship ${stanceBadgeClass}">
            ${escapeHtml(stanceLabel)}
          </span>
        </div>

        <a href="${escapeHtml(src.url)}" target="_blank" rel="noopener noreferrer" class="btn-open-source">
          OPEN SOURCE ↗
        </a>
      </div>
    `;

    container.appendChild(card);
  });
}


function getRelationshipIcon(code) {
  if (code === "SUPPORTS") return "✓";
  if (code === "CONTRADICTS") return "✕";
  if (code === "CONTEXT") return "ℹ";
  return "?";
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// =============================================================================
// Initial Benchmark Load on Page Launch
// =============================================================================
function runInitialDemoVerification() {
  // Preload a rich verification so the dashboard is immediately populated on launch
  const initialData = {
    original_input: "Government secretly announces that all public schools will remain closed for three months.",
    extracted_claim: "Government secretly announces that all public schools will remain closed for three months.",
    detected_language: "English (en)",
    source_url: "Direct User Submission",
    prediction: "MISLEADING",
    model_confidence: "Moderate",
    confidence_score: 64.0,
    stylistic_markers: ["government secretly", "secretly", "announces", "closed"],
    explanation: "The model detected stylistic patterns (government secretly, secretly, announces, closed) consistent with sensationalist or speculative rhetoric.",
    evidence_status: "Contradicted by available evidence",
    status_code: "CONTRADICTED",
    status_description: "Publicly accessible official or news reports contradict or debunk the asserted claim.",
    human_verification: "Strongly recommended",
    sources_count: 8,
    primary_sources_count: 3,
    burst_detected: true,
    mentions_velocity: 520,
    ocr_used: false,
    source_and_spread: {
      retrieval_timestamp: "25 Sep 2026, 10:30 AM",
      original_source: {
        title: "Viral Social Media Broadcast: School Suspension Claim",
        url: "#",
        author: "Author information not publicly available",
        publication_date: "24 Sep 2026, 08:45 AM"
      },
      sources_found_count: 8,
      platforms_count: 3,
      platform_breakdown: {
        "News websites": 4,
        "YouTube": 3,
        "Instagram / Social": 1
      },
      spread_info: {
        first_observed: "24 Sep 2026, 08:45 AM",
        latest_observed: "25 Sep 2026, 10:30 AM",
        sources_found: 8,
        platforms_found: 3,
        status: "Rapid increase detected",
        badge_class: "badge-rapid-increase"
      },
      sources: [
        {
          platform: "News Website",
          source_type: "Official Organization",
          title: "Fact Check: Education Ministry Debunks False Rumors of Prolonged School Closures",
          author: "Education Desk (Reuters Fact Check)",
          publication_date: "24 Sep 2026, 14:20 GMT",
          engagement: "Verified Editorial Review",
          url: "https://www.reuters.com/fact-check",
          evidence_snippet: "Government educational authorities confirmed that all public schools will remain open following the routine holiday calendar, dismissing viral social media claims of a secret three-month closure order as completely fabricated.",
          relationship_label: "Contradicts claim",
          badge_class: "badge-contradicts"
        },
        {
          platform: "YouTube",
          source_type: "Social Media",
          title: "Education Ministry Press Conference: Clarification on School Term Schedules",
          author: "Public Broadcast News",
          publication_date: "18 hours ago",
          engagement: "214,800 views",
          url: "https://www.youtube.com/watch?v=sample_news",
          evidence_snippet: "The ministry spokesperson announced during this morning's press briefing that academic calendars will proceed normally without unplanned shutdowns.",
          relationship_label: "Contradicts claim",
          badge_class: "badge-contradicts"
        },
        {
          platform: "News Website",
          source_type: "News",
          title: "Associated Press: No truth to viral shutdown decrees circulating on messaging apps",
          author: "AP National News Team",
          publication_date: "25 Sep 2026, 06:10 GMT",
          engagement: "Public journalistic publication",
          url: "https://apnews.com",
          evidence_snippet: "Officials reiterated that emergency executive declarations are only published via the official state gazette and no closure orders have been issued.",
          relationship_label: "Contradicts claim",
          badge_class: "badge-contradicts"
        },
        {
          platform: "Instagram (Public Index)",
          source_type: "Social Media",
          title: "Public Fact Check Reel: Addressing Viral WhatsApp Claim on Academic Closures",
          author: "Author information not publicly available",
          publication_date: "Yesterday",
          engagement: "Public engagement metrics restricted by platform",
          url: "https://www.instagram.com",
          evidence_snippet: "Verified reporters debunk viral forwarded chain letter claiming government closed all schools for ninety days.",
          relationship_label: "Contradicts claim",
          badge_class: "badge-contradicts"
        }
      ]
    }
  };

  renderVerificationResults(initialData);
}

// =============================================================================
// History Tab Logic
// =============================================================================
function initHistoryTab() {
  const refreshBtn = document.getElementById("btn-refresh-history");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", loadHistoryList);
  }
}

async function loadHistoryList() {
  const tbody = document.getElementById("history-tbody");
  tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-dim); padding: 1.5rem;">Loading audit records...</td></tr>';

  try {
    const resp = await fetch("/api/history");
    const data = await resp.json();

    if (!data.history || data.history.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-dim); padding: 1.5rem;">No verification records found.</td></tr>';
      return;
    }

    tbody.innerHTML = "";
    data.history.forEach(item => {
      const tr = document.createElement("tr");
      const isMisleading = item.prediction === "MISLEADING";
      const predColor = isMisleading ? "var(--color-misleading)" : "var(--color-genuine)";

      tr.innerHTML = `
        <td style="font-family: monospace; color: var(--text-dim);">#${item.id}</td>
        <td style="white-space: nowrap; font-size: 0.78rem; color: var(--text-dim);">${escapeHtml(item.timestamp)}</td>
        <td style="max-width: 320px; font-weight: 500;">${escapeHtml(item.extracted_claim)}</td>
        <td><strong style="color: ${predColor};">${escapeHtml(item.prediction)}</strong></td>
        <td><span class="badge-tag" style="background: rgba(255,255,255,0.06); font-size: 0.75rem;">${escapeHtml(item.evidence_status)}</span></td>
        <td style="text-align: center; font-weight: 700;">${item.sources_count}</td>
        <td style="font-size: 0.8rem; color: #bfdbfe;">${escapeHtml(item.human_verification)}</td>
        <td>
          <button class="btn-reopen" onclick="reopenHistoryRecord(${item.id})">
            Reopen
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: #f43f5e; padding: 1.5rem;">Failed to load history records.</td></tr>';
  }
}

window.reopenHistoryRecord = async function(id) {
  try {
    const resp = await fetch(`/api/history/${id}`);
    const record = await resp.json();

    if (resp.ok && record) {
      // Re-populate text area
      document.getElementById("input-text-area").value = record.original_input;
      ocrUsedFlag = record.ocr_used;
      currentSourceUrl = "";

      // Adapt record fields to render format
      const formatted = {
        original_input: record.original_input,
        extracted_claim: record.extracted_claim,
        detected_language: "English (en)",
        source_url: record.input_type === "url" ? record.original_input : "History Archive",
        prediction: record.prediction,
        model_confidence: record.model_confidence,
        confidence_score: record.confidence_score,
        stylistic_markers: record.stylistic_markers || [],
        explanation: record.explanation,
        evidence_status: record.evidence_status,
        status_code: record.evidence_status.includes("Contradicted") ? "CONTRADICTED" : (record.evidence_status.includes("Supported") ? "SUPPORTED" : "MIXED"),
        status_description: `Loaded from persistent verification audit log #${id}`,
        human_verification: record.human_verification,
        sources_count: record.sources_count,
        primary_sources_count: record.primary_sources_count,
        burst_detected: record.burst_detected,
        mentions_velocity: record.mentions_velocity,
        ocr_used: record.ocr_used,
        annotated_sources: record.sources || []
      };

      renderVerificationResults(formatted);

      // Switch view back to Dashboard
      document.querySelector('.nav-btn[data-tab="tab-dashboard"]').click();
    }
  } catch (err) {
    alert("Failed to reload history record.");
  }
};

// =============================================================================
// Big Data Layer Loader
// =============================================================================
function initBigDataTab() {
  // Handled dynamically on tab click
}

async function loadBigDataStats() {
  const codeBox = document.getElementById("spark-code-display");
  try {
    const resp = await fetch("/api/bigdata-stats");
    const data = await resp.json();
    if (data.spark_script) {
      codeBox.textContent = data.spark_script;
    }
  } catch (err) {
    codeBox.textContent = "# PySpark script documentation temporarily unavailable.";
  }
}
