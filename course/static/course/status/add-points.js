  document.addEventListener('DOMContentLoaded', function () {
    if (window.$ && $.fn.selectpicker) { $('.selectpicker').selectpicker(); }
    const pointsInput = document.querySelector("input[name='points']");
    if (pointsInput) {
      pointsInput.addEventListener('input', function () {
        if (parseFloat(this.value) > 10) {
          this.value = 10;
          if (window.Swal) Swal.fire({ icon: 'warning', title: 'Limit Exceeded', text: 'Points cannot exceed 10.', confirmButtonColor: '#1b4332' });
        }
      });
    }
  });