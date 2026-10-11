"use strict";

// Offsets from the API are Unicode code points. JavaScript strings index UTF-16 code
// units, so all slicing goes through an array of code points. User text is only ever
// inserted with textContent / text nodes.
const SAMPLE = [
  "Example protocol",
  "Add 5 mL of water to the tube, then mix for 30 s.",
  "Centrifuge at 14,000 x g for 10 min at 4 °C.",
  "Transfer the supernatant to a new tube and incubate overnight at room temperature.",
].join("\n");

const ENTITY_LABELS = ["Action", "Amount", "Concentration", "Device", "Generic-Measure", "Location",
  "Measure-Type", "Mention", "Method", "Modifier", "Numerical", "Reagent", "Seal", "Size", "Speed",
  "Temperature", "Time", "pH"];
const RELATION_LABELS = ["Acts-on", "Commands", "Coreference-Link", "Count", "Measure",
  "Measure-Type-Link", "Meronym", "Mod-Link", "Of-Type", "Or", "Product", "Setting", "Site", "Using"];
const QUANTITY_LABELS = ["Amount", "Concentration", "Generic-Measure", "Numerical", "Size", "Speed",
  "Temperature", "Time", "pH"];
const LEGEND = ["Action", "Reagent", "Amount", "Location", "Device", "Time", "Temperature", "Modifier"];

const $ = (id) => document.getElementById(id);
let doc = null;
let preview = { sheet: [], review_items: [], normalized_values: {} };
let refreshTimer = null;

// ------------------------------------------------------------------ helpers

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("data-")) node.setAttribute(key, value);
    else node[key] = value;
  }
  for (const child of children) {
    if (child === null || child === undefined) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function button(label, onClick, cls = "") {
  const b = el("button", { type: "button", class: cls }, label);
  b.addEventListener("click", onClick);
  return b;
}

function select(options, value, onChange) {
  const s = el("select");
  for (const option of options) s.append(el("option", { value: option, selected: option === value }, option));
  s.addEventListener("change", () => onChange(s.value));
  return s;
}

function setStatus(message, isError = false) {
  $("status").textContent = message;
  $("status").classList.toggle("error", isError);
}

function updateCounter() {
  $("counter").textContent = `${Array.from($("text").value).length.toLocaleString()} characters`;
}

function spanText(entity) {
  return doc.cps.slice(entity.start, entity.end).join("");
}

function isWord(ch) {
  return /[\p{L}\p{N}]/u.test(ch || "");
}

function describeValue(v) {
  if (!v) return "";
  const unit = v.unit ? ` ${v.unit}` : "";
  const q = v.qualifier ? `${v.qualifier} ` : "";
  if (v.kind === "number") return `${q}${v.value}${unit}`;
  if (v.kind === "range") return `${q}${v.low}–${v.high}${unit}`;
  if (v.kind === "ratio") return `${v.numerator}:${v.denominator}`;
  return String(v.value);
}

function kept(entity) {
  return entity && entity.decision !== "rejected";
}

async function postJSON(url, body, headers = {}) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
  const isJSON = (res.headers.get("content-type") || "").includes("json");
  const payload = isJSON ? await res.json() : await res.text();
  if (!res.ok) {
    const detail = isJSON ? payload.detail : payload;
    throw new Error(Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail || `HTTP ${res.status}`);
  }
  return { res, payload };
}

// -------------------------------------------------------------- model info

async function loadModelInfo() {
  const box = $("model-info");
  try {
    const res = await fetch("/readyz");
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || "model not ready");
    box.textContent = `${body.system} · ${body.model_version}`;
    box.title = `bundle ${body.bundle_sha256}`;
    box.className = "model ready";
    $("demo-notice").hidden = !body.public_demo;
    const names = {
      "span-relation": "SciBERT span-relation model.",
      "crf+logreg": "Baseline model (CRF + logistic regression).",
    };
    $("notice-model").textContent = names[body.system] || "Model output.";
    const ev = body.evaluation || {};
    if (typeof ev.relation_f1_end_to_end === "number") {
      $("notice-scores").textContent =
        `Development-set end-to-end relation F1 ${ev.relation_f1_end_to_end.toFixed(2)}`
        + (typeof ev.entity_f1 === "number" ? `, entity F1 ${ev.entity_f1.toFixed(2)}.` : ".");
    }
  } catch (err) {
    box.textContent = `Model unavailable: ${err.message}`;
    box.className = "model down";
  }
}

// --------------------------------------------------------------- extraction

async function extract() {
  const text = $("text").value;
  if (!text.trim()) {
    setStatus("Paste or upload some protocol text first.", true);
    return;
  }
  if ($("scratch").checked) {
    startScratch(text);
    return;
  }
  $("extract").disabled = true;
  setStatus("Extracting…");
  try {
    const { payload: body } = await postJSON("/v1/extract", { text });
    doc = {
      text,
      cps: Array.from(text),
      modelVersion: body.model.model_version,
      entities: new Map(body.entities.map((e) => [e.id, {
        id: e.id, label: e.label, start: e.start, end: e.end, origin: "model", decision: "accepted",
        original: null }])),
      relations: new Map(body.relations.map((r) => [r.id, {
        id: r.id, head: r.head, label: r.label, tail: r.tail, origin: "model", decision: "accepted" }])),
      review: null,
      dirty: false,
      next: 1,
      selected: null,
      pending: null,
      idempotencyKey: null,
    };
    preview = { sheet: body.sheet, review_items: body.review_items, normalized_values: body.normalized_values };
    $("token-note").hidden = true;
    renderAll();
    const notes = body.warnings.length ? ` ${body.warnings.join(" ")}` : "";
    setStatus(`${body.entities.length} entities, ${body.relations.length} relations, `
      + `${body.review_items.length} items to review.${notes}`);
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    $("extract").disabled = false;
  }
}

function startScratch(text) {
  // Gold annotation: no model call, so suggestions cannot bias the labels. Text must be
  // stored for the annotation to be exportable as a dataset.
  doc = {
    text, cps: Array.from(text), modelVersion: "manual-annotation",
    entities: new Map(), relations: new Map(), review: null, dirty: false, next: 1,
    selected: null, pending: null, idempotencyKey: null,
  };
  preview = { sheet: [], review_items: [], normalized_values: {} };
  $("store-text").checked = true;
  $("token-note").hidden = true;
  renderAll();
  setStatus("Annotating from scratch: select text in the Evidence panel to add each entity.");
}

// ------------------------------------------------------------------ editing

function content() {
  return {
    entities: [...doc.entities.values()].map(({ id, label, start, end, origin, decision, original }) =>
      ({ id, label, start, end, origin, decision, original })),
    relations: [...doc.relations.values()].map(({ id, head, label, tail, origin, decision }) =>
      ({ id, head, label, tail, origin, decision })),
  };
}

function changed() {
  doc.dirty = true;
  doc.idempotencyKey = null;
  renderAll();
  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(refresh, 150);
}

async function refresh() {
  try {
    const { payload } = await postJSON("/v1/preview", { text: doc.text, content: content() });
    preview = payload;
    renderSheet();
    renderReview();
    renderSaveBar();
  } catch (err) {
    setStatus(`Edit not valid: ${err.message}`, true);
  }
}

function editEntity(id, change) {
  const e = doc.entities.get(id);
  if (e.origin === "model" && !e.original) e.original = { label: e.label, start: e.start, end: e.end };
  Object.assign(e, change);
  if (e.origin === "model") {
    const o = e.original;
    const same = o && o.label === e.label && o.start === e.start && o.end === e.end;
    e.decision = same ? "accepted" : "edited";
    if (same) e.original = null;
  }
  changed();
}

function nudge(id, edge, direction) {
  const e = doc.entities.get(id);
  let pos = (edge === "start" ? e.start : e.end) + direction;
  // Move to the next word boundary in the requested direction.
  while (pos > 0 && pos < doc.cps.length && isWord(doc.cps[pos - 1]) && isWord(doc.cps[pos])) pos += direction;
  let start = edge === "start" ? pos : e.start;
  let end = edge === "end" ? pos : e.end;
  // Never let a span gain edge whitespace.
  while (start < end && /\s/u.test(doc.cps[start])) start += 1;
  while (end > start && /\s/u.test(doc.cps[end - 1])) end -= 1;
  if (start < 0 || end > doc.cps.length || start >= end) return;
  editEntity(id, { start, end });
}

function rejectEntity(id) {
  const e = doc.entities.get(id);
  for (const [rid, r] of doc.relations) {
    if (r.head !== id && r.tail !== id) continue;
    if (r.origin === "human") doc.relations.delete(rid);
    else r.decision = "rejected";
  }
  if (e.origin === "human") {
    doc.entities.delete(id);
    doc.selected = null;
  } else {
    e.decision = "rejected";
  }
  changed();
}

function restoreEntity(id) {
  const e = doc.entities.get(id);
  e.decision = e.original ? "edited" : "accepted";
  changed();
}

function toggleRelation(id) {
  const r = doc.relations.get(id);
  if (r.origin === "human") {
    doc.relations.delete(id);
  } else if (r.decision === "rejected") {
    if (!kept(doc.entities.get(r.head)) || !kept(doc.entities.get(r.tail))) {
      setStatus("Restore both entities before restoring this relation.", true);
      return;
    }
    r.decision = "accepted";
  } else {
    r.decision = "rejected";
  }
  changed();
}

function addEntity(start, end, label) {
  const id = `H${doc.next++}`;
  doc.entities.set(id, { id, label, start, end, origin: "human", decision: "added", original: null });
  doc.selected = id;
  doc.pending = null;
  changed();
}

function addRelation(head, label, tail, replace) {
  if (head === tail) return;
  if (replace) {
    for (const [rid, r] of doc.relations) {
      if (r.tail === tail && r.label === label && r.head !== head && r.decision !== "rejected") {
        if (r.origin === "human") doc.relations.delete(rid);
        else r.decision = "rejected";
      }
    }
  }
  const duplicate = [...doc.relations.values()].find((r) => r.head === head && r.tail === tail
    && r.label === label);
  if (duplicate) {
    if (duplicate.decision === "rejected") duplicate.decision = "accepted";
  } else {
    const id = `HR${doc.next++}`;
    doc.relations.set(id, { id, head, label, tail, origin: "human", decision: "added" });
  }
  changed();
}

// ---------------------------------------------------------------- rendering

function chip(id, extra) {
  const entity = doc.entities.get(id);
  const normalized = describeValue(preview.normalized_values[id]);
  const where = `${entity.label} · characters ${entity.start}–${entity.end}`;
  const marks = entity.origin === "human" ? " · added by reviewer"
    : entity.decision === "edited" ? " · edited by reviewer" : "";
  const node = el("button", {
    type: "button",
    class: `value from-${entity.origin}${entity.decision === "edited" ? " edited" : ""}`,
    "data-label": entity.label,
    title: `${where}${marks}${normalized ? `\nNormalized: ${normalized}` : ""}`,
  }, spanText(entity));
  if (entity.origin === "human") node.append(" ", el("span", { class: "badge" }, "human"));
  if (extra) node.append(" ", el("small", {}, extra));
  node.addEventListener("click", () => selectEntity(id));
  return node;
}

function renderEvidence() {
  const container = $("evidence");
  container.replaceChildren();
  if (!doc) return;
  container.classList.remove("empty");
  const { cps } = doc;
  const entities = [...doc.entities.values()];
  const bounds = new Set([0, cps.length]);
  for (const e of entities) {
    bounds.add(e.start);
    bounds.add(e.end);
  }
  const points = [...bounds].sort((a, b) => a - b);
  for (let i = 0; i < points.length - 1; i += 1) {
    const [a, b] = [points[i], points[i + 1]];
    const piece = cps.slice(a, b).join("");
    const covering = entities.filter((e) => e.start <= a && b <= e.end)
      .sort((x, y) => Number(kept(x)) - Number(kept(y)));
    if (covering.length === 0) {
      container.append(el("span", { class: "plain", "data-start": String(a) }, piece));
      continue;
    }
    const top = covering[covering.length - 1];
    const classes = ["span", `from-${top.origin}`];
    if (top.decision === "rejected") classes.push("rejected");
    if (top.decision === "edited") classes.push("edited");
    if (covering.some((e) => e.id === doc.selected)) classes.push("focus");
    const node = el("span", {
      class: classes.join(" "),
      "data-label": top.label,
      "data-start": String(a),
      "data-ids": covering.map((e) => e.id).join(" "),
      title: covering.map((e) => `${e.label} [${e.start}, ${e.end}) · ${e.origin} · ${e.decision}`).join("\n"),
    }, piece);
    node.addEventListener("click", () => {
      if (!window.getSelection().isCollapsed) return;
      selectEntity(top.id);
    });
    container.append(node);
  }
}

function selectEntity(id) {
  doc.selected = id;
  doc.pending = null;
  renderEvidence();
  renderInspector();
  const node = $("evidence").querySelector(".span.focus");
  if (node) node.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function offsetOf(node, offset) {
  const host = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
  if (!host || !host.dataset || host.dataset.start === undefined) return null;
  const within = node.nodeType === Node.TEXT_NODE ? Array.from(node.textContent.slice(0, offset)).length : 0;
  return Number(host.dataset.start) + within;
}

function captureSelection() {
  if (!doc) return;
  const selection = window.getSelection();
  if (selection.isCollapsed || !$("evidence").contains(selection.anchorNode)
      || !$("evidence").contains(selection.focusNode)) return;
  let a = offsetOf(selection.anchorNode, selection.anchorOffset);
  let b = offsetOf(selection.focusNode, selection.focusOffset);
  if (a === null || b === null) return;
  if (a > b) [a, b] = [b, a];
  while (a < b && /\s/u.test(doc.cps[a])) a += 1;
  while (b > a && /\s/u.test(doc.cps[b - 1])) b -= 1;
  if (a >= b) return;
  doc.pending = { start: a, end: b };
  doc.selected = null;
  renderInspector();
}

function relationItem(r) {
  const head = doc.entities.get(r.head);
  const tail = doc.entities.get(r.tail);
  const rejected = r.decision === "rejected";
  const item = el("li", { class: `from-${r.origin}${rejected ? " rejected" : ""}` },
    el("span", { class: "value", "data-label": head.label }, spanText(head)),
    el("span", { class: "rel-label" }, `—${r.label}→`),
    el("span", { class: "value", "data-label": tail.label }, spanText(tail)),
    r.origin === "human" ? el("span", { class: "badge" }, "human") : null);
  const action = r.origin === "human" ? "Remove" : rejected ? "Restore" : "Reject";
  item.append(button(action, (event) => {
    event.stopPropagation();
    toggleRelation(r.id);
  }, "mini"));
  item.addEventListener("click", () => {
    for (const node of $("evidence").querySelectorAll(".span")) {
      const ids = node.dataset.ids.split(" ");
      node.classList.toggle("focus", ids.includes(r.head) || ids.includes(r.tail));
    }
  });
  return item;
}

function renderInspector() {
  const box = $("inspector");
  box.replaceChildren();
  if (!doc) {
    box.hidden = true;
    return;
  }
  box.hidden = false;
  if (doc.pending) {
    const { start, end } = doc.pending;
    let label = "Reagent";
    box.append(
      el("h3", {}, "Add a missing entity"),
      el("p", { class: "quote" }, doc.cps.slice(start, end).join("")),
      el("div", { class: "row" },
        select(ENTITY_LABELS, label, (v) => { label = v; }),
        button("Add as reviewer entity", () => addEntity(start, end, label), "primary"),
        button("Cancel", () => { doc.pending = null; renderInspector(); })),
    );
    return;
  }
  const entity = doc.selected ? doc.entities.get(doc.selected) : null;
  if (!entity) {
    box.append(el("p", { class: "muted" },
      "Select a highlighted span to edit it, or select any text to add a missing entity."));
    return;
  }
  const rejected = entity.decision === "rejected";
  const status = entity.origin === "human" ? "added by reviewer" : entity.decision;
  box.append(el("h3", {}, el("span", { class: "quote" }, spanText(entity)), " ",
    el("span", { class: `badge from-${entity.origin}` }, status)));
  if (entity.original) {
    const o = entity.original;
    box.append(el("p", { class: "muted" },
      `Model said: ${o.label} “${doc.cps.slice(o.start, o.end).join("")}”`));
  }
  const type = select(ENTITY_LABELS, entity.label, (v) => editEntity(entity.id, { label: v }));
  type.disabled = rejected;
  const nudges = [
    ["◀ start", "start", -1], ["start ▶", "start", 1],
    ["◀ end", "end", -1], ["end ▶", "end", 1],
  ].map(([label, edge, dir]) => {
    const b = button(label, () => nudge(entity.id, edge, dir), "mini");
    b.disabled = rejected;
    return b;
  });
  const toggle = entity.origin === "human" ? button("Remove", () => rejectEntity(entity.id))
    : rejected ? button("Restore", () => restoreEntity(entity.id))
      : button("Reject", () => rejectEntity(entity.id));
  box.append(el("div", { class: "row" }, el("label", {}, "Type ", type), ...nudges, toggle));

  const links = [...doc.relations.values()].filter((r) => r.head === entity.id || r.tail === entity.id);
  if (links.length) box.append(el("ul", { class: "relations compact" }, ...links.map(relationItem)));

  if (rejected) return;
  const others = [...doc.entities.values()].filter((e) => e.id !== entity.id && kept(e))
    .sort((a, b) => a.start - b.start);
  if (!others.length) return;
  let other = others[0].id;
  let label = entity.label === "Action" ? "Acts-on" : "Measure";
  let role = entity.label === "Action" ? "head" : "tail";
  // Replacing other links is the "move this value" action: on by default only for a
  // quantity that is the tail. A material can legitimately be acted on by many actions.
  const isQuantity = QUANTITY_LABELS.includes(entity.label);
  let replace = isQuantity && role === "tail";
  const otherSelect = el("select");
  for (const o of others) otherSelect.append(el("option", { value: o.id }, `${spanText(o)} (${o.label})`));
  otherSelect.addEventListener("change", () => { other = otherSelect.value; });
  const replaceBox = el("input", { type: "checkbox", checked: replace });
  replaceBox.addEventListener("change", () => { replace = replaceBox.checked; });
  box.append(el("div", { class: "row add-relation" },
    "This is the ",
    select(["tail", "head"], role, (v) => { role = v; }),
    " of ", otherSelect, " via ",
    select(RELATION_LABELS, label, (v) => { label = v; }),
    el("label", { class: "check" }, replaceBox, " replace other links of this type"),
    button("Add relation", () => {
      const [head, tail] = role === "tail" ? [other, entity.id] : [entity.id, other];
      addRelation(head, label, tail, replace);
    }, "primary")));
}

function cell(ids, emptyText = "—", emptyClass = "none") {
  const td = el("td");
  if (ids.length === 0) td.append(el("span", { class: emptyClass }, emptyText));
  for (const id of ids) td.append(chip(id));
  return td;
}

function renderSheet() {
  const body = $("sheet").querySelector("tbody");
  body.replaceChildren();
  if (!doc || preview.sheet.length === 0) {
    body.append(el("tr", { class: "placeholder" },
      el("td", { colSpan: 6 }, doc ? "No actions recognized." : "No extraction yet.")));
    return;
  }
  for (const row of preview.sheet) {
    const quantities = el("td");
    if (row.quantities.length === 0) quantities.append(el("span", { class: "none" }, "—"));
    for (const q of row.quantities) {
      const of = doc.entities.get(q.of);
      quantities.append(chip(q.entity, of && q.of !== row.action ? `of ${spanText(of)}` : ""));
    }
    const review = row.status === "review_required";
    body.append(el("tr", {},
      cell([row.action]),
      cell(row.materials, "Not explicitly stated", "implicit"),
      quantities,
      cell(row.locations),
      cell(row.conditions),
      el("td", {}, el("span", { class: `status-pill${review ? " review" : ""}`, title: row.issues.join("\n") },
        review ? "Review required" : "Proposed"))));
  }
}

function renderRelations() {
  const list = $("relations");
  list.replaceChildren();
  if (!doc) return;
  const relations = [...doc.relations.values()];
  const keptCount = relations.filter((r) => r.decision !== "rejected").length;
  $("relation-count").textContent = `${keptCount} kept · ${relations.length - keptCount} rejected`;
  for (const r of relations) list.append(relationItem(r));
}

function renderReview() {
  const list = $("review");
  list.replaceChildren();
  $("review-count").textContent = `${preview.review_items.length}`;
  if (!doc) return;
  if (preview.review_items.length === 0) list.append(el("li", { class: "muted" }, "Nothing flagged."));
  for (const item of preview.review_items) {
    const entity = doc.entities.get(item.entity);
    const li = el("li", {}, el("span", { class: "value", "data-label": entity.label }, spanText(entity)),
      " ", item.issue);
    li.addEventListener("click", () => selectEntity(item.entity));
    list.append(li);
  }
}

function renderSaveBar() {
  const saved = Boolean(doc && doc.review);
  $("save").disabled = !doc;
  $("save").textContent = saved ? "Save revision" : "Save review";
  $("store-text").disabled = !doc || saved;
  $("export-json").disabled = !saved || doc.dirty;
  $("export-csv").disabled = !saved || doc.dirty;
  if (!doc) {
    $("save-state").textContent = "Extract a protocol to start reviewing.";
    return;
  }
  const counts = { added: 0, edited: 0, rejected: 0 };
  for (const item of [...doc.entities.values(), ...doc.relations.values()]) {
    const key = item.origin === "human" ? "added" : item.decision;
    if (key in counts) counts[key] += 1;
  }
  const summary = `${counts.added} added \u00b7 ${counts.edited} edited \u00b7 ${counts.rejected} rejected`
    + " (entities and relations)";
  $("save-state").textContent = saved
    ? `Review ${doc.review.id} · revision ${doc.review.revision}`
      + `${doc.dirty ? " · unsaved changes" : " · saved"} · ${summary}`
    : `Not saved · ${summary}`;
}

function renderAll() {
  renderEvidence();
  renderInspector();
  renderSheet();
  renderRelations();
  renderReview();
  renderSaveBar();
}

// ------------------------------------------------------------ save / export

async function save() {
  $("save").disabled = true;
  try {
    if (!doc.review) {
      doc.idempotencyKey = doc.idempotencyKey || crypto.randomUUID();
      const storeText = $("store-text").checked;
      const { payload } = await postJSON("/v1/reviews", {
        text: doc.text, save_text: storeText, model_version: doc.modelVersion, content: content(),
      }, { "Idempotency-Key": doc.idempotencyKey });
      if (!payload.token) throw new Error("This review was already saved; its token was shown earlier.");
      doc.review = { id: payload.id, token: payload.token, revision: payload.revision, storedText: storeText };
      const note = $("token-note");
      note.replaceChildren("Review saved. Keep this access token; it is shown only once: ",
        el("code", {}, payload.token));
      note.hidden = false;
    } else {
      const { payload } = await postJSON(`/v1/reviews/${encodeURIComponent(doc.review.id)}/revisions`,
        { text: doc.text, content: content() }, { "X-Review-Token": doc.review.token });
      doc.review.revision = payload.revision;
    }
    doc.dirty = false;
    setStatus(`Saved revision ${doc.review.revision}.`);
  } catch (err) {
    setStatus(`Save failed: ${err.message}`, true);
  } finally {
    renderSaveBar();
  }
}

async function exportReview(format) {
  try {
    const body = { format };
    if (!doc.review.storedText) body.text = doc.text;
    const { res, payload } = await postJSON(`/v1/reviews/${encodeURIComponent(doc.review.id)}/export`,
      body, { "X-Review-Token": doc.review.token });
    const blob = new Blob([format === "csv" ? payload : JSON.stringify(payload, null, 2)],
      { type: format === "csv" ? "text/csv" : "application/json" });
    const disposition = res.headers.get("content-disposition") || "";
    const name = (disposition.match(/filename="([^"]+)"/) || [])[1] || `review.${format}`;
    const link = el("a", { href: URL.createObjectURL(blob), download: name });
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    setStatus(`Exported ${name}.`);
  } catch (err) {
    setStatus(`Export failed: ${err.message}`, true);
  }
}

// --------------------------------------------------------------------- init

async function readFile(file) {
  if (file.size > 256 * 1024) {
    setStatus("File is larger than 256 KB.", true);
    return;
  }
  try {
    $("text").value = new TextDecoder("utf-8", { fatal: true }).decode(await file.arrayBuffer());
    updateCounter();
    setStatus(`Loaded ${file.name}.`);
  } catch {
    setStatus("That file is not valid UTF-8 text.", true);
  }
}

function init() {
  $("legend").replaceChildren(...LEGEND.map((label) => el("span", { class: "chip", "data-label": label }, label)));
  $("text").addEventListener("input", updateCounter);
  $("text").addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") extract();
  });
  $("extract").addEventListener("click", extract);
  $("scratch").addEventListener("change", () => {
    $("extract").textContent = $("scratch").checked ? "Start annotating" : "Extract";
  });
  $("sample").addEventListener("click", () => {
    $("text").value = SAMPLE;
    updateCounter();
  });
  $("file").addEventListener("change", (event) => {
    const [file] = event.target.files;
    if (file) readFile(file);
    event.target.value = "";
  });
  $("evidence").addEventListener("mouseup", captureSelection);
  $("save").addEventListener("click", save);
  $("export-json").addEventListener("click", () => exportReview("json"));
  $("export-csv").addEventListener("click", () => exportReview("csv"));
  window.addEventListener("beforeunload", (event) => {
    if (doc && doc.dirty) event.preventDefault();
  });
  updateCounter();
  loadModelInfo();
  renderSaveBar();
}

document.addEventListener("DOMContentLoaded", init);
