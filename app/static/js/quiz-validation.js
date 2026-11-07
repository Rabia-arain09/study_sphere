(function () {
    var form = document.querySelector('form[data-quiz-validation]');
    if (!form) return;

    var errorBox = form.querySelector('[data-quiz-error]');
    var missingList = form.querySelector('[data-quiz-missing-list]');
    var cards = Array.from(form.querySelectorAll('[data-question-card]'));

    function hasAnswer(card) {
        var radioInputs = Array.from(
            card.querySelectorAll('input[type="radio"]')
        );
        if (radioInputs.length) {
            return radioInputs.some(function (input) {
                return input.checked;
            });
        }
        return Array.from(card.querySelectorAll('input, textarea, select'))
            .some(function (field) {
                return field.value.trim().length > 0;
            });
    }

    function clearCardError(card) {
        if (hasAnswer(card)) card.classList.remove('quiz-unanswered');
    }

    cards.forEach(function (card) {
        card.addEventListener('input', function () {
            clearCardError(card);
        });
        card.addEventListener('change', function () {
            clearCardError(card);
        });
    });

    form.addEventListener('submit', function (event) {
        var missing = cards.filter(function (card) {
            return !hasAnswer(card);
        });
        if (!missing.length) {
            errorBox.hidden = true;
            return;
        }

        event.preventDefault();
        cards.forEach(function (card) {
            card.classList.toggle('quiz-unanswered', missing.indexOf(card) !== -1);
        });
        missingList.replaceChildren();
        missing.forEach(function (card) {
            var item = document.createElement('li');
            var link = document.createElement('a');
            link.href = '#' + card.id;
            link.textContent = card.dataset.questionLabel || 'Unanswered question';
            item.appendChild(link);
            missingList.appendChild(item);
        });
        errorBox.hidden = false;
        missing[0].scrollIntoView({behavior: 'smooth', block: 'center'});
        var firstInput = missing[0].querySelector('input, textarea, select');
        if (firstInput) firstInput.focus({preventScroll: true});
    });
})();
