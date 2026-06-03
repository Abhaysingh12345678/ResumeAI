/* ResumeAI — main.js */

// Auto-dismiss flash messages after 5s
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    document.querySelectorAll('.flash').forEach(el => {
      el.style.transition = 'opacity 0.5s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 500);
    });
  }, 5000);

  // Animate progress bars on page load
  document.querySelectorAll('.progress-fill').forEach(bar => {
    const width = bar.style.width;
    bar.style.width = '0';
    setTimeout(() => { bar.style.width = width; }, 100);
  });

  // File upload visual feedback
  const uploadInput = document.getElementById('resumeUploadInput');
  if (uploadInput) {
    uploadInput.addEventListener('change', () => {
      const label = document.querySelector('label[for="resumeUploadInput"]');
      if (label && uploadInput.files.length > 0) {
        label.textContent = `⏳ Uploading ${uploadInput.files[0].name}…`;
        label.style.opacity = '0.7';
      }
    });
  }

  // Animate stat numbers
  document.querySelectorAll('.stat-value').forEach(el => {
    const raw = el.textContent.trim();
    const num = parseFloat(raw.replace('%', '').replace(',', ''));
    if (!isNaN(num) && num > 0) {
      let start = 0;
      const step = num / 30;
      const timer = setInterval(() => {
        start = Math.min(start + step, num);
        el.textContent = raw.includes('%')
          ? Math.round(start) + '%'
          : Math.round(start).toString();
        if (start >= num) clearInterval(timer);
      }, 30);
    }
  });
});
