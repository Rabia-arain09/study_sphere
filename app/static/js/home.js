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
    var conversationList = home.querySelector('[data-home-conversations]');
    var conversationEmpty = home.querySelector('[data-home-conversations-empty]');
    var conversationSearch = home.querySelector('[data-home-chat-search]');
    var newChatButton = home.querySelector('[data-home-new-chat]');
    var sidebar = home.querySelector('#home-chat-sidebar');
    var sidebarCollapseButton = home.querySelector('[data-home-sidebar-collapse]');
    var sidebarToggle = home.querySelector('[data-home-sidebar-toggle]');
    var sidebarBackdrop = home.querySelector('[data-home-sidebar-backdrop]');
    var greeting = home.querySelector('[data-home-greeting]');
    var greetingText = home.querySelector('[data-home-greeting-text]');
    var mainContent = home.querySelector('.home-main-content');
    var sidebarMedia = window.matchMedia('(max-width: 900px)');
    var sidebarCollapsed = document.documentElement.getAttribute(
        'data-home-sidebar-collapsed'
    ) === 'true';
    var selectedType = null;
    var selectedId = null;
    var dropdownRequest = 0;
    var historyRequest = 0;
    var conversationRequest = 0;

    function updateGreeting() {
        var hour = new Date().getHours();
        var greetingForTime = hour < 12
            ? 'Good morning'
            : hour <= 17 ? 'Good afternoon' : 'Good evening';
        greetingText.textContent = greetingForTime + ', ' +
            greeting.dataset.firstName;
    }

    function updateSidebarCollapseState(persist) {
        document.documentElement.setAttribute(
            'data-home-sidebar-collapsed',
            String(sidebarCollapsed)
        );
        if (persist) {
            try {
                localStorage.setItem(
                    'studysphere.sidebarCollapsed',
                    String(sidebarCollapsed)
                );
            } catch (error) {
                setStatus('Could not save the sidebar preference.', true);
            }
        }

        if (!sidebarMedia.matches) {
            var expanded = !sidebarCollapsed;
            sidebarCollapseButton.setAttribute(
                'aria-expanded',
                String(expanded)
            );
            var desktopLabel = sidebarCollapsed
                ? 'Expand chat history sidebar'
                : 'Collapse chat history sidebar';
            sidebarCollapseButton.setAttribute('aria-label', desktopLabel);
            sidebarCollapseButton.title = desktopLabel;
        }
    }

    function updateSidebarAccessibility() {
        var closedOnMobile = sidebarMedia.matches &&
            !home.classList.contains('sidebar-open');
        if (sidebarMedia.matches) {
            var drawerOpen = home.classList.contains('sidebar-open');
            var mobileLabel = drawerOpen
                ? 'Close chat history sidebar'
                : 'Open chat history sidebar';
            sidebarCollapseButton.setAttribute(
                'aria-expanded',
                String(drawerOpen)
            );
            sidebarCollapseButton.setAttribute('aria-label', mobileLabel);
            sidebarCollapseButton.title = mobileLabel;
            sidebarToggle.setAttribute('aria-expanded', String(drawerOpen));
        }
        sidebar.inert = closedOnMobile;
        sidebar.setAttribute('aria-hidden', String(closedOnMobile));
        mainContent.inert = sidebarMedia.matches &&
            home.classList.contains('sidebar-open');
    }

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

    function renderConversations(conversations) {
        conversationList.replaceChildren();
        conversationEmpty.hidden = conversations.length > 0;
        if (!conversations.length) {
            conversationEmpty.textContent = conversationSearch.value.trim()
                ? 'No matching chats.'
                : 'No chats yet. Pick a topic and ask a question.';
            return;
        }

        conversations.forEach(function (conversation) {
            var item = document.createElement('div');
            item.className = 'home-conversation-item';
            item.setAttribute('role', 'listitem');
            var isActive = selectedType === conversation.type &&
                String(selectedId) === String(conversation.id);
            if (isActive) item.classList.add('is-active');

            var selectButton = document.createElement('button');
            selectButton.type = 'button';
            selectButton.className = 'home-conversation-select';
            selectButton.dataset.conversationType = conversation.type;
            selectButton.dataset.conversationId = String(conversation.id);
            if (isActive) selectButton.setAttribute('aria-current', 'page');

            var title = document.createElement('span');
            title.className = 'home-conversation-title';
            title.textContent = conversation.title;
            selectButton.appendChild(title);

            if (conversation.subject) {
                var subject = document.createElement('span');
                subject.className = 'home-conversation-subject';
                subject.textContent = conversation.subject;
                selectButton.appendChild(subject);
            }

            var preview = document.createElement('span');
            preview.className = 'home-conversation-preview';
            preview.textContent = conversation.preview;
            selectButton.appendChild(preview);

            var time = document.createElement('time');
            time.className = 'home-conversation-time';
            time.dateTime = conversation.last_activity;
            var activityDate = new Date(conversation.last_activity);
            time.textContent = Number.isNaN(activityDate.getTime())
                ? conversation.last_activity
                : activityDate.toLocaleString();
            selectButton.appendChild(time);
            selectButton.addEventListener('click', function () {
                selectConversation(conversation);
            });

            var deleteButton = document.createElement('button');
            deleteButton.type = 'button';
            deleteButton.className = 'home-conversation-delete';
            deleteButton.textContent = 'Delete';
            deleteButton.setAttribute(
                'aria-label',
                'Delete chat: ' + conversation.title
            );
            deleteButton.addEventListener('click', function () {
                deleteConversation(conversation);
            });

            item.appendChild(selectButton);
            item.appendChild(deleteButton);
            conversationList.appendChild(item);
        });
    }

    function refreshConversations() {
        var requestId = ++conversationRequest;
        var url = home.dataset.conversationsUrl;
        var search = conversationSearch.value.trim();
        if (search) url += '?q=' + encodeURIComponent(search);
        return requestJson(url).then(function (data) {
            if (requestId === conversationRequest) {
                renderConversations(data.conversations);
            }
        }).catch(function (error) {
            if (requestId === conversationRequest) setStatus(error.message, true);
        });
    }

    function closeSidebar() {
        home.classList.remove('sidebar-open');
        sidebarToggle.setAttribute('aria-expanded', 'false');
        sidebarCollapseButton.setAttribute('aria-expanded', 'false');
        sidebarCollapseButton.setAttribute(
            'aria-label',
            'Close chat history sidebar'
        );
        sidebarCollapseButton.title = 'Close chat history sidebar';
        updateSidebarAccessibility();
        sidebarToggle.focus();
    }

    function resetConversation() {
        historyRequest += 1;
        selectedType = null;
        selectedId = null;
        questionInput.value = '';
        messages.replaceChildren();
        hint.hidden = false;
        clearButton.hidden = true;
        openNoteLink.hidden = true;
        openNoteLink.removeAttribute('href');
        setStatus('', false);
        renderConversationsFromCurrentState();
    }

    function renderConversationsFromCurrentState() {
        var items = Array.from(conversationList.children);
        items.forEach(function (item) {
            var button = item.querySelector('.home-conversation-select');
            var active = button &&
                ((selectedType === 'topic' || selectedType === 'upload') &&
                    button.dataset.conversationType === selectedType &&
                    button.dataset.conversationId === String(selectedId));
            item.classList.toggle('is-active', Boolean(active));
            if (active) {
                button.setAttribute('aria-current', 'page');
            } else {
                button.removeAttribute('aria-current');
            }
        });
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
        renderConversationsFromCurrentState();
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

        return requestJson('/home/courses?semester=' + encodeURIComponent(semesterSelect.value))
            .then(function (data) {
                if (requestId !== dropdownRequest) return false;
                data.courses.forEach(function (course) {
                    var option = document.createElement('option');
                    option.value = String(course.id);
                    option.textContent = course.code + ' - ' + course.name;
                    subjectSelect.insertBefore(option, uploadsOption);
                });
                subjectSelect.disabled = false;
                return true;
            })
            .catch(function (error) {
                if (requestId === dropdownRequest) setStatus(error.message, true);
                return false;
            });
    }

    function loadTopics(courseId) {
        var requestId = ++dropdownRequest;
        topicLabel.textContent = 'Topic';
        topicSelect.disabled = true;
        fillSelect(topicSelect, 'Choose a topic', []);
        resetConversation();
        return requestJson('/home/topics?course_id=' + encodeURIComponent(courseId))
            .then(function (data) {
                if (requestId !== dropdownRequest) return false;
                fillSelect(topicSelect, 'Choose a topic', data.topics);
                topicSelect.disabled = false;
                return true;
            })
            .catch(function (error) {
                if (requestId === dropdownRequest) setStatus(error.message, true);
                return false;
            });
    }

    function loadUploads() {
        var requestId = ++dropdownRequest;
        topicLabel.textContent = 'Uploaded material';
        topicSelect.disabled = true;
        fillSelect(topicSelect, 'Choose your material', []);
        resetConversation();
        return requestJson('/home/uploads')
            .then(function (data) {
                if (requestId !== dropdownRequest) return false;
                fillSelect(topicSelect, 'Choose your material', data.uploads);
                topicSelect.disabled = false;
                return true;
            })
            .catch(function (error) {
                if (requestId === dropdownRequest) setStatus(error.message, true);
                return false;
            });
    }

    function selectConversation(conversation) {
        closeSidebar();
        semesterSelect.value = String(
            conversation.semester || home.dataset.defaultSemester
        );
        loadCourses().then(function (coursesLoaded) {
            if (!coursesLoaded) return false;
            if (conversation.type === 'upload') {
                subjectSelect.value = '__uploads__';
                return loadUploads();
            }
            subjectSelect.value = String(conversation.course_id);
            return loadTopics(conversation.course_id);
        }).then(function (contextLoaded) {
            if (!contextLoaded) return;
            topicSelect.value = String(conversation.id);
            if (!topicSelect.value) {
                setStatus('This chat is no longer available.', true);
                return;
            }
            chooseContext(
                conversation.type,
                conversation.id,
                conversation.type === 'upload'
                    ? '/upload/' + conversation.id
                    : '/topics/' + conversation.id
            );
        }).catch(function (error) {
            setStatus(error.message, true);
        });
    }

    function startNewChat() {
        semesterSelect.value = home.dataset.defaultSemester;
        resetConversation();
        subjectSelect.disabled = true;
        topicSelect.disabled = true;
        topicLabel.textContent = 'Topic';
        loadCourses();
    }

    function deleteConversation(conversation) {
        if (!window.confirm('Delete this saved chat and all its messages?')) return;
        var url = home.dataset.conversationsUrl + '/' +
            encodeURIComponent(conversation.type) + '/' +
            encodeURIComponent(conversation.id);
        requestJson(url, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': home.dataset.csrfToken }
        }).then(function () {
            if (selectedType === conversation.type &&
                String(selectedId) === String(conversation.id)) {
                startNewChat();
            }
            return refreshConversations();
        }).catch(function (error) {
            setStatus(error.message, true);
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
            refreshConversations();
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
            refreshConversations();
        }).catch(function (error) {
            if (selectedType === clearedType && selectedId === clearedId) {
                setStatus(error.message, true);
            }
        }).finally(function () {
            clearButton.disabled = false;
        });
    });

    newChatButton.addEventListener('click', startNewChat);
    conversationSearch.addEventListener('input', refreshConversations);
    sidebarToggle.addEventListener('click', function () {
        var isOpen = home.classList.toggle('sidebar-open');
        sidebarToggle.setAttribute('aria-expanded', String(isOpen));
        sidebarCollapseButton.setAttribute('aria-expanded', String(isOpen));
        sidebarCollapseButton.setAttribute(
            'aria-label',
            isOpen ? 'Close chat history sidebar' : 'Open chat history sidebar'
        );
        sidebarCollapseButton.title = isOpen
            ? 'Close chat history sidebar'
            : 'Open chat history sidebar';
        updateSidebarAccessibility();
        if (isOpen) newChatButton.focus();
    });
    sidebarCollapseButton.addEventListener('click', function () {
        if (sidebarMedia.matches) {
            closeSidebar();
            return;
        }
        sidebarCollapsed = !sidebarCollapsed;
        updateSidebarCollapseState(true);
        updateSidebarAccessibility();
    });
    sidebarBackdrop.addEventListener('click', closeSidebar);
    sidebarMedia.addEventListener('change', function () {
        if (!sidebarMedia.matches) {
            home.classList.remove('sidebar-open');
            sidebarToggle.setAttribute('aria-expanded', 'false');
            updateSidebarCollapseState(false);
        } else {
            sidebarCollapseButton.setAttribute('aria-expanded', 'false');
            sidebarCollapseButton.setAttribute(
                'aria-label',
                'Open chat history sidebar'
            );
            sidebarCollapseButton.title = 'Open chat history sidebar';
        }
        updateSidebarAccessibility();
    });
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && home.classList.contains('sidebar-open')) {
            closeSidebar();
            return;
        }
        if (event.key === 'Tab' && sidebarMedia.matches &&
            home.classList.contains('sidebar-open')) {
            var focusable = sidebar.querySelectorAll(
                'button:not([disabled]), input:not([disabled])'
            );
            var first = focusable[0];
            var last = focusable[focusable.length - 1];
            if (!sidebar.contains(document.activeElement)) {
                event.preventDefault();
                (event.shiftKey ? last : first).focus();
            } else if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }
    });

    updateGreeting();
    updateSidebarCollapseState(false);
    updateSidebarAccessibility();
    refreshConversations();
    loadCourses();
})();
