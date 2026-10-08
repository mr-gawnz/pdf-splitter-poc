const form = document.querySelector('#split-form');
const status = document.querySelector('#status');
const download = document.querySelector('#download');
const button = document.querySelector('#split');
let downloadUrl;

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  download.hidden = true;
  if (downloadUrl) {
    URL.revokeObjectURL(downloadUrl);
    downloadUrl = undefined;
  }
  const file = document.querySelector('#pdf').files[0];
  if (!file) return;
  if (file.size > 50 * 1024 * 1024) {
    status.textContent = 'PDF must be 50 MiB or smaller.';
    return;
  }
  const data = new FormData(form);
  data.set('only_landscape', document.querySelector('#landscape').checked.toString());
  button.disabled = true;
  status.textContent = 'Splitting PDF…';
  try {
    const response = await fetch('/api/split', { method: 'POST', body: data });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(typeof error.detail === 'string' ? error.detail : 'Could not split this PDF. Check the file and options.');
    }
    downloadUrl = URL.createObjectURL(await response.blob());
    download.href = downloadUrl;
    download.download = `${file.name.replace(/\.pdf$/i, '')}_split.pdf`;
    download.hidden = false;
    status.textContent = `Done. ${response.headers.get('X-Split-Pages')} page(s) split; ${response.headers.get('X-Untouched-Pages')} left unchanged.`;
  } catch (error) {
    status.textContent = error.message || 'Upload failed. Please try again.';
  } finally {
    button.disabled = false;
  }
});
