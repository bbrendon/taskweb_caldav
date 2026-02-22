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

// Sidebar active state
document.querySelectorAll('.sidebar-link').forEach(link => {
    link.addEventListener('click', function() {
        document.querySelectorAll('.sidebar-link').forEach(l => {
            l.classList.remove('bg-blue-50', 'text-blue-700', 'font-medium');
        });
        this.classList.add('bg-blue-50', 'text-blue-700', 'font-medium');
    });
});

// Search: clear active sidebar filter when searching; show/hide bookmark button
document.getElementById('search-input')?.addEventListener('input', function() {
    if (this.value.length > 0) {
        document.querySelectorAll('.sidebar-link').forEach(l => {
            l.classList.remove('bg-blue-50', 'text-blue-700', 'font-medium');
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
