    function addChoice() {
      const choiceContainer = document.createElement('div');
      choiceContainer.classList.add('input-group', 'mb-3', 'choice-container', 'd-flex', 'align-items-center');

      const radioInput = document.createElement('input');
      radioInput.type = 'radio';
      radioInput.name = 'correct_answer';
      radioInput.classList.add('me-2');
      radioInput.required = true;

      const textInput = document.createElement('input');
      textInput.type = 'text';
      textInput.name = 'choices';
      textInput.classList.add('form-control', 'ml-2');
      textInput.required = true;

      const deleteButton = document.createElement('button');
      deleteButton.type = 'button';
      deleteButton.classList.add('btn', 'btn-danger', 'btn-sm', 'ml-2', 'remove-choice');
      deleteButton.textContent = 'Remove';
      deleteButton.onclick = function () {
        if (document.querySelectorAll('.choice-container').length > 2) {
          choiceContainer.remove();
        }
      };

      choiceContainer.appendChild(radioInput);
      choiceContainer.appendChild(textInput);
      choiceContainer.appendChild(deleteButton);

      document.getElementById('choices').appendChild(choiceContainer);
    }
  

    window.MathJax = {
      tex: {
        inlineMath: [['$', '$'], ['\\(', '\\)']],
        displayMath: [['$$', '$$'], ['\\[', '\\]']]
      },
      options: {
        skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
      }
    };
  

    document.addEventListener("DOMContentLoaded", function () {
      var questionInput = document.getElementById("question_text");
      var answerInput = document.getElementById("correct_answer");
      var questionPreview = document.getElementById("mathjax-preview-question");
      var answerPreview = document.getElementById("mathjax-preview-answer");

      function updateMathJaxPreview(inputElement, previewElement) {
        if (inputElement && previewElement) {
          var input = inputElement.value.trim();
          previewElement.innerHTML = `\\(${input}\\)`;
          MathJax.typesetPromise([previewElement]).catch(function (err) {
          });
        }
      }

    // Run preview on input events
      if (questionInput) {
        questionInput.addEventListener("input", function () {
          updateMathJaxPreview(questionInput, questionPreview);
        });

      // Trigger update on page load
        updateMathJaxPreview(questionInput, questionPreview);
      }

      if (answerInput) {
        answerInput.addEventListener("input", function () {
          updateMathJaxPreview(answerInput, answerPreview);
        });

      // Trigger update on page load
        updateMathJaxPreview(answerInput, answerPreview);
      }
      
      // Initialize total percentage calculation
      if (document.getElementById('total_percentage')) {
        updateTotalPercentage();
      }
      
      // Add event listeners for rubric item removal
      document.querySelectorAll('.remove-rubric').forEach(button => {
        button.addEventListener('click', function () {
          this.parentElement.remove();
          updateTotalPercentage();
        });
      });
    });
  

    function addRightOption() {
      const additionalRightOptions = document.getElementById("additional_right_options");

      const rightOptionContainer = document.createElement("div");
      rightOptionContainer.classList.add("input-group", "mb-3");

      const textInput = document.createElement("input");
      textInput.type = "text";
      textInput.name = "extra_right";  // 
      textInput.classList.add("form-control");
      textInput.required = true;

      const deleteButton = document.createElement("button");
      deleteButton.type = "button";
      deleteButton.classList.add("btn", "btn-danger", "btn-sm", "ml-2", "remove-right");
      deleteButton.textContent = "Remove";
      deleteButton.onclick = function () {
        rightOptionContainer.remove();
      };

      rightOptionContainer.appendChild(textInput);
      rightOptionContainer.appendChild(deleteButton);

      additionalRightOptions.appendChild(rightOptionContainer);
    }

  // 
    document.querySelectorAll(".remove-right").forEach((button) => {
      button.addEventListener("click", function () {
        this.parentElement.remove();
      });
    });
  