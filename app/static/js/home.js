(function () {
    var home = document.querySelector('[data-home-chat]');
    if (!home) return;

    var semesterSelect = home.querySelector('[data-home-semester]');
    var subjectSelect = home.querySelector('[data-home-subject]');
    var topicSelect = home.querySelector('[data-home-topic]');
    var topicLabel = home.querySelector('[data-home-topic-label]');
    var form = home.querySelector('[data-home-chat-form]');
    var questionInput = home.querySelector('[data-home-question]');
    var sendButton = home.querySelector('[data-home-send]');
    var messages = home.querySelector('[data-home-messages]');
    var hint = home.querySelector('[data-home-hint]');
    var status = home.querySelector('[data-home-status]');
    var clearButton = home.querySelector('[data-home-clear]');
    var openNoteLink = home.querySelector('[data-home-open-note]');
    var selectedType = null;
    var selectedId = null;
    var dropdownRequest = 0;
    var historyRequest = 0;

    function setStatus(message, isError) {
        status.textContent = message;
        status.classList.toggle('is-error', Boolean(isError));
    }

    function appendMessage(role, content) {
        var article = document.createElement('article');
        article.className = 'home-chat-message home-chat-' + role;
        var label = document.createElement('span');
        label.className = 'study-chat-role';
        label.textContent = role === 'user' ? 'You' : 'Study assistant';
        var text = document.createElement('p');
        text.textContent = content;
        article.appendChild(label);
        article.appendChild(text);
        messages.appendChild(article);
        messages.scrollTop = messages.scrollHeight;
    }

    function requestJson(url, options) {
        return fetch(url, options || {}).then(function (response) {
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

    function fillSelect(select, placeholder, items) {
        select.replaceChildren();
        var emptyOption = document.createElement('option');
        emptyOption.value = '';
        emptyOption.textContent = placeholder;
        select.appendChild(emptyOption);
        items.forEach(function (item) {
            var option = document.createElement('option');
            option.value = String(item.id);
            option.textContent = item.name || item.title;
            select.appendChild(option);
        });
    }

    function resetConversation() {
        historyRequest += 1;
        selectedType = null;
        selectedId = null;
        messages.replaceChildren();
        hint.hidden = false;
        clearButton.hidden = true;
        openNoteLink.hidden = true;
        openNoteLink.removeAttribute('href');
        setStatus('', false);
    }

    function loadHistory() {
        var requestId = ++historyRequest;
        var parameter = selectedType === 'topic' ? 'topic_id' : 'upload_id';
        var url = home.dataset.chatHistoryUrl + '?' + parameter + '=' +
            encodeURIComponent(selectedId);
        setStatus('Loading saved chat...', false);
        return requestJson(url).then(function (data) {
            if (requestId !== historyRequest) return;
            messages.replaceChildren();
            data.messages.forEach(function (message) {
                appendMessage(message.role, message.content);
            });
            hint.hidden = true;
            setStatus('', false);
        }).catch(function (error) {
            if (requestId === historyRequest) setStatus(error.message, true);
        });
    }

    function chooseContext(type, id, url) {
        selectedType = type;
        selectedId = id;
        messages.replaceChildren();
        hint.hidden = true;
        clearButton.hidden = false;
        openNoteLink.href = url;
        openNoteLink.hidden = false;
        loadHistory();
    }

    function loadCourses() {
        var requestId = ++dropdownRequest;
        subjectSelect.disabled = true;
        topicSelect.disabled = true;
        fillSelect(subjectSelect, 'Choose a subject', []);
        var uploadsOption = document.createElement('option');
        uploadsOption.value = '__uploads__';
        uploadsOption.textContent = 'My uploaded material';
        subjectSelect.appendChild(uploadsOption);
        fillSelect(topicSelect, 'Choose a topic', []);
        topicLabel.textContent = 'Topic';
        resetConversation();

        requestJson('/home/courses?semester=' + encodeURIComponent(semesterSelect.value))
            .then(function (data) {
                if (requestId !== dropdownRequest) return;
                data.courses.forEach(function (course) {
                    var option = document.createElement('option');
                    option.value = String(course.id);
                    option.textContent = course.code + ' - ' + course.name;
                    subjectSelect.insertBefore(option, uploadsOption);
                });
                subjectSelect.disabled = false;
            })
            .catch(function (error) {
                if (requestId === dropdownRequest) setStatus(error.message, true);
            });
    }

    function loadTopics(courseId) {
        var requestId = ++dropdownRequest;
        topicLabel.textContent = 'Topic';
        topicSelect.disabled = true;
        fillSelect(topicSelect, 'Choose a topic', []);
        resetConversation();
        requestJson('/home/topics?course_id=' + encodeURIComponent(courseId))
            .then(function (data) {
                if (requestId !== dropdownRequest) return;
                fillSelect(topicSelect, 'Choose a topic', data.topics);
                topicSelect.disabled = false;
            })
            .catch(function (error) {
                if (requestId === dropdownRequest) setStatus(error.message, true);
            });
    }

    function loadUploads() {
        var requestId = ++dropdownRequest;
        topicLabel.textContent = 'Uploaded material';
        topicSelect.disabled = true;
        fillSelect(topicSelect, 'Choose your material', []);
        resetConversation();
        requestJson('/home/uploads')
            .then(function (data) {
                if (requestId !== dropdownRequest) return;
                fillSelect(topicSelect, 'Choose your material', data.uploads);
                topicSelect.disabled = false;
            })
            .catch(function (error) {
                if (requestId === dropdownRequest) setStatus(error.message, true);
            });
    }

    semesterSelect.addEventListener('change', loadCourses);
    subjectSelect.addEventListener('change', function () {
        if (subjectSelect.value === '__uploads__') {
            loadUploads();
        } else if (subjectSelect.value) {
            loadTopics(subjectSelect.value);
        } else {
            dropdownRequest += 1;
            topicSelect.disabled = true;
            fillSelect(topicSelect, 'Choose a topic', []);
            resetConversation();
        }
    });

    topicSelect.addEventListener('change', function () {
        if (!topicSelect.value) {
            resetConversation();
            return;
        }
        var isUpload = subjectSelect.value === '__uploads__';
        var id = topicSelect.value;
        chooseContext(
            isUpload ? 'upload' : 'topic',
            id,
            isUpload ? '/upload/' + id : '/topics/' + id
        );
    });

    form.addEventListener('submit', function (event) {
        event.preventDefault();
        var question = questionInput.value.trim();
        if (!selectedType || !selectedId) {
            hint.hidden = false;
            setStatus('Choose a topic or uploaded material first.', true);
            return;
        }
        if (!question) {
            setStatus('Please enter a question.', true);
            return;
        }
        if (question.length > 500) {
            setStatus('Questions must be 500 characters or fewer.', true);
            return;
        }
        if (sendButton.disabled) return;

        var submittedType = selectedType;
        var submittedId = selectedId;
        var endpoint = submittedType === 'topic' ? '/chat/topic/' : '/chat/upload/';
        sendButton.disabled = true;
        setStatus('Thinking...', false);
        requestJson(endpoint + encodeURIComponent(submittedId), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': home.dataset.csrfToken
            },
            body: JSON.stringify({ question: question })
        }).then(function (data) {
            if (selectedType !== submittedType || selectedId !== submittedId) return;
            historyRequest += 1;
            appendMessage('user', question);
            appendMessage('assistant', data.answer);
            questionInput.value = '';
            setStatus('', false);
        }).catch(function (error) {
            if (selectedType === submittedType && selectedId === submittedId) {
                setStatus(error.message, true);
            }
        }).finally(function () {
            sendButton.disabled = false;
            questionInput.focus();
        });
    });

    clearButton.addEventListener('click', function () {
        if (!selectedType || !selectedId) return;
        var clearedType = selectedType;
        var clearedId = selectedId;
        var endpoint = clearedType === 'topic' ? '/chat/topic/' : '/chat/upload/';
        historyRequest += 1;
        clearButton.disabled = true;
        setStatus('', false);
        requestJson(endpoint + encodeURIComponent(clearedId) + '/clear', {
            method: 'POST',
            headers: { 'X-CSRFToken': home.dataset.csrfToken }
        }).then(function () {
            if (selectedType !== clearedType || selectedId !== clearedId) return;
            messages.replaceChildren();
            setStatus('Chat cleared.', false);
        }).catch(function (error) {
            if (selectedType === clearedType && selectedId === clearedId) {
                setStatus(error.message, true);
            }
        }).finally(function () {
            clearButton.disabled = false;
        });
    });

    loadCourses();
})();
