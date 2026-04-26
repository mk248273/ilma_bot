const API_URL = window.location.origin;

// Extreme Debugging
window.onerror = function(msg, url, line) {
    alert("Error: " + msg + "\nAt: " + line);
};

document.addEventListener('DOMContentLoaded', () => {
    console.log("Chat JS Loaded. Host:", API_URL);
    
    const sendBtn = document.getElementById('sendBtn');
    const userInput = document.getElementById('userInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const fileInput = document.getElementById('fileInput');

    if (sendBtn) sendBtn.addEventListener('click', sendMessage);
    if (userInput) {
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }
    if (uploadBtn) uploadBtn.addEventListener('click', () => fileInput.click());
    if (fileInput) fileInput.addEventListener('change', handleFileSelect);

    // Initial load
    try {
        loadHistory();
        const userDisplay = document.getElementById('userNameDisplay');
        if (userDisplay) userDisplay.innerText = localStorage.getItem('username') || 'Student';
    } catch(e) { console.error("Init error", e); }
});

function handleFileSelect() {
    const file = document.getElementById('fileInput').files[0];
    const preview = document.getElementById('filePreview');
    if (file && preview) {
        document.getElementById('fileName').innerText = file.name;
        preview.style.display = 'flex';
    }
}

async function sendMessage() {
    try {
        const textInput = document.getElementById('userInput');
        const message = textInput.value.trim();
        const fileInput = document.getElementById('fileInput');
        const file = fileInput ? fileInput.files[0] : null;

        if (!message && !file) return;

        console.log("Attempting to send:", message);

        // UI Updates
        appendMessage('user', message);
        textInput.value = '';
        
        const preview = document.getElementById('filePreview');
        if (preview) preview.style.display = 'none';

        const botMsgDiv = appendMessage('bot', 'AI is thinking...');
        let botText = '';

        const formData = new FormData();
        formData.append('message', message);
        if (file) formData.append('file', file);

        const token = localStorage.getItem('token');
        if (!token) {
            alert("Please login first");
            window.location.href = 'login.html';
            return;
        }

        const response = await fetch(`${API_URL}/chat/send`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });

        if (!response.ok) throw new Error("Server error: " + response.status);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        botMsgDiv.querySelector('.message-content').innerHTML = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.substring(6));
                    botText += data.text;
                    
                    let html = botText;
                    if (window.marked) {
                        html = typeof marked.parse === 'function' ? marked.parse(botText) : marked(botText);
                    }
                    if (window.DOMPurify) html = DOMPurify.sanitize(html);
                    
                    botMsgDiv.querySelector('.message-content').innerHTML = html;
                }
            }
            const container = document.getElementById('messages');
            if (container) container.scrollTop = container.scrollHeight;
        }
    } catch (err) {
        alert("Send Error: " + err.message);
        console.error(err);
    }
}

function appendMessage(role, text) {
    const container = document.getElementById('messages');
    if (!container) {
        console.error("Messages container not found!");
        return;
    }

    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    
    let html = text;
    if (role === 'bot' && text !== 'AI is thinking...') {
       if (window.marked) {
           html = typeof marked.parse === 'function' ? marked.parse(text) : marked(text);
       }
       if (window.DOMPurify) html = DOMPurify.sanitize(html);
    }

    msgDiv.innerHTML = `<div class="message-content">${html}</div>`;
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
    return msgDiv;
}

async function loadHistory() {
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
        const res = await fetch(`${API_URL}/chat/history`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            const history = await res.json();
            const list = document.getElementById('historyList');
            if (list) {
                list.innerHTML = '';
                history.filter(h => h.role === 'user').slice(-5).forEach(m => {
                    const div = document.createElement('div');
                    div.className = 'history-item';
                    div.style = 'padding:8px; font-size:12px; opacity:0.7; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;';
                    div.innerText = m.content;
                    list.appendChild(div);
                });
            }
        }
    } catch(e) {}
}
