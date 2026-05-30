const DIGEST_URL = "/api/v1/ops/readiness-digest";

const statusCopy = {
  blocked: "Blocked",
  in_progress: "In progress",
  done: "Done",
  ready_for_cto_review: "Ready for CTO review",
  ready_for_founder_risk_review: "Ready for founder risk review",
  approved_for_second_slice_repeatability_review:
    "Approved for repeatability review",
  not_ready_for_gate_review: "Not ready for gate review",
};

const verdictTone = {
  not_ready_for_gate_review: "blocked",
  ready_for_cto_review: "ready",
  ready_for_founder_risk_review: "ready",
  approved_for_second_slice_repeatability_review: "done",
};

function formatLabel(value) {
  return statusCopy[value] ?? value.replaceAll("_", " ");
}

function setAccessState(state, detail = "") {
  const accessState = document.querySelector("#auth-status");
  accessState.textContent = state;
  accessState.dataset.state = state.toLowerCase().replaceAll(" ", "-");
  accessState.title = detail;
}

function renderWarningBanner(warnings) {
  const banner = document.querySelector("#warning-banner");
  if (!warnings.length) {
    banner.hidden = true;
    banner.textContent = "";
    return;
  }

  banner.hidden = false;
  banner.textContent = warnings
    .map((warning) => `${warning.code}: ${warning.message}`)
    .join(" ");
}

function renderBlockers(blockers) {
  const blockerCount = document.querySelector("#blocker-count");
  const blockerList = document.querySelector("#blocker-list");

  blockerCount.textContent = String(blockers.length);
  blockerList.innerHTML = "";

  if (!blockers.length) {
    blockerList.append(createEmptyState("No open blockers in the digest scope."));
    return;
  }

  blockers.forEach((blocker) => {
    const item = document.createElement("li");
    item.className = "blocker-item";
    item.innerHTML = `
      <strong>${blocker.issue}</strong>
      <p class="blocker-reason">${blocker.reason}</p>
    `;
    blockerList.append(item);
  });
}

function renderEvidence(links) {
  const evidenceList = document.querySelector("#evidence-list");
  evidenceList.innerHTML = "";

  if (!links.length) {
    evidenceList.append(createEmptyState("No evidence artifacts attached yet."));
    return;
  }

  links.forEach((link) => {
    const item = document.createElement("li");
    item.className = "evidence-item";
    item.innerHTML = `
      <strong>${link.label}</strong>
      <a href="../../${link.path}" target="_blank" rel="noreferrer">${link.path}</a>
    `;
    evidenceList.append(item);
  });
}

function renderWorkstreams(workstreams) {
  const rows = document.querySelector("#workstream-rows");
  rows.innerHTML = "";

  workstreams.forEach((stream) => {
    const tr = document.createElement("tr");
    const blockerTokens = stream.blockers.length
      ? renderTokenList(stream.blockers)
      : `<span class="token">None</span>`;
    const evidenceTokens = stream.requiredEvidence.length
      ? renderTokenList(stream.requiredEvidence)
      : `<span class="token">Not specified</span>`;

    tr.innerHTML = `
      <td>${formatLabel(stream.key)}</td>
      <td>${stream.issue}</td>
      <td><span class="status-tag ${stream.status}">${formatLabel(stream.status)}</span></td>
      <td><div class="token-list">${blockerTokens}</div></td>
      <td><div class="token-list">${evidenceTokens}</div></td>
    `;
    rows.append(tr);
  });
}

function renderTokenList(values) {
  return values.map((value) => `<span class="token">${value}</span>`).join("");
}

function createEmptyState(text) {
  const template = document.querySelector("#empty-state-template");
  const node = template.content.firstElementChild.cloneNode(true);
  node.textContent = text;
  return node;
}

function renderSummary(digest) {
  document.querySelector("#slice-id").textContent = digest.sliceId;
  document.querySelector("#generated-at").textContent = new Date(
    digest.generatedAt,
  ).toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  });

  const verdictPill = document.querySelector("#verdict-pill");
  verdictPill.textContent = formatLabel(digest.overallVerdict);
  verdictPill.className = `status-pill ${verdictTone[digest.overallVerdict] ?? "neutral"}`;

  document.querySelector("#summary-copy").textContent =
    `Program scope ${digest.scope.programIssue}; architecture contract ${digest.scope.architectureIssue}.`;
  document.querySelector("#completed-count").textContent =
    digest.summary.completedWorkstreams;
  document.querySelector("#blocked-count").textContent =
    digest.summary.blockedWorkstreams;
  document.querySelector("#in-progress-count").textContent =
    digest.summary.inProgressWorkstreams;
}

async function loadDigest() {
  try {
    const token =
      document
        .querySelector('meta[name="readiness-digest-token"]')
        ?.content?.trim() ?? "";
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const response = await fetch(DIGEST_URL, { headers });

    if (response.status === 401) {
      setAccessState("Authentication required", "The protected operator API rejected this browser session.");
      renderWarningBanner([
        {
          code: "DIGEST_AUTH_REQUIRED",
          message:
            "Operator authentication is required before this UI can load the readiness digest. The route-like static digest fixture has been removed from this operator surface.",
        },
      ]);
      document.querySelector("#summary-copy").textContent =
        "Authenticate as an internal operator to load the live digest from the protected API route.";
      return;
    }

    if (!response.ok) {
      throw new Error(`Digest request failed with ${response.status}`);
    }

    const digest = await response.json();
    setAccessState("Authenticated", "Digest loaded from the protected operator API.");
    renderSummary(digest);
    renderWarningBanner(digest.warnings ?? []);
    renderBlockers(digest.blockers ?? []);
    renderWorkstreams(digest.workstreams ?? []);
    renderEvidence(digest.evidenceLinks ?? []);
  } catch (error) {
    setAccessState("Unavailable", error.message);
    renderWarningBanner([
      {
        code: "DIGEST_LOAD_FAILED",
        message: error.message,
      },
    ]);
    document.querySelector("#summary-copy").textContent =
      "Digest data could not be loaded. This prototype intentionally degrades instead of blanking the page.";
  }
}

if (typeof document !== "undefined") {
  loadDigest();
}
