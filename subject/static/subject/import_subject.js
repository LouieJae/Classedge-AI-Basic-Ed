  (function () {
    const dropZone = document.getElementById('impDrop');
    const fileInput = document.getElementById('importFile');
    const fileName = document.getElementById('impFileName');
    const fileNameSpan = fileName ? fileName.querySelector('span') : null;
    if (!dropZone || !fileInput) return;

    function setName(name) {
      if (!fileName || !fileNameSpan) return;
      fileNameSpan.textContent = name;
      fileName.classList.toggle('show', !!name);
    }

    fileInput.addEventListener('change', () => {
      const f = fileInput.files && fileInput.files[0];
      setName(f ? f.name : '');
    });
    ['dragenter', 'dragover'].forEach(ev => dropZone.addEventListener(ev, (e) => {
      e.preventDefault(); dropZone.classList.add('dragover');
    }));
    ['dragleave', 'drop'].forEach(ev => dropZone.addEventListener(ev, (e) => {
      e.preventDefault(); dropZone.classList.remove('dragover');
    }));
    dropZone.addEventListener('drop', (e) => {
      const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) {
        const dt = new DataTransfer();
        dt.items.add(f);
        fileInput.files = dt.files;
        setName(f.name);
      }
    });
  })();