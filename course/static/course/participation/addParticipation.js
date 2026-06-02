  document.addEventListener('DOMContentLoaded', function () {
    var maxInput = document.getElementById('ma-max-score');
    function clamp() {
      var max = parseFloat(maxInput.value) || 0;
      document.querySelectorAll('.ma-score-input').forEach(function (inp) {
        inp.max = max;
        var v = parseFloat(inp.value);
        if (!isNaN(v) && v > max) inp.value = max;
      });
    }
    maxInput.addEventListener('input', clamp);
    clamp();
  });