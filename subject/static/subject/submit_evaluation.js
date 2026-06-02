    document.addEventListener('DOMContentLoaded', function () {
      document.querySelectorAll('.star-rating').forEach(function (starRatingContainer) {
        const fieldName = starRatingContainer.getAttribute('data-field-name')
        const hiddenInput = document.getElementsByName(fieldName)[0]
    
        starRatingContainer.querySelectorAll('.star').forEach(function (star) {
          star.addEventListener('click', function () {
            const ratingValue = star.getAttribute('data-value')
            hiddenInput.value = ratingValue
    
            // Highlight selected stars
            starRatingContainer.querySelectorAll('.star').forEach(function (s) {
              s.classList.toggle('selected', s.getAttribute('data-value') <= ratingValue)
            })
          })
    
          // Hover effect to preview rating
          star.addEventListener('mouseover', function () {
            const ratingValue = star.getAttribute('data-value')
            starRatingContainer.querySelectorAll('.star').forEach(function (s) {
              s.classList.toggle('hovered', s.getAttribute('data-value') <= ratingValue)
            })
          })
    
          star.addEventListener('mouseout', function () {
            starRatingContainer.querySelectorAll('.star').forEach(function (s) {
              s.classList.remove('hovered')
            })
          })
        })
    
        // Clear rating button functionality
        starRatingContainer.querySelector('.clear-rating').addEventListener('click', function () {
          hiddenInput.value = ''
          starRatingContainer.querySelectorAll('.star').forEach(function (s) {
            s.classList.remove('selected')
          })
        })
      })
    })
  