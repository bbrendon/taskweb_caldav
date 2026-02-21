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

// Close modal on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeModal();
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

// HTMX events: close modal after successful task create/update
document.addEventListener('htmx:afterRequest', function(evt) {
    const target = evt.detail.elt;
    if (target.tagName === 'FORM' && evt.detail.successful) {
        const method = target.getAttribute('hx-post') || target.getAttribute('hx-patch');
        if (method) {
            closeModal();
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

// Search: clear active sidebar filter when searching
document.getElementById('search-input')?.addEventListener('input', function() {
    if (this.value.length > 0) {
        document.querySelectorAll('.sidebar-link').forEach(l => {
            l.classList.remove('bg-blue-50', 'text-blue-700', 'font-medium');
        });
    }
});
