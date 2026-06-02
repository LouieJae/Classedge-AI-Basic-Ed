  // Bootstrap 5 form validation - Enhanced for score field
  (function () {
    'use strict'
    
    // Fetch all the forms we want to apply custom Bootstrap validation styles to
    var forms = document.querySelectorAll('.needs-validation')
    
    // Loop over them and prevent submission
    Array.prototype.slice.call(forms).forEach(function (form) {
      form.addEventListener('submit', function (event) {
        // Get the score input
        var scoreInput = document.getElementById('validationCustomScore');
        var maxScore = parseFloat(scoreInput.max);
        var scoreValue = parseFloat(scoreInput.value);
        
        // Custom validation for score
        if (isNaN(scoreValue) || scoreValue < 0 || scoreValue > maxScore) {
          scoreInput.setCustomValidity('Please enter a valid score between 0 and ' + maxScore);
        } else {
          scoreInput.setCustomValidity('');
        }            
        
        // Check form validity
        if (!form.checkValidity()) {
          event.preventDefault()
          event.stopPropagation()
        }
        
        form.classList.add('was-validated')
      }, false)
      
      // Add real-time validation for score input
      var scoreInput = document.getElementById('validationCustomScore');
      if (scoreInput) {
        scoreInput.addEventListener('input', function() {
          var maxScore = parseFloat(this.max);
          var scoreValue = parseFloat(this.value);
          
          if (isNaN(scoreValue) || scoreValue < 0 || scoreValue > maxScore) {
            this.classList.add('is-invalid');
            this.classList.remove('is-valid');
          } else {
            this.classList.remove('is-invalid');
            this.classList.add('is-valid');
          }
        });
      }
    })
  })()