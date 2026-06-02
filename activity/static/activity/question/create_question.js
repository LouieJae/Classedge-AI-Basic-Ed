    function addChoice() {
        const choiceCount = document.querySelectorAll('input[name="choices"]').length;
        const choiceIndex = choiceCount;
        const choiceContainer = document.createElement('div');
        choiceContainer.classList.add('input-group', 'mb-3');

        const radioInput = document.createElement('input');
        radioInput.type = 'radio';
        radioInput.name = 'correct_answer';
        radioInput.value = choiceIndex;
        radioInput.required = true;

        const textInput = document.createElement('input');
        textInput.type = 'text';
        textInput.name = 'choices';
        textInput.classList.add('form-control');
        textInput.placeholder = `Choice ${choiceIndex + 1}`;

        const imgInput = document.createElement('input');
        imgInput.type = 'file';
        imgInput.name = `choice_image_${choiceIndex}`;
        imgInput.accept = 'image/*';
        imgInput.classList.add('form-control');
        imgInput.style.maxWidth = '220px';
        imgInput.title = 'Choice image (optional)';

        choiceContainer.appendChild(radioInput);
        choiceContainer.appendChild(textInput);
        choiceContainer.appendChild(imgInput);

        document.getElementById('choices').appendChild(choiceContainer);
    }

    function addMatchingPair() {
        const pairContainer = document.createElement('div');
        pairContainer.classList.add('input-group', 'mb-3');

        const leftInput = document.createElement('input');
        leftInput.type = 'text';
        leftInput.name = 'matching_left';
        leftInput.classList.add('form-control');
        leftInput.placeholder = 'Left side';
        leftInput.required = true;

        const rightInput = document.createElement('input');
        rightInput.type = 'text';
        rightInput.name = 'matching_right';
        rightInput.classList.add('form-control');
        rightInput.placeholder = 'Right side';
        rightInput.required = true;

        pairContainer.appendChild(leftInput);
        pairContainer.appendChild(rightInput);

        document.getElementById('matching_pairs').appendChild(pairContainer);
    }