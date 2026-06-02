    (function () {
      const dz = document.getElementById('dropzone');
      const input = document.getElementById('csv_file');
      const chip = document.getElementById('fileChip');
      const fileName = document.getElementById('fileName');

      function setFile(name) {
        if (name) {
          fileName.textContent = name;
          chip.classList.add('show');
        } else {
          chip.classList.remove('show');
        }
      }
      input.addEventListener('change', () => setFile(input.files && input.files[0] ? input.files[0].name : ''));
      ['dragenter', 'dragover'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add('dragover'); }));
      ['dragleave', 'drop'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove('dragover'); }));
      dz.addEventListener('drop', e => {
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
          input.files = e.dataTransfer.files;
          setFile(e.dataTransfer.files[0].name);
        }
      });
    })();
  