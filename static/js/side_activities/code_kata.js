/**
 * code_kata.js — Code kata activity (editor + submit).
 * Plain JS, no modules. All functions are global.
 */

function initCodeKata(container, testCases, onSubmit) {
    var textarea = container.querySelector('.code-kata-editor');
    var submitBtn = container.querySelector('.code-kata-submit');
    var testList = container.querySelector('.code-kata-tests');

    // Render test cases for reference
    if (testList && testCases && testCases.length) {
        testList.innerHTML = '';
        testCases.forEach(function(tc, i) {
            var li = document.createElement('li');
            li.className = 'code-kata-test-case';
            li.textContent = 'Test ' + (i + 1) + ': ' +
                (tc.label || ('Input: ' + JSON.stringify(tc.input) + ' → Expected: ' + JSON.stringify(tc.expected)));
            testList.appendChild(li);
        });
    }

    submitBtn.addEventListener('click', function() {
        var code = textarea.value;
        if (typeof onSubmit === 'function') onSubmit(code);
    });
}
