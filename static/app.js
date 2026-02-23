// Sidebar management (mobile slide-over)
function openSidebar() {
    document.getElementById('sidebar').classList.remove('-translate-x-full');
    document.getElementById('sidebar-backdrop').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeSidebar() {
    document.getElementById('sidebar').classList.add('-translate-x-full');
    document.getElementById('sidebar-backdrop').classList.add('hidden');
    document.body.style.overflow = '';
}

// Auto-close sidebar on mobile when any link inside it is clicked
document.getElementById('sidebar').addEventListener('click', function(e) {
    if (window.innerWidth < 768 && e.target.closest('a, button[hx-get]')) {
        closeSidebar();
    }
});

// Modal management
function openModal() {
    document.getElementById('modal').classList.remove('hidden');
    document.getElementById('modal-overlay').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    document.getElementById('modal').classList.add('hidden');
    document.getElementById('modal-overlay').classList.add('hidden');
    document.body.style.overflow = '';
}

// Close modal or sidebar on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeModal();
        closeSidebar();
    }
});

// Recurrence select handler
function handleRecurrenceChange(select) {
    const container = document.getElementById('custom-rrule-container');
    const customInput = document.getElementById('custom-rrule-input');
    if (select.value === 'custom') {
        container.classList.remove('hidden');
        // Disable the select's value from being submitted, use custom input instead
        select.removeAttribute('name');
        customInput.setAttribute('name', 'recurrence');
    } else {
        container.classList.add('hidden');
        select.setAttribute('name', 'recurrence');
        customInput.removeAttribute('name');
    }
}

// HTMX events: close modal after successful task create/update, or close save panel
document.addEventListener('htmx:afterRequest', function(evt) {
    const target = evt.detail.elt;
    if (target.tagName === 'FORM' && evt.detail.successful) {
        const method = target.getAttribute('hx-post') || target.getAttribute('hx-patch');
        if (method) {
            if (target.closest('#save-search-panel')) {
                hideSavePanel();
            } else {
                closeModal();
            }
        }
    }
});

// Sidebar active state + clear search on quick filter click (event delegation)
document.getElementById('sidebar').addEventListener('click', function(e) {
    const link = e.target.closest('.sidebar-link');
    if (!link) return;
    document.querySelectorAll('.sidebar-link').forEach(l => {
        l.classList.remove('bg-blue-900', 'text-blue-300', 'font-medium');
    });
    link.classList.add('bg-blue-900', 'text-blue-300', 'font-medium');
    const input = document.getElementById('search-input');
    if (input) input.value = '';
    const btn = document.getElementById('save-search-btn');
    if (btn) btn.classList.add('hidden');
});

// Search: clear active sidebar filter when searching; show/hide bookmark button
document.getElementById('search-input')?.addEventListener('input', function() {
    if (this.value.length > 0) {
        document.querySelectorAll('.sidebar-link').forEach(l => {
            l.classList.remove('bg-blue-900', 'text-blue-300', 'font-medium');
        });
    }
    const btn = document.getElementById('save-search-btn');
    if (btn) btn.classList.toggle('hidden', !this.value.trim());
});

// Saved searches: show save panel with current query pre-filled
function showSavePanel() {
    document.getElementById('save-search-query').value =
        document.getElementById('search-input').value;
    const panel = document.getElementById('save-search-panel');
    panel.classList.remove('hidden');
    document.getElementById('save-search-name').focus();
}

function hideSavePanel() {
    document.getElementById('save-search-panel').classList.add('hidden');
    document.getElementById('save-search-name').value = '';
}

// Run a saved search: set the search input and trigger HTMX fetch
function runSavedSearch(el) {
    const q = el.dataset.query;
    const input = document.getElementById('search-input');
    input.value = q;
    // Show bookmark button since input now has content
    const btn = document.getElementById('save-search-btn');
    if (btn) btn.classList.remove('hidden');
    htmx.ajax('GET', '/search?q=' + encodeURIComponent(q), { target: '#task-list', swap: 'innerHTML' });
}

// Location search — initialised when the task form is loaded into the modal
function initLocationSearch() {
    const searchInput = document.getElementById('loc-search-input');
    const dropdown = document.getElementById('loc-dropdown');
    if (!searchInput || !dropdown) return;

    // Wire preset buttons
    document.querySelectorAll('.loc-preset-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            selectLocation(JSON.parse(this.dataset.preset));
        });
    });

    let debounceTimer = null;

    searchInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        const q = this.value.trim();
        if (!q) { dropdown.classList.add('hidden'); return; }
        debounceTimer = setTimeout(() => {
            fetch('/locations/search?q=' + encodeURIComponent(q))
                .then(r => r.json())
                .then(results => {
                    dropdown.innerHTML = '';
                    if (!results.length) {
                        dropdown.classList.add('hidden');
                        return;
                    }
                    results.forEach((r, i) => {
                        const btn = document.createElement('button');
                        btn.type = 'button';
                        btn.className = 'w-full text-left px-3 py-2 text-sm hover:bg-blue-50 focus:bg-blue-50 focus:outline-none border-b border-gray-100 last:border-0';
                        btn.innerHTML = '<span class="font-medium">' + escapeHtml(r.title) + '</span>' +
                            '<br><span class="text-xs text-gray-400">' + escapeHtml(r.address) + '</span>';
                        btn.addEventListener('click', () => selectLocation(r));
                        dropdown.appendChild(btn);
                    });
                    dropdown.classList.remove('hidden');
                })
                .catch(() => dropdown.classList.add('hidden'));
        }, 300);
    });

    // Keyboard: close dropdown on Escape
    searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') dropdown.classList.add('hidden');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function handler(e) {
        if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.classList.add('hidden');
        }
    });
}

function selectLocation(obj) {
    document.getElementById('loc-title-input').value = obj.title || '';
    document.getElementById('loc-address-input').value = obj.address || '';
    document.getElementById('loc-lat-input').value = obj.lat || '';
    document.getElementById('loc-lng-input').value = obj.lng || '';
    document.getElementById('loc-selected-label').textContent = obj.title || '';

    const picker = document.getElementById('loc-picker');
    const selected = document.getElementById('loc-selected');
    if (picker) picker.classList.add('hidden');
    if (selected) selected.classList.remove('hidden');

    const dropdown = document.getElementById('loc-dropdown');
    if (dropdown) dropdown.classList.add('hidden');
}

function clearLocation() {
    document.getElementById('loc-title-input').value = '';
    document.getElementById('loc-address-input').value = '';
    document.getElementById('loc-lat-input').value = '';
    document.getElementById('loc-lng-input').value = '';
    document.getElementById('loc-selected-label').textContent = '';

    const searchInput = document.getElementById('loc-search-input');
    if (searchInput) searchInput.value = '';

    const picker = document.getElementById('loc-picker');
    const selected = document.getElementById('loc-selected');
    if (picker) picker.classList.remove('hidden');
    if (selected) selected.classList.add('hidden');
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// Re-wire location search when the task form is loaded into the modal via HTMX
document.addEventListener('htmx:afterSwap', function(e) {
    if (e.detail.target && e.detail.target.id === 'modal-content') {
        initLocationSearch();
    }
});
