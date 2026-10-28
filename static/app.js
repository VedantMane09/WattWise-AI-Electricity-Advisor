const $ = (id) => document.getElementById(id);
const colors = ["#25b875", "#4f8fe8", "#f2a24d", "#9b82dc", "#22a6a1", "#e77986", "#7f9b8a", "#d2b24c"];
let state = {items: [], settings: {rate: 8, days_per_month: 30}, summary: {}, recommendations: []};
let catalog = [];
let toastTimer;

function money(value) {
  return new Intl.NumberFormat("en-IN", {style:"currency", currency:"INR", maximumFractionDigits:2}).format(Number(value || 0));
}
function num(value, digits=1) {
  return Number(value || 0).toLocaleString("en-IN", {minimumFractionDigits:digits, maximumFractionDigits:digits});
}
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function iconFor(category) {
  return ({Lighting:"💡",Cooling:"🌀",Entertainment:"📺",Computing:"💻",Kitchen:"🍳",Laundry:"🧺",Household:"🧹",Bathroom:"🚿",Utility:"⚙️",Electronics:"🔌"})[category] || "⚡";
}
function showToast(message) {
  $("toast").textContent = message;
  $("toast").classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => $("toast").classList.remove("show"), 2600);
}
async function api(url, options={}) {
  const response = await fetch(url, {headers: {"Content-Type":"application/json"}, ...options});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Something went wrong. Please try again.");
  return data;
}
async function refresh() {
  state = await api("/api/state");
  renderAll();
}
function renderAll() {
  renderSummary();
  renderItems();
  renderCharts();
  renderRecommendations();
  renderSimulatorOptions();
  $("headerRate").textContent = money(state.settings.rate) + "/unit";
  $("bannerUnits").innerHTML = `${num(state.summary.total_monthly_kwh)} <small>kWh</small>`;
  $("days").value = state.settings.days_per_month;
}
function renderSummary() {
  const s = state.summary;
  $("totalKwh").innerHTML = `${num(s.total_monthly_kwh)} <small>kWh</small>`;
  $("totalCost").textContent = money(s.total_monthly_cost);
  $("topAppliance").textContent = s.top_appliance || "—";
  $("topKwh").textContent = s.item_count ? `${num(s.top_kwh)} kWh estimated per month` : "Add appliances to begin";
  $("itemCount").textContent = s.item_count || 0;
}
function renderItems() {
  const body = $("applianceRows");
  if (!state.items.length) {
    body.innerHTML = '<tr><td colspan="6" class="empty-state">No appliances yet. Add one to start your energy analysis.</td></tr>';
    return;
  }
  body.innerHTML = state.items.map(item => `
    <tr>
      <td><div class="appliance-cell"><div class="appliance-emoji">${iconFor(item.category)}</div><div><span class="appliance-name">${escapeHtml(item.name)}</span><span class="appliance-category">${escapeHtml(item.category)}</span></div></div></td>
      <td><div class="power-cell"><strong>${num(item.watts,0)} W × ${item.quantity}</strong><small>${escapeHtml(item.source)}</small></div></td>
      <td><div class="usage-cell"><strong>${num(item.hours_per_day,2)} h/day</strong><small>${item.days_per_month} days/mo</small></div></td>
      <td><strong>${num(item.monthly_kwh)}</strong> <span class="muted">kWh</span></td>
      <td class="cost-cell">${money(item.monthly_cost)}</td>
      <td><div class="row-actions"><button class="mini-action" data-edit="${item.id}" aria-label="Edit ${escapeHtml(item.name)}">Edit</button><button class="mini-action" data-delete="${item.id}" aria-label="Delete ${escapeHtml(item.name)}">×</button></div></td>
    </tr>`).join("");
  body.querySelectorAll("[data-edit]").forEach(btn => btn.addEventListener("click", () => openEdit(Number(btn.dataset.edit))));
  body.querySelectorAll("[data-delete]").forEach(btn => btn.addEventListener("click", () => removeItem(Number(btn.dataset.delete))));
}
function renderCharts() {
  const items = [...state.items].sort((a,b) => b.monthly_kwh-a.monthly_kwh);
  const total = state.summary.total_monthly_kwh || 0;
  $("donutTotal").textContent = num(total);
  if (!items.length || total <= 0) {
    $("donutChart").style.background = "conic-gradient(#dce7df 0 100%)";
    $("chartLegend").innerHTML = '<p class="muted">Your appliance breakdown will appear here.</p>';
    $("barChart").innerHTML = '<p class="muted">Add an appliance to view comparisons.</p>';
    return;
  }
  let current = 0;
  const segments = items.map((item, i) => {
    const start = current;
    current += item.monthly_kwh / total * 100;
    return `${colors[i % colors.length]} ${start}% ${current}%`;
  });
  $("donutChart").style.background = `conic-gradient(${segments.join(",")})`;
  $("chartLegend").innerHTML = items.slice(0,5).map((item,i) => `
    <div class="legend-row"><span class="legend-dot" style="background:${colors[i%colors.length]}"></span><span class="legend-name">${escapeHtml(item.name)}</span><span class="legend-value">${Math.round(item.monthly_kwh/total*100)}%</span></div>`).join("");
  const max = Math.max(...items.map(i => i.monthly_kwh), 1);
  $("barChart").innerHTML = items.slice(0,5).map((item,i) => `
    <div class="bar-row"><span class="bar-name">${escapeHtml(item.name)}</span><div class="bar-track"><div class="bar-fill" style="width:${Math.max(0,Math.min(100,item.monthly_kwh/max*100))}%;background:${colors[i%colors.length]}"></div></div><span class="bar-value">${num(item.monthly_kwh)} kWh</span></div>`).join("");
}
function renderRecommendations() {
  const recs = state.recommendations || [];
  $("recommendations").innerHTML = recs.map(rec => `
    <div class="recommendation" data-level="${escapeHtml(rec.level)}">
      <div class="rec-symbol">${rec.level==="high"?"↗":rec.level==="medium"?"◈":"✦"}</div>
      <div><strong>${escapeHtml(rec.title)}</strong><p>${escapeHtml(rec.body)}</p></div>
    </div>`).join("");
}
function renderSimulatorOptions() {
  const select = $("simAppliance");
  const old = select.value;
  select.innerHTML = '<option value="">Choose from your appliances</option>' + state.items.map(i => `<option value="${i.id}">${escapeHtml(i.name)} (${num(i.watts,0)} W)</option>`).join("");
  if (state.items.some(i => String(i.id) === old)) select.value = old;
  if (!select.value && state.items.length) select.value = String(state.items[0].id);
  updateSimulatorDefaults();
}
function updateSimulatorDefaults() {
  const item = state.items.find(i => String(i.id) === $("simAppliance").value);
  if (item) {
    $("currentHours").value = item.hours_per_day;
    $("proposedHours").value = Math.max(0, item.hours_per_day - 1);
  }
}
function openModal() {
  $("modalBackdrop").hidden = false;
  $("formError").textContent = "";
  $("catalogSearch").value = "";
  renderCatalog("");
  $("applianceName").focus();
}
function closeModal() {
  $("modalBackdrop").hidden = true;
  $("applianceForm").reset();
  $("itemId").value = "";
  $("modalTitle").textContent = "Add an appliance";
  $("saveButton").textContent = "Save appliance";
  $("wattageInfo").innerHTML = '<span>ⓘ</span><p>Choose an appliance above to see a typical range and where to verify its rating. Generic values are estimates, not exact specifications.</p>';
}
function applyCatalog(item) {
  $("applianceName").value = item.name;
  $("category").value = item.category;
  $("watts").value = item.default_w;
  $("source").value = "Estimated";
  $("wattageInfo").innerHTML = `<span>ⓘ</span><p><strong>Typical illustrative range: ${item.min_w}–${item.max_w} W.</strong> ${escapeHtml(item.note)} The suggested default is ${item.default_w} W and may differ from your model. Select “Appliance label” or “Manufacturer specification” when you verify it.</p>`;
  document.querySelectorAll(".catalog-option").forEach(btn => btn.classList.toggle("selected", btn.dataset.name === item.name));
}
function renderCatalog(query) {
  const q = query.toLowerCase().trim();
  const list = catalog.filter(item => item.name.toLowerCase().includes(q) || item.category.toLowerCase().includes(q)).slice(0,8);
  $("catalogSuggestions").innerHTML = list.map(item => `
    <button type="button" class="catalog-option" data-name="${escapeHtml(item.name)}">
      <strong>${iconFor(item.category)} ${escapeHtml(item.name)}</strong>
      <span>${item.min_w}–${item.max_w} W typical range · default ${item.default_w} W</span>
    </button>`).join("");
  $("catalogSuggestions").querySelectorAll(".catalog-option").forEach(btn => {
    btn.addEventListener("click", () => {
      const item = catalog.find(c => c.name === btn.dataset.name);
      if (item) applyCatalog(item);
    });
  });
}
function openEdit(id) {
  const item = state.items.find(i => i.id === id);
  if (!item) return;
  openModal();
  $("modalTitle").textContent = "Edit appliance";
  $("saveButton").textContent = "Save changes";
  $("itemId").value = item.id;
  $("applianceName").value = item.name;
  $("category").value = item.category;
  $("watts").value = item.watts;
  $("quantity").value = item.quantity;
  $("hours").value = item.hours_per_day;
  $("days").value = item.days_per_month;
  $("source").value = item.source;
  $("catalogSearch").value = item.name;
  const match = catalog.find(c => c.name.toLowerCase() === item.name.toLowerCase());
  if (match) applyCatalog(match);
  $("watts").value = item.watts;
  $("source").value = item.source;
}
async function removeItem(id) {
  const item = state.items.find(i => i.id === id);
  if (!item || !confirm(`Remove ${item.name} from your appliance list?`)) return;
  try { await api(`/api/items/${id}`, {method:"DELETE"}); await refresh(); showToast("Appliance removed."); }
  catch (err) { showToast(err.message); }
}
function formData() {
  return {
    name: $("applianceName").value.trim(),
    category: $("category").value,
    watts: $("watts").value,
    quantity: $("quantity").value,
    hours_per_day: $("hours").value,
    days_per_month: $("days").value,
    source: $("source").value
  };
}
async function saveItem(event) {
  event.preventDefault();
  $("formError").textContent = "";
  const id = $("itemId").value;
  try {
    await api(id ? `/api/items/${id}` : "/api/items", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(formData())
    });
    closeModal();
    await refresh();
    showToast(id ? "Appliance updated." : "Appliance added.");
  } catch (err) { $("formError").textContent = err.message; }
}
async function runSimulation(event) {
  event.preventDefault();
  const item = state.items.find(i => String(i.id) === $("simAppliance").value);
  if (!item) { showToast("Add an appliance before running a simulation."); return; }
  const resultBox = $("simResult");
  try {
    const result = await api("/api/simulate", {
      method:"POST",
      body:JSON.stringify({
        watts:item.watts, quantity:item.quantity,
        current_hours:$("currentHours").value, proposed_hours:$("proposedHours").value,
        days:item.days_per_month, rate:state.settings.rate
      })
    });
    const positive = result.saved_kwh >= 0;
    resultBox.innerHTML = `<span class="result-icon">${positive?"↗":"↘"}</span><div><strong>${positive?"Estimated monthly difference":"Proposed usage increases consumption"}</strong><span class="result-number">${positive?money(result.saved_cost)+" possible saving":money(Math.abs(result.saved_cost))+" extra cost"}</span><p>${num(Math.abs(result.saved_kwh))} kWh ${positive?"less":"more"} per month if usage changes from ${num($("currentHours").value,2)} to ${num($("proposedHours").value,2)} hours/day. ${escapeHtml(result.message)}</p></div>`;
  } catch (err) {
    resultBox.innerHTML = `<span class="result-icon">!</span><div><strong>Unable to calculate</strong><p>${escapeHtml(err.message)}</p></div>`;
  }
}
async function saveRate() {
  const current = state.settings.rate;
  const entered = prompt("Enter your electricity energy rate in ₹ per kWh (unit). This is an estimate; actual bills may include slab rates and fixed charges.", current);
  if (entered === null) return;
  try {
    await api("/api/settings", {method:"POST", body:JSON.stringify({rate:entered, days_per_month:state.settings.days_per_month})});
    await refresh(); showToast("Electricity rate updated.");
  } catch (err) { showToast(err.message); }
}

async function init() {
  catalog = await api("/api/catalog");
  await refresh();
  $("openAdd").addEventListener("click", openModal);
  $("closeModal").addEventListener("click", closeModal);
  $("cancelModal").addEventListener("click", closeModal);
  $("modalBackdrop").addEventListener("click", e => { if (e.target === $("modalBackdrop")) closeModal(); });
  $("applianceForm").addEventListener("submit", saveItem);
  $("catalogSearch").addEventListener("input", e => renderCatalog(e.target.value));
  $("simForm").addEventListener("submit", runSimulation);
  $("simAppliance").addEventListener("change", updateSimulatorDefaults);
  $("mobileMenu").addEventListener("click", () => $("sidebar").classList.toggle("open"));
  document.querySelectorAll(".nav-link").forEach(link => link.addEventListener("click", () => $("sidebar").classList.remove("open")));
  $("headerRate").parentElement.parentElement.style.cursor = "pointer";
  $("headerRate").parentElement.parentElement.title = "Click to change the electricity rate";
  $("headerRate").parentElement.parentElement.addEventListener("click", saveRate);
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !$("modalBackdrop").hidden) closeModal(); });
}
init().catch(err => showToast("Could not load application: " + err.message));
