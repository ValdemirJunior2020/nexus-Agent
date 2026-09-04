const client = ZAFClient.init();
let latestAnswer = "";
const ISSUE_MESSAGE = "I'm saving all the issues happening with me so Junior can fix it later.";
const PENDING_ISSUES_KEY = "nexus_pending_issues";

const $ = (id) => document.getElementById(id);
const setStatus = (text, cls="") => {
  const el = $("status");
  el.textContent = text;
  el.className = "status" + (cls ? " " + cls : "");
};

let progressTimer = null;
let progressValue = 0;
function setProgress(value, label="Processing") {
  progressValue = Math.max(0, Math.min(100, Math.round(value)));
  $("progressWrap").classList.remove("hidden");
  $("progressBar").style.width = `${progressValue}%`;
  $("progressPct").textContent = `${progressValue}%`;
  $("progressLabel").textContent = label;
  if (progressValue < 100) setStatus(`${label} ${progressValue}%`, "busy");
}
function startProgress() {
  if (progressTimer) clearInterval(progressTimer);
  setProgress(5, "Reading ticket");
  progressTimer = setInterval(() => {
    if (progressValue >= 92) return;
    const step = progressValue < 45 ? 4 : progressValue < 75 ? 2 : 1;
    setProgress(progressValue + step, progressValue < 30 ? "Checking context" : progressValue < 70 ? "NEXUS is reasoning" : "Verifying answer");
  }, 900);
}
function finishProgress(ok=true) {
  if (progressTimer) { clearInterval(progressTimer); progressTimer = null; }
  setProgress(100, ok ? "Complete" : "Issue saved");
  setTimeout(() => $("progressWrap").classList.add("hidden"), 1200);
}

function queueLocalIssue(issue) {
  try {
    const current = JSON.parse(localStorage.getItem(PENDING_ISSUES_KEY) || "[]");
    current.push({...issue, saved_at: new Date().toISOString()});
    localStorage.setItem(PENDING_ISSUES_KEY, JSON.stringify(current.slice(-100)));
  } catch (_) {}
}

async function reportIssue(apiUrl, issue) {
  try {
    const response = await fetch(`${apiUrl}/logs/client`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(issue)
    });
    if (!response.ok) throw new Error(`log endpoint ${response.status}`);
    return await response.json();
  } catch (_) {
    queueLocalIssue(issue);
    return null;
  }
}

async function flushPendingIssues(apiUrl) {
  let pending = [];
  try { pending = JSON.parse(localStorage.getItem(PENDING_ISSUES_KEY) || "[]"); } catch (_) {}
  if (!Array.isArray(pending) || pending.length === 0) return;
  const remaining = [];
  for (const issue of pending.slice(-100)) {
    try {
      const response = await fetch(`${apiUrl}/logs/client`, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(issue)
      });
      if (!response.ok) remaining.push(issue);
    } catch (_) { remaining.push(issue); }
  }
  try { localStorage.setItem(PENDING_ISSUES_KEY, JSON.stringify(remaining)); } catch (_) {}
}

async function safeGet(path) {
  try {
    const data = await client.get(path);
    return data[path];
  } catch (_) {
    return null;
  }
}

function conversationToComments(conversation) {
  const publicComments = [];
  const internalComments = [];
  for (const event of Array.isArray(conversation) ? conversation : []) {
    const content = event?.message?.content;
    if (!content) continue;
    const author = event?.author?.name || event?.author?.role || "Unknown";
    const stamp = event?.timestamp || "";
    const text = `${author} ${stamp}\n${content}`.trim();
    if (event?.channel?.name === "internal") internalComments.push(text);
    else publicComments.push(text);
  }
  return { publicComments, internalComments };
}

async function buildPayload() {
  const metadata = await client.metadata();
  const settings = metadata?.settings || {};
  const [ticketId, subject, requester, status, priority, brand, tags, assignee, conversation] = await Promise.all([
    safeGet("ticket.id"),
    safeGet("ticket.subject"),
    safeGet("ticket.requester.name"),
    safeGet("ticket.status"),
    safeGet("ticket.priority"),
    safeGet("ticket.brand.name"),
    safeGet("ticket.tags"),
    safeGet("ticket.assignee"),
    safeGet("ticket.conversation")
  ]);
  const comments = conversationToComments(conversation);
  return {
    apiUrl: String(settings.nexus_api_url || "http://127.0.0.1:8787").replace(/\/$/, ""),
    body: {
      ticket_id: String(ticketId || "unknown"),
      user_id: String(settings.nexus_user_id || "zendesk-agent"),
      subject: subject || "",
      requester: requester || "",
      status: status || "",
      priority: priority || "",
      brand: brand || "",
      group: assignee?.group?.name || "",
      assignee: assignee?.user?.name || "",
      tags: Array.isArray(tags) ? tags : [],
      public_comments: comments.publicComments,
      internal_comments: comments.internalComments,
      engine: "nexus",
      mode: "auto",
      allow_tools: true
    }
  };
}

async function analyzeTicket() {
  const button = $("analyze");
  button.disabled = true;
  startProgress();
  $("result").classList.remove("hidden");
  $("result").textContent = "Reading the current ticket and checking the Ticket Matrix…";
  $("actions").classList.add("hidden");
  try {
    const { apiUrl, body } = await buildPayload();
    setProgress(15, "Reading ticket");
    await flushPendingIssues(apiUrl);
    setProgress(25, "Checking Ticket Matrix");
    const response = await fetch(`${apiUrl}/zendesk/analyze`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(body)
    });
    if (!response.ok) throw new Error(`NEXUS API returned ${response.status}: ${await response.text()}`);
    const data = await response.json();
    latestAnswer = data.answer || "No answer returned.";
    $("result").textContent = latestAnswer;
    $("actions").classList.remove("hidden");
    finishProgress(true);
    setStatus(data.verified ? "Verified" : "Complete");
  } catch (err) {
    latestAnswer = "";
    let apiUrl = "http://127.0.0.1:8787";
    let ticketId = "unknown";
    try {
      const payload = await buildPayload();
      apiUrl = payload.apiUrl;
      ticketId = payload.body.ticket_id;
    } catch (_) {}
    const saved = await reportIssue(apiUrl, {
      component: "zendesk_app.analyze",
      error: String(err?.message || err),
      ticket_id: ticketId,
      source: "zendesk_app"
    });
    const issueSuffix = saved?.incident_id ? `\nIssue ID: ${saved.incident_id}` : "";
    $("result").textContent = `Unable to analyze this ticket.\n\n${ISSUE_MESSAGE}${issueSuffix}`;
    finishProgress(false);
    setStatus("Issue saved", "error");
  } finally {
    button.disabled = false;
    try { await client.invoke("resize", { width: "100%", height: "520px" }); } catch (_) {}
  }
}

$("analyze").addEventListener("click", analyzeTicket);
$("copy").addEventListener("click", async () => {
  if (!latestAnswer) return;
  await navigator.clipboard.writeText(latestAnswer);
  setStatus("Copied");
});
$("append").addEventListener("click", async () => {
  if (!latestAnswer) return;
  try {
    await client.invoke("ticket.comment.appendText", latestAnswer);
    await client.set("ticket.comment.type", "internalNote");
    setStatus("Added to note");
  } catch (err) {
    setStatus("Issue saved", "error");
    try {
      const { apiUrl, body } = await buildPayload();
      await reportIssue(apiUrl, {
        component: "zendesk_app.append_internal_note",
        error: String(err?.message || err),
        ticket_id: body.ticket_id,
        source: "zendesk_app"
      });
    } catch (_) {}
  }
});

client.on("app.registered", async () => {
  try {
    const { apiUrl } = await buildPayload();
    await flushPendingIssues(apiUrl);
  } catch (_) {}
  return client.invoke("resize", { width: "100%", height: "280px" });
});
