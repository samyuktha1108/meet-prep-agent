let currentContact = null;
let contactsCache = [];

const contactList = document.getElementById("contact-list");
const emptyState = document.getElementById("empty-state");
const contactView = document.getElementById("contact-view");
const contactNameEl = document.getElementById("contact-name");
const meetingCountEl = document.getElementById("meeting-count");

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

// Returns {label, cls} describing how urgent a date is, or null if no date.
function reminderStatus(dateStr) {
  if (!dateStr) return null;
  const today = new Date(todayStr() + "T00:00:00");
  const target = new Date(dateStr + "T00:00:00");
  const diffDays = Math.round((target - today) / 86400000);
  if (diffDays < 0) return { label: `${-diffDays}d overdue`, cls: "overdue" };
  if (diffDays === 0) return { label: "today", cls: "soon" };
  if (diffDays === 1) return { label: "tomorrow", cls: "soon" };
  if (diffDays <= 3) return { label: `in ${diffDays}d`, cls: "soon" };
  return { label: dateStr, cls: "later" };
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function loadContacts(selectName) {
  const contacts = await api("/api/contacts");
  contactsCache = contacts;
  contactList.innerHTML = "";
  contacts.forEach((c) => {
    const li = document.createElement("li");
    li.dataset.name = c.name;
    li.className = currentContact === c.name ? "active" : "";
    const reminder = reminderStatus(c.next_meeting_date);
    const dot = reminder ? `<span class="badge-dot ${reminder.cls}" title="Next meeting: ${c.next_meeting_date}"></span>` : "";
    li.innerHTML = `<span class="name">${c.name}${dot}</span><span class="count">${c.meeting_count || 0}</span>`;
    li.addEventListener("click", () => selectContact(c.name));
    contactList.appendChild(li);
  });
  if (selectName) selectContact(selectName);
}

function selectContact(name) {
  currentContact = name;
  emptyState.classList.add("hidden");
  contactView.classList.remove("hidden");
  contactNameEl.textContent = name;
  meetingCountEl.textContent = "";
  document.getElementById("briefing-box").textContent = "Prep briefings appear here once generated.";
  document.getElementById("briefing-box").classList.add("placeholder");
  document.getElementById("timeline-list").innerHTML = "";
  document.getElementById("notes-input").value = "";
  document.getElementById("meeting-date-input").value = todayStr();

  const contact = contactsCache.find((c) => c.name === name) || {};
  document.getElementById("next-meeting-input").value = contact.next_meeting_date || "";
  renderReminderBadge(contact.next_meeting_date);

  [...contactList.children].forEach((li) => {
    li.classList.toggle("active", li.dataset.name === name);
  });
  refreshTimeline();
}

function renderReminderBadge(dateStr) {
  const badge = document.getElementById("next-meeting-badge");
  const reminder = reminderStatus(dateStr);
  if (!reminder) {
    badge.textContent = "";
    badge.className = "reminder-badge";
    return;
  }
  badge.textContent = reminder.label;
  badge.className = `reminder-badge ${reminder.cls}`;
}

document.getElementById("add-contact-btn").addEventListener("click", async () => {
  const input = document.getElementById("new-contact-input");
  const name = input.value.trim();
  if (!name) return;
  await api("/api/contacts", { method: "POST", body: JSON.stringify({ name }) });
  input.value = "";
  await loadContacts(name);
});

document.getElementById("new-contact-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") document.getElementById("add-contact-btn").click();
});

document.getElementById("log-btn").addEventListener("click", async () => {
  const notes = document.getElementById("notes-input").value.trim();
  const date = document.getElementById("meeting-date-input").value || null;
  const statusEl = document.getElementById("log-status");
  if (!notes || !currentContact) return;
  const btn = document.getElementById("log-btn");
  btn.disabled = true;
  statusEl.textContent = "Saving to memory...";
  statusEl.className = "status";
  try {
    await api("/api/log", { method: "POST", body: JSON.stringify({ contact: currentContact, notes, date }) });
    statusEl.textContent = "Logged.";
    document.getElementById("notes-input").value = "";
    await loadContacts(currentContact);
    await refreshTimeline();
  } catch (err) {
    statusEl.textContent = err.message;
    statusEl.className = "status error";
  } finally {
    btn.disabled = false;
  }
});

document.getElementById("save-next-meeting-btn").addEventListener("click", async () => {
  if (!currentContact) return;
  const date = document.getElementById("next-meeting-input").value || null;
  try {
    await api("/api/next-meeting", { method: "POST", body: JSON.stringify({ contact: currentContact, date }) });
    renderReminderBadge(date);
    await loadContacts(currentContact);
  } catch (err) {
    alert("Couldn't save next meeting date: " + err.message);
  }
});

document.getElementById("prep-btn").addEventListener("click", async () => {
  if (!currentContact) return;
  const box = document.getElementById("briefing-box");
  const btn = document.getElementById("prep-btn");
  btn.disabled = true;
  box.classList.remove("placeholder");
  box.textContent = "Thinking back over everything with " + currentContact + "...";
  try {
    const result = await api("/api/prep", { method: "POST", body: JSON.stringify({ contact: currentContact }) });
    box.textContent = result.briefing;
  } catch (err) {
    box.textContent = "Couldn't generate a briefing: " + err.message;
  } finally {
    btn.disabled = false;
  }
});

document.getElementById("timeline-btn").addEventListener("click", refreshTimeline);

async function refreshTimeline() {
  if (!currentContact) return;
  const list = document.getElementById("timeline-list");
  try {
    const result = await api("/api/timeline", { method: "POST", body: JSON.stringify({ contact: currentContact }) });
    list.innerHTML = "";
    if (!result.memories.length) {
      list.innerHTML = '<li style="border-left-color: var(--border); color: var(--ink-dim);">Nothing remembered yet - log a meeting to get started.</li>';
      return;
    }
    result.memories.forEach((m) => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="memory-type">${m.type || "memory"}</span>${m.text}`;
      list.appendChild(li);
    });
  } catch (err) {
    list.innerHTML = `<li style="border-left-color: var(--danger);">${err.message}</li>`;
  }
}

loadContacts();
