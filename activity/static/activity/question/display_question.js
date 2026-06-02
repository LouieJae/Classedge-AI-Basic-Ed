      window.MathJax = {
        tex: {
          inlineMath: [['\\(', '\\)'], ['$', '$']],
          displayMath: [['\\[', '\\]'], ['$$', '$$']]
        },
        options: {
          skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
        }
      };
    

      window.MathJax = {
        tex: {
          inlineMath: [['\\(', '\\)'], ['$', '$']],
          displayMath: [['\\[', '\\]'], ['$$', '$$']]
        },
        options: {
          skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
        }
      };
    

      document.addEventListener('DOMContentLoaded', function () {
        if (typeof MathJax !== 'undefined') {
          MathJax.typeset();
        }
      });
    

      function disableRetakeButton(form) {
        const button = form.querySelector('button[type="submit"]');
        button.disabled = true;
        button.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Retaking...`;
        return true;
      }
    