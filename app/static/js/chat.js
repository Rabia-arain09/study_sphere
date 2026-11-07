(function () {
    var widget = document.querySelector('[data-study-chat]');
    if (!widget) return;

    var form = widget.querySelector('[data-chat-form]');
    var textarea = form.querySelector('textarea');
    var sendButton = widget.querySelector('[data-chat-send]');
    var clearButton = widget.querySelector('[data-chat-clear]');
    var messages = widget.querySelector('[data-chat-messages]');
    var status = widget.querySelector('[data-chat-status]');

    function scrollToLatest() {
        messages.scrollTop = messages.scrollHeight;
    }

    function setStatus(message, isError) {
        status.textContent = message;
        status.classList.toggle('is-error', Boolean(isError));
    }

    function addMessage(role, text) {
        var article = document.createElement('article');
        article.className = 'study-chat-message study-chat-' + role;

        var label = document.createElement('span');
        label.className = 'study-chat-role';
        label.textContent = role === 'user' ? 'You' : 'Study assistant';

        var content = document.createElement('p');
        content.textContent = text;
        article.appendChild(label);
        article.appendChild(content);

        var emptyState = messages.querySelector('[data-chat-empty]');
        if (emptyState) emptyState.remove();
        messages.appendChild(article);
        scrollToLatest();
        return article;
    }

    function requestJson(url, payload) {
        return fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': widget.dataset.csrfToken
            },
            body: JSON.stringify(payload || {})
        }).then(function (response) {
            return response.json().catch(function () {
                return {};
            }).then(function (data) {
                if (!response.ok) {
                    throw new Error(data.error || 'The request could not be completed.');
                }
                return data;
            });
        });
    }

    form.addEventListener('submit', function (event) {
        event.preventDefault();
        var question = textarea.value.trim();
        if (!question) {
            setStatus('Please enter a question.', true);
            return;
        }
        if (question.length > 500) {
            setStatus('Questions must be 500 characters or fewer.', true);
            return;
        }

        sendButton.disabled = true;
        clearButton.disabled = true;
        setStatus('Thinking...', false);
        var pendingQuestion = addMessage('user', question);

        requestJson(widget.dataset.sendUrl, { question: question })
            .then(function (data) {
                addMessage('assistant', data.answer);
                textarea.value = '';
                setStatus('', false);
            })
            .catch(function (error) {
                pendingQuestion.remove();
                setStatus(error.message, true);
                scrollToLatest();
            })
            .finally(function () {
                sendButton.disabled = false;
                clearButton.disabled = false;
                textarea.focus();
            });
    });

    clearButton.addEventListener('click', function () {
        sendButton.disabled = true;
        clearButton.disabled = true;
        setStatus('', false);

        requestJson(widget.dataset.clearUrl)
            .then(function () {
                messages.replaceChildren();
                var emptyState = document.createElement('p');
                emptyState.className = 'study-chat-empty';
                emptyState.dataset.chatEmpty = '';
                emptyState.textContent = 'Ask a question about this note or material.';
                messages.appendChild(emptyState);
                setStatus('Chat cleared.', false);
                scrollToLatest();
            })
            .catch(function (error) {
                setStatus(error.message, true);
            })
            .finally(function () {
                sendButton.disabled = false;
                clearButton.disabled = false;
            });
    });

    scrollToLatest();
})();
