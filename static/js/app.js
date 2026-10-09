/**
 * =============================================================================
 * PARKFLOW CLIENT JAVASCRIPT CONTROLLER (app.js)
 * RESTful API client interacting with Flask Python Backend & Python Stack
 * =============================================================================
 */

// Application State
let appState = {
  currentPage: 'dashboard',
  allSlots: [],
  activeVehicles: [],
  history: [],
  stackDetails: null,
  selectedExitVehicle: null
};

let searchDebounceTimer = null;

// =============================================================================
// INITIALIZATION
// =============================================================================
document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initModals();
  initMobileMenu();
  loadAllData();

  // Auto-refresh background stats every 15 seconds
  setInterval(() => {
    fetchStatus(false);
  }, 15000);
});

function initNavigation() {
  document.querySelectorAll('.nav-link[data-page]').forEach(button => {
    button.addEventListener('click', () => {
      const page = button.getAttribute('data-page');
      navigateTo(page);
    });
  });
}

function navigateTo(pageId) {
  appState.currentPage = pageId;

  // 1. Update Navigation Menu
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.toggle('active', link.getAttribute('data-page') === pageId);
  });

  // 2. Update Page Views
  document.querySelectorAll('.page-view').forEach(view => {
    view.classList.remove('active');
  });

  const targetView = document.getElementById(`view-${pageId}`);
  if (targetView) {
    targetView.classList.add('active');
  }

  // 3. Update Breadcrumb
  const titles = {
    dashboard: 'Dashboard',
    park: 'Park Vehicle',
    slots: 'Parking Slots Matrix',
    vehicles: 'Parked Vehicles',
    search: 'Vehicle Search',
    history: 'Parking History',
    stack: 'Stack Operations (LIFO)'
  };
  const titleText = titles[pageId] || 'Dashboard';
  const breadcrumbEl = document.getElementById('breadcrumbCurrent');
  if (breadcrumbEl) breadcrumbEl.textContent = titleText;

  // 4. Close mobile sidebar if open
  const sidebar = document.getElementById('sidebar');
  if (sidebar) sidebar.classList.remove('open');

  // 5. Trigger view-specific data refresh
  if (pageId === 'slots') fetchSlots();
  if (pageId === 'vehicles') fetchVehicles();
  if (pageId === 'history') fetchHistory();
  if (pageId === 'stack') fetchStack();
  if (pageId === 'dashboard') fetchStatus();
  
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function initMobileMenu() {
  const toggleBtn = document.getElementById('mobileMenuBtn');
  const sidebar = document.getElementById('sidebar');
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });
  }
}

function initModals() {
  const resetBtn = document.getElementById('btnOpenReset');
  if (resetBtn) {
    resetBtn.addEventListener('click', openResetModal);
  }
}

// =============================================================================
// API DATA FETCHING
// =============================================================================

async function loadAllData() {
  await fetchStatus(true);
  await fetchSlots();
  await fetchVehicles();
}

async function fetchStatus(showLoading = false) {
  try {
    const res = await fetch('/api/status');
    const json = await res.json();
    if (!json.success) return;

    const data = json.data;
    appState.allSlots = data.slots || [];
    appState.activeVehicles = data.active_vehicles || [];
    appState.stackDetails = data.stack_details || null;

    // Update KPI Cards
    updateKPIs(data);

    // Update Dashboard Mini Slots Map
    renderMiniSlots(appState.allSlots);

    // Update Stack Preview Widget
    updateStackPreview(data);

    // Update Dashboard Table
    renderDashVehicles(appState.activeVehicles);

    // Update Next assignable slot on Park page
    const parkNextEl = document.getElementById('parkNextSlotValue');
    if (parkNextEl) {
      parkNextEl.textContent = data.next_available_slot ? `Slot ${data.next_available_slot}` : 'Lot Full';
    }

    // Update DB Badge
    const dbBadge = document.getElementById('dbBadgeText');
    if (dbBadge && json.database_engine) {
      dbBadge.textContent = `Flask + ${json.database_engine}`;
    }
  } catch (err) {
    console.error('Error fetching status:', err);
  }
}

async function fetchSlots() {
  try {
    const res = await fetch('/api/slots');
    const json = await res.json();
    if (!json.success) return;

    appState.allSlots = json.slots || [];
    renderLargeSlots(appState.allSlots);
  } catch (err) {
    console.error('Error fetching slots:', err);
  }
}

async function fetchVehicles() {
  try {
    const res = await fetch('/api/vehicles');
    const json = await res.json();
    if (!json.success) return;

    appState.activeVehicles = json.vehicles || [];
    renderAllActiveVehicles(appState.activeVehicles);
  } catch (err) {
    console.error('Error fetching vehicles:', err);
  }
}

async function fetchHistory() {
  try {
    const res = await fetch('/api/history');
    const json = await res.json();
    if (!json.success) return;

    appState.history = json.history || [];
    renderHistoryTable(appState.history);
  } catch (err) {
    console.error('Error fetching history:', err);
  }
}

async function fetchStack() {
  try {
    const res = await fetch('/api/stack');
    const json = await res.json();
    if (!json.success) return;

    appState.stackDetails = json.stack || null;
    renderStackDisplay(appState.stackDetails);
  } catch (err) {
    console.error('Error fetching stack:', err);
  }
}

// =============================================================================
// DOM RENDERING HELPERS
// =============================================================================

function updateKPIs(data) {
  setText('kpiTotalSlots', data.total_slots);
  setText('kpiAvailableSlots', data.available_slots);
  setText('kpiOccupiedSlots', data.occupied_slots);
  setText('kpiUtilization', `${data.utilization_rate}%`);
}

function updateStackPreview(data) {
  const nextSlotEl = document.getElementById('dashNextSlot');
  if (nextSlotEl) {
    nextSlotEl.textContent = data.next_available_slot !== null ? data.next_available_slot : 'FULL';
    if (data.next_available_slot === null) {
      nextSlotEl.style.fontSize = '1.8rem';
      nextSlotEl.style.color = 'var(--red)';
    } else {
      nextSlotEl.style.fontSize = '2.75rem';
      nextSlotEl.style.color = 'var(--primary)';
    }
  }

  setText('dashStackRatio', `${data.available_slots} / ${data.total_slots} Slots`);

  const barEl = document.getElementById('dashStackBar');
  if (barEl) {
    const pct = Math.round((data.available_slots / data.total_slots) * 100);
    barEl.style.width = `${pct}%`;
  }
}

function renderMiniSlots(slots) {
  const container = document.getElementById('dashSlotsGrid');
  if (!container) return;

  if (!slots || slots.length === 0) {
    container.innerHTML = '<div class="empty-state">No slots initialized.</div>';
    return;
  }

  container.innerHTML = slots.map(slot => {
    const isOccupied = slot.is_occupied === 1 || slot.is_occupied === true;
    const cls = isOccupied ? 'occupied' : 'available';
    const label = isOccupied ? escapeHtml(slot.vehicle_no || 'Occupied') : 'Free';
    const tooltip = isOccupied ? `${slot.vehicle_no} (${slot.owner_name})` : `Slot ${slot.slot_number} Available`;

    return `
      <div class="slot-box ${cls}" title="${tooltip}" onclick="handleSlotClick(${slot.slot_number}, ${isOccupied})">
        <span class="slot-number">${slot.slot_number}</span>
        <span class="slot-vehicle">${label}</span>
      </div>
    `;
  }).join('');
}

function renderLargeSlots(slots) {
  const container = document.getElementById('fullSlotsGrid');
  if (!container) return;

  container.innerHTML = slots.map(slot => {
    const isOccupied = slot.is_occupied === 1 || slot.is_occupied === true;
    const cls = isOccupied ? 'occupied' : 'available';
    const statusText = isOccupied ? 'Occupied' : 'Available';

    return `
      <div class="slot-box ${cls}" onclick="handleSlotClick(${slot.slot_number}, ${isOccupied})">
        <span class="slot-badge">${statusText}</span>
        <span class="slot-number">Slot ${slot.slot_number}</span>
        <span class="slot-vehicle">${isOccupied ? escapeHtml(slot.vehicle_no) : 'Empty Bay'}</span>
        ${isOccupied ? `<span class="slot-status-label">${escapeHtml(slot.owner_name)}</span>` : `<span class="slot-status-label text-green">Ready to Park</span>`}
      </div>
    `;
  }).join('');
}

function renderDashVehicles(vehicles) {
  const tbody = document.getElementById('dashVehiclesTableBody');
  if (!tbody) return;

  if (!vehicles || vehicles.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No vehicles currently parked.</td></tr>';
    return;
  }

  const topVehicles = vehicles.slice(0, 5);
  tbody.innerHTML = topVehicles.map(v => `
    <tr>
      <td><span class="slot-tag">Slot ${v.slot_number}</span></td>
      <td><strong>${escapeHtml(v.vehicle_no)}</strong></td>
      <td>${escapeHtml(v.owner_name)}</td>
      <td>${escapeHtml(v.vehicle_type)}</td>
      <td>${escapeHtml(v.entry_time)}</td>
      <td>
        <button class="btn btn-outline-danger btn-sm" onclick="openExitModal(${v.slot_number}, '${escapeHtml(v.vehicle_no)}', '${escapeHtml(v.owner_name)}', '${escapeHtml(v.entry_time)}')">
          Exit Vehicle
        </button>
      </td>
    </tr>
  `).join('');
}

function renderAllActiveVehicles(vehicles) {
  const tbody = document.getElementById('allActiveVehiclesTableBody');
  const countBadge = document.getElementById('activeVehiclesCountBadge');
  if (countBadge) countBadge.textContent = `${vehicles.length} Parked`;

  if (!tbody) return;

  if (!vehicles || vehicles.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No vehicles currently parked.</td></tr>';
    return;
  }

  tbody.innerHTML = vehicles.map(v => `
    <tr>
      <td><span class="slot-tag">Slot ${v.slot_number}</span></td>
      <td><strong>${escapeHtml(v.vehicle_no)}</strong></td>
      <td>${escapeHtml(v.owner_name)}</td>
      <td>${escapeHtml(v.vehicle_type)}</td>
      <td>${escapeHtml(v.entry_time)}</td>
      <td><span class="badge badge-green">Parked</span></td>
      <td>
        <button class="btn btn-outline-danger btn-sm" onclick="openExitModal(${v.slot_number}, '${escapeHtml(v.vehicle_no)}', '${escapeHtml(v.owner_name)}', '${escapeHtml(v.entry_time)}')">
          Exit Vehicle
        </button>
      </td>
    </tr>
  `).join('');
}

function filterActiveVehicles() {
  const query = (document.getElementById('filterVehiclesInput')?.value || '').toLowerCase().trim();
  const filtered = appState.activeVehicles.filter(v => 
    v.vehicle_no.toLowerCase().includes(query) ||
    v.owner_name.toLowerCase().includes(query) ||
    String(v.slot_number).includes(query)
  );
  renderAllActiveVehicles(filtered);
}

function renderHistoryTable(history) {
  const tbody = document.getElementById('historyTableBody');
  if (!tbody) return;

  if (!history || history.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" class="empty-state">No parking history records yet.</td></tr>';
    return;
  }

  tbody.innerHTML = history.map(item => {
    const isParked = item.status === 'Parked';
    const statusBadge = isParked ? 
      '<span class="badge badge-green">Parked</span>' : 
      '<span class="badge badge-primary">Exited</span>';

    const durationText = item.duration_minutes ? 
      (item.duration_minutes < 60 ? `${item.duration_minutes} min` : `${Math.floor(item.duration_minutes / 60)}h ${item.duration_minutes % 60}m`) : 
      (isParked ? 'Active' : '-');

    return `
      <tr>
        <td>#${item.id}</td>
        <td>${statusBadge}</td>
        <td><span class="slot-tag">Slot ${item.slot_number}</span></td>
        <td><strong>${escapeHtml(item.vehicle_no)}</strong></td>
        <td>${escapeHtml(item.owner_name)}</td>
        <td>${escapeHtml(item.vehicle_type)}</td>
        <td>${escapeHtml(item.entry_time)}</td>
        <td>${item.exit_time ? escapeHtml(item.exit_time) : '-'}</td>
        <td>${durationText}</td>
      </tr>
    `;
  }).join('');
}

function renderStackDisplay(stack) {
  const container = document.getElementById('stackVisualDisplay');
  const countBadge = document.getElementById('stackCountBadge');
  if (!container) return;

  if (!stack || !stack.items_top_to_bottom || stack.items_top_to_bottom.length === 0) {
    if (countBadge) countBadge.textContent = 'Stack Empty (0 Available)';
    container.innerHTML = `
      <div class="empty-state">
        <strong>Stack Underflow!</strong><br>
        All 20 parking slots are currently occupied. The stack is empty.
      </div>
    `;
    return;
  }

  if (countBadge) countBadge.textContent = `${stack.size} Available Slots`;

  const items = stack.items_top_to_bottom; // Top element is at index 0

  container.innerHTML = items.map((slotNo, idx) => {
    const isTop = idx === 0;
    return `
      <div class="stack-slot-card ${isTop ? 'top' : ''}">
        <div class="slot-left">
          <span class="slot-id">Slot ${slotNo}</span>
          ${isTop ? '<span class="top-tag">TOP / PEEK</span>' : ''}
        </div>
        <div class="slot-pointer">
          ${isTop ? 'Next to be popped →' : `Stack index [${items.length - 1 - idx}]`}
        </div>
      </div>
    `;
  }).join('');
}

// =============================================================================
// ACTIONS: VEHICLE ENTRY & EXIT
// =============================================================================

async function handleParkSubmit(event) {
  event.preventDefault();
  const alertBox = document.getElementById('parkFormAlert');
  const submitBtn = document.getElementById('btnSubmitPark');

  const vehicleNo = document.getElementById('inputVehicleNo').value.trim();
  const ownerName = document.getElementById('inputOwnerName').value.trim();
  const vehicleType = document.getElementById('selectVehicleType').value;

  if (!vehicleNo || !ownerName) {
    showAlert(alertBox, 'danger', 'Please provide both vehicle registration number and owner name.');
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = 'Allocating Slot via Python Stack...';

  try {
    const res = await fetch('/api/park', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vehicle_no: vehicleNo, owner_name: ownerName, vehicle_type: vehicleType })
    });

    const result = await res.json();

    if (result.success) {
      showAlert(alertBox, 'success', `Vehicle ${result.data.vehicle_no} allocated to Slot ${result.data.slot_number} (POP operation successful).`);
      showToast(`Vehicle parked in Slot ${result.data.slot_number}`, 'success');

      // Clear input fields
      document.getElementById('inputVehicleNo').value = '';
      document.getElementById('inputOwnerName').value = '';

      // Refresh data
      await loadAllData();
      if (appState.currentPage === 'stack') fetchStack();
    } else {
      showAlert(alertBox, 'danger', result.message || 'Failed to park vehicle.');
      showToast(result.message || 'Parking failed', 'error');
    }
  } catch (err) {
    console.error('Error in handleParkSubmit:', err);
    showAlert(alertBox, 'danger', 'Network or server error while parking vehicle.');
    showToast('Network error', 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
      <span>Allocate Slot & Park Vehicle</span>
    `;
  }
}

function handleSlotClick(slotNumber, isOccupied) {
  if (isOccupied) {
    const vehicle = appState.activeVehicles.find(v => v.slot_number === slotNumber);
    if (vehicle) {
      openExitModal(vehicle.slot_number, vehicle.vehicle_no, vehicle.owner_name, vehicle.entry_time);
    }
  } else {
    // Navigate to park page
    navigateTo('park');
  }
}

function openExitModal(slotNumber, vehicleNo, ownerName, entryTime) {
  appState.selectedExitVehicle = { slotNumber, vehicleNo, ownerName, entryTime };

  setText('exitVehiclePlate', vehicleNo);
  setText('exitSlotNumber', `Slot ${slotNumber}`);
  setText('exitOwnerName', ownerName);
  setText('exitEntryTime', entryTime);

  const modal = document.getElementById('exitModalBackdrop');
  if (modal) modal.classList.add('open');
}

function closeExitModal() {
  const modal = document.getElementById('exitModalBackdrop');
  if (modal) modal.classList.remove('open');
  appState.selectedExitVehicle = null;
}

async function submitExit() {
  if (!appState.selectedExitVehicle) return;

  const btn = document.getElementById('btnConfirmExit');
  btn.disabled = true;
  btn.textContent = 'Processing Exit...';

  const { slotNumber, vehicleNo } = appState.selectedExitVehicle;

  try {
    const res = await fetch('/api/exit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slot_number: slotNumber })
    });

    const result = await res.json();

    if (result.success) {
      closeExitModal();
      showToast(`Slot ${result.data.slot_number} freed! Pushed back to stack.`, 'success');
      await loadAllData();
      if (appState.currentPage === 'vehicles') fetchVehicles();
      if (appState.currentPage === 'history') fetchHistory();
      if (appState.currentPage === 'stack') fetchStack();
    } else {
      showToast(result.message || 'Exit failed', 'error');
    }
  } catch (err) {
    console.error('Error submitting exit:', err);
    showToast('Failed to process vehicle exit', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Confirm Departure';
  }
}

// =============================================================================
// SEARCH
// =============================================================================

function debounceSearch() {
  clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(performSearch, 300);
}

async function performSearch() {
  const query = (document.getElementById('globalSearchInput')?.value || '').trim();
  const heading = document.getElementById('searchResultsHeading');
  const tbody = document.getElementById('searchResultsTableBody');

  if (!query) {
    if (heading) heading.textContent = 'Search Results';
    if (tbody) tbody.innerHTML = '<tr><td colspan="9" class="empty-state">Enter a search keyword to find vehicle records.</td></tr>';
    return;
  }

  if (heading) heading.textContent = `Search Results for "${escapeHtml(query)}"`;

  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    const json = await res.json();

    if (!json.success || !json.results || json.results.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" class="empty-state">No matching vehicle or owner records found for "${escapeHtml(query)}".</td></tr>`;
      return;
    }

    tbody.innerHTML = json.results.map(r => {
      const isParked = r.status === 'Parked';
      const statusBadge = isParked ? 
        '<span class="badge badge-green">Parked</span>' : 
        '<span class="badge badge-primary">Exited</span>';

      const durationText = r.duration_minutes ? 
        (r.duration_minutes < 60 ? `${r.duration_minutes} min` : `${Math.floor(r.duration_minutes / 60)}h ${r.duration_minutes % 60}m`) : 
        (isParked ? 'Active' : '-');

      const actionBtn = isParked ? 
        `<button class="btn btn-outline-danger btn-sm" onclick="openExitModal(${r.slot_number}, '${escapeHtml(r.vehicle_no)}', '${escapeHtml(r.owner_name)}', '${escapeHtml(r.entry_time)}')">Exit</button>` : 
        '-';

      return `
        <tr>
          <td>${statusBadge}</td>
          <td><span class="slot-tag">Slot ${r.slot_number}</span></td>
          <td><strong>${escapeHtml(r.vehicle_no)}</strong></td>
          <td>${escapeHtml(r.owner_name)}</td>
          <td>${escapeHtml(r.vehicle_type)}</td>
          <td>${escapeHtml(r.entry_time)}</td>
          <td>${r.exit_time ? escapeHtml(r.exit_time) : '-'}</td>
          <td>${durationText}</td>
          <td>${actionBtn}</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Error during search:', err);
    tbody.innerHTML = '<tr><td colspan="9" class="empty-state text-danger">Error retrieving search results.</td></tr>';
  }
}

// =============================================================================
// RESET SYSTEM
// =============================================================================

function openResetModal() {
  const modal = document.getElementById('resetModalBackdrop');
  if (modal) modal.classList.add('open');
}

function closeResetModal() {
  const modal = document.getElementById('resetModalBackdrop');
  if (modal) modal.classList.remove('open');
}

async function confirmResetSystem() {
  try {
    const res = await fetch('/api/reset', { method: 'POST' });
    const json = await res.json();
    closeResetModal();

    if (json.success) {
      showToast('Parking system reset to initial 20 slots!', 'success');
      await loadAllData();
      if (appState.currentPage === 'stack') fetchStack();
      if (appState.currentPage === 'history') fetchHistory();
      if (appState.currentPage === 'vehicles') fetchVehicles();
    } else {
      showToast(json.message || 'Reset failed', 'error');
    }
  } catch (err) {
    console.error('Error resetting system:', err);
    showToast('Failed to reset system', 'error');
  }
}

// =============================================================================
// UI HELPERS (TOAST, ALERT, SANITIZATION)
// =============================================================================

function setText(elementId, text) {
  const el = document.getElementById(elementId);
  if (el) el.textContent = text;
}

function showAlert(alertEl, type, message) {
  if (!alertEl) return;
  alertEl.className = `alert-box alert-${type}`;
  alertEl.textContent = message;
  alertEl.classList.remove('d-none');
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, match => {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return map[match];
  });
}

// Export for inline event handlers
window.navigateTo = navigateTo;
window.handleParkSubmit = handleParkSubmit;
window.handleSlotClick = handleSlotClick;
window.openExitModal = openExitModal;
window.closeExitModal = closeExitModal;
window.submitExit = submitExit;
window.openResetModal = openResetModal;
window.closeResetModal = closeResetModal;
window.confirmResetSystem = confirmResetSystem;
window.performSearch = performSearch;
window.debounceSearch = debounceSearch;
window.filterActiveVehicles = filterActiveVehicles;
window.fetchHistory = fetchHistory;
