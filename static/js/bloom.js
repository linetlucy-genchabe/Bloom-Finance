// Sidebar toggle
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('overlay').classList.toggle('show');
}
function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('overlay').classList.remove('show');
}

// Auto-dismiss messages
document.querySelectorAll('.message').forEach(msg => {
  setTimeout(() => msg.style.opacity = '0', 4000);
  setTimeout(() => msg.remove(), 4400);
});

// PIN keypad logic
function initPinKeypad(maxLen = 6) {
  const form = document.getElementById('pin-form');
  const input = document.getElementById('pin-input');
  const dots = document.querySelectorAll('.pin-dot');
  if (!input) return;

  function updateDots() {
    dots.forEach((d, i) => d.classList.toggle('filled', i < input.value.length));
  }

  document.querySelectorAll('.pin-key').forEach(key => {
    key.addEventListener('click', () => {
      const val = key.dataset.val;
      if (val === 'clear') {
        input.value = input.value.slice(0, -1);
      } else if (val === 'submit') {
        if (input.value.length >= 4) form.submit();
      } else if (input.value.length < maxLen) {
        input.value += val;
        if (input.value.length === maxLen) setTimeout(() => form.submit(), 200);
      }
      updateDots();
    });
  });

  document.addEventListener('keydown', e => {
    if (e.key >= '0' && e.key <= '9' && input.value.length < maxLen) {
      input.value += e.key;
      if (input.value.length === maxLen) setTimeout(() => form.submit(), 200);
    } else if (e.key === 'Backspace') {
      input.value = input.value.slice(0, -1);
    } else if (e.key === 'Enter' && input.value.length >= 4) {
      form.submit();
    }
    updateDots();
  });
}

// Confirm delete
function confirmDelete(formId, name) {
  if (confirm(`Delete "${name}"? This cannot be undone.`)) {
    document.getElementById(formId).submit();
  }
}

// Chart defaults
if (typeof Chart !== 'undefined') {
  Chart.defaults.font.family = "'Poppins', sans-serif";
  Chart.defaults.color = '#7A6B8A';
}

// Animate progress bars on load
window.addEventListener('load', () => {
  document.querySelectorAll('.progress-fill[data-width]').forEach(el => {
    el.style.width = el.dataset.width + '%';
  });
});

// Emoji picker shortcut
document.querySelectorAll('.emoji-pick').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = document.getElementById(btn.dataset.target);
    if (target) target.value = btn.textContent;
    document.querySelectorAll('.emoji-pick').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
  });
});
