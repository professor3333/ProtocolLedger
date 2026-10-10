"use strict";

// Offsets from the API are Unicode code points. JavaScript strings index UTF-16 code
// units, so all slicing goes through an array of code points.
const SAMPLE = [
  "Example protocol",
  "Add 5 mL of water to the tube, then mix for 30 s.",
  "Centrifuge at 14,000 x g for 10 min at 4 °C.",
  "Transfer the supernatant to a new tube and incubate overnight at room temperature.",
].join("\n");

const LEGEND = ["Action", "Reagent", "Amount", "Location", "Device", "Time", "Temperature", "Modifier"];

const $ = (id) => document.getElementById(id);
let current = null; // { text, cps, entities: Map, relations }

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("data-")) node.setAttribute(key, value);
    else node[key] = value;
  }
  for (const child of children) {
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function setStatus(message, isError = false) {
  const status = $("status");
  status.textContent = message;
  status.classList.toggle("error", isError);
}

function updateCounter() {
  const n = Array.from($("text").value).length;
  $("counter").textContent = `${n.toLocaleString()} characters`;
}

async function loadModelInfo() {
  const box = $("model-info");
  try {
    const res = await fetch("/readyz");
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || "model not ready");
    box.textContent = `${body.system} · ${body.model_version}`;
    box.title = `bundle ${body.bundle_sha256}`;
    box.className = "model ready";
  } catch (err) {
    box.textContent = `Model unavailable: ${err.message}`;
    box.className = "model down";
  }
}

function spanText(entity) {
  return current.cps.slice(entity.start, entity.end).join("");
}

function renderEvidence() {
  const container = $("evidence");
  container.replaceChildren();
  container.classList.remove("empty");
  const { cps } = current;
  const bounds = new Set([0, cps.length]);
  for (const e of current.entities.values()) {
    bounds.add(e.start);
    bounds.add(e.end);
  }
  const points = [...bounds].sort((a, b) => a - b);
  for (let i = 0; i < points.length - 1; i += 1) {
    const [a, b] = [points[i], points[i + 1]];
    const piece = cps.slice(a, b).join("");
    const covering = [...current.entities.values()].filter((e) => e.start <= a && b <= e.end);
    if (covering.length === 0) {
      container.append(document.createTextNode(piece));
      continue;
    }
    const top = covering[covering.length - 1];
    const node = el("span", {
      class: "span",
      "data-label": top.label,
      "data-ids": covering.map((e) => e.id).join(" "),
      title: covering.map((e) => `${e.label} [${e.start}, ${e.end})`).join("\n"),
    }, piece);
    node.addEventListener("click", () => focusEntities(covering.map((e) => e.id)));
    container.append(node);
  }
}

function focusEntities(ids) {
  const wanted = new Set(ids);
  let first = null;
  for (const node of $("evidence").querySelectorAll(".span")) {
    const hit = node.dataset.ids.split(" ").some((id) => wanted.has(id));
    node.classList.toggle("focus", hit);
    if (hit && !first) first = node;
  }
  if (first) first.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function describeValue(v) {
  if (!v) return "";
  const unit = v.unit ? ` ${v.unit}` : "";
  const q = v.qualifier ? `${v.qualifier} ` : "";
  if (v.kind === "number") return `${q}${v.value}${unit}`;
  if (v.kind === "range") return `${q}${v.low}\u2013${v.high}${unit}`;
  if (v.kind === "ratio") return `${v.numerator}:${v.denominator}`;
  return String(v.value);
}

function valueChip(id, extra) {
  const entity = current.entities.get(id);
  const normalized = describeValue(current.normalized[id]);
  const where = `${entity.label} \u00b7 characters ${entity.start}\u2013${entity.end}`;
  const chip = el("button", { type: "button", class: "value", "data-label": entity.label,
    title: normalized ? `${where}\nNormalized: ${normalized}` : where }, spanText(entity));
  if (extra) chip.append(" ", el("small", {}, extra));
  chip.addEventListener("click", () => focusEntities([id]));
  return chip;
}

function cell(ids, emptyText = "—", emptyClass = "none") {
  const td = el("td");
  if (ids.length === 0) td.append(el("span", { class: emptyClass }, emptyText));
  for (const id of ids) td.append(valueChip(id));
  return td;
}

function renderSheet(rows) {
  const body = $("sheet").querySelector("tbody");
  body.replaceChildren();
  if (rows.length === 0) {
    body.append(el("tr", { class: "placeholder" }, el("td", { colSpan: 6 }, "No actions recognized.")));
    return;
  }
  for (const row of rows) {
    const quantities = el("td");
    if (row.quantities.length === 0) quantities.append(el("span", { class: "none" }, "—"));
    for (const q of row.quantities) {
      const of = current.entities.get(q.of);
      quantities.append(valueChip(q.entity, of && q.of !== row.action ? `of ${spanText(of)}` : ""));
    }
    const review = row.status === "review_required";
    const status = el("td", {}, el("span", {
      class: `status-pill${review ? " review" : ""}`, title: row.issues.join("\n"),
    }, review ? "Review required" : "Proposed"));
    body.append(el("tr", {},
      cell([row.action]),
      cell(row.materials, "Not explicitly stated", "implicit"),
      quantities,
      cell(row.locations),
      cell(row.conditions),
      status,
    ));
  }
}

function renderRelations(relations) {
  const list = $("relations");
  list.replaceChildren();
  $("relation-count").textContent = `${relations.length}`;
  for (const r of relations) {
    const head = current.entities.get(r.head);
    const tail = current.entities.get(r.tail);
    const item = el("li", {}, el("span", { class: "value", "data-label": head.label }, spanText(head)),
      el("span", { class: "rel-label" }, `—${r.label}→`),
      el("span", { class: "value", "data-label": tail.label }, spanText(tail)));
    item.addEventListener("click", () => focusEntities([r.head, r.tail]));
    list.append(item);
  }
}

function renderReview(items) {
  const list = $("review");
  list.replaceChildren();
  $("review-count").textContent = `${items.length}`;
  if (items.length === 0) list.append(el("li", { class: "muted" }, "Nothing flagged."));
  for (const item of items) {
    const entity = current.entities.get(item.entity);
    const li = el("li", {}, el("span", { class: "value", "data-label": entity.label }, spanText(entity)),
      " ", item.issue);
    li.addEventListener("click", () => focusEntities([item.entity]));
    list.append(li);
  }
}

async function extract() {
  const text = $("text").value;
  if (!text.trim()) {
    setStatus("Paste or upload some protocol text first.", true);
    return;
  }
  const button = $("extract");
  button.disabled = true;
  setStatus("Extracting…");
  try {
    const res = await fetch("/v1/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const body = await res.json();
    if (!res.ok) {
      const detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join("; ") : body.detail;
      throw new Error(detail || `request failed (${res.status})`);
    }
    current = {
      text,
      cps: Array.from(text),
      entities: new Map(body.entities.map((e) => [e.id, e])),
      normalized: body.normalized_values,
    };
    renderEvidence();
    renderSheet(body.sheet);
    renderRelations(body.relations);
    renderReview(body.review_items);
    const notes = body.warnings.length ? ` ${body.warnings.join(" ")}` : "";
    setStatus(`${body.entities.length} entities, ${body.relations.length} relations, `
      + `${body.review_items.length} items to review.${notes}`);
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    button.disabled = false;
  }
}

async function readFile(file) {
  if (file.size > 256 * 1024) {
    setStatus("File is larger than 256 KB.", true);
    return;
  }
  try {
    const bytes = await file.arrayBuffer();
    $("text").value = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
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
  $("sample").addEventListener("click", () => {
    $("text").value = SAMPLE;
    updateCounter();
  });
  $("file").addEventListener("change", (event) => {
    const [file] = event.target.files;
    if (file) readFile(file);
    event.target.value = "";
  });
  updateCounter();
  loadModelInfo();
}

document.addEventListener("DOMContentLoaded", init);
