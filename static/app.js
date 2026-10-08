const form = document.querySelector('#split-form');
const status = document.querySelector('#status');
const download = document.querySelector('#download');
const button = document.querySelector('#split');
const input = document.querySelector('#pdf');
const dropZone = document.querySelector('#drop-zone');
const selectedFile = document.querySelector('#selected-file');
const result = document.querySelector('#result');
const buttonLabel = document.querySelector('#button-label');
const actionHint = document.querySelector('.action-hint');
let downloadUrl;
let processing = false;
let dragDepth = 0;

function formatSize(bytes) {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MiB` : `${(bytes / 1024).toFixed(1)} KiB`;
}

function setStatus(message, state = '') {
  status.textContent = message;
  status.dataset.state = state;
}

function clearResult() {
  result.hidden = true;
  download.hidden = true;
  download.removeAttribute('href');
  if (downloadUrl) {
    URL.revokeObjectURL(downloadUrl);
    downloadUrl = undefined;
  }
}

function updateFile() {
  clearResult();
  setStatus('');
  const file = input.files[0];
  selectedFile.hidden = !file;
  button.disabled = true;
  actionHint.textContent = 'Choose a PDF to get started.';
  if (!file) return;
  document.querySelector('#file-name').textContent = file.name;
  document.querySelector('#file-size').textContent = `${formatSize(file.size)} · PDF document`;
  if (!/\.pdf$/i.test(file.name)) {
    setStatus('Please choose a PDF file.', 'error');
  } else if (!file.size) {
    setStatus('This file is empty. Please choose another PDF.', 'error');
  } else if (file.size > 200 * 1024 * 1024) {
    setStatus('PDF must be 200 MiB or smaller.', 'error');
  } else {
    button.disabled = false;
    actionHint.textContent = 'Ready when you are.';
  }
}

input.addEventListener('change', updateFile);
document.querySelector('#remove-file').addEventListener('click', () => {
  input.value = '';
  updateFile();
  input.focus();
});
form.querySelectorAll('input[type="radio"], #landscape').forEach((control) => {
  control.addEventListener('change', () => {
    clearResult();
    setStatus('');
  });
});

['dragenter', 'dragover', 'dragleave', 'drop'].forEach((type) => {
  dropZone.addEventListener(type, (event) => {
    event.preventDefault();
    if (processing) return;
    if (type === 'dragenter') dragDepth += 1;
    if (type === 'dragleave') dragDepth = Math.max(0, dragDepth - 1);
    if (type === 'drop') {
      dragDepth = 0;
      if (event.dataTransfer.files.length !== 1) {
        setStatus('Please drop one PDF at a time.', 'error');
      } else {
        input.files = event.dataTransfer.files;
        updateFile();
      }
    }
    dropZone.classList.toggle('drag-over', type === 'dragover' || dragDepth > 0);
  });
});

function setProcessing(active) {
  processing = active;
  form.classList.toggle('processing', active);
  form.setAttribute('aria-busy', active.toString());
  form.querySelectorAll('input, button').forEach((control) => { control.disabled = active; });
  buttonLabel.textContent = active ? 'Splitting your PDF…' : 'Split my PDF';
  document.querySelector('#button-icon').hidden = active;
  document.querySelector('#spinner').hidden = !active;
  actionHint.textContent = active ? 'Larger files may take a little longer.' : 'Ready when you are.';
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (processing || button.disabled) return;
  const file = input.files[0];
  if (!file) return;
  clearResult();
  const data = new FormData(form);
  data.set('only_landscape', document.querySelector('#landscape').checked.toString());
  setProcessing(true);
  setStatus('Uploading and splitting your PDF. Keep this page open.', 'processing');
  try {
    const response = await fetch('api/split', { method: 'POST', body: data });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(typeof error.detail === 'string' ? error.detail : 'Could not split this PDF. Check the file and try again.');
    }
    const blob = await response.blob();
    downloadUrl = URL.createObjectURL(blob);
    download.href = downloadUrl;
    download.download = `${file.name.replace(/\.pdf$/i, '')}_split.pdf`;
    document.querySelector('#result-summary').textContent = `${response.headers.get('X-Split-Pages')} page(s) split · ${response.headers.get('X-Untouched-Pages')} left unchanged`;
    document.querySelector('#result-size').textContent = `${formatSize(blob.size)} · Ready to download`;
    result.hidden = false;
    download.hidden = false;
    setStatus('Your PDF is ready to download.', 'success');
    download.focus({ preventScroll: true });
    result.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'nearest' });
  } catch (error) {
    setStatus(error.message || 'Upload failed. Please try again.', 'error');
  } finally {
    setProcessing(false);
  }
});

window.addEventListener('pagehide', () => { if (downloadUrl) URL.revokeObjectURL(downloadUrl); });
