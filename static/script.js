const API_URL = "http://127.0.0.1:8000";
let currentPdfFile = null;
let uploadController = null; // Used to stop the upload

// DOM Elements
const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const fileInput = document.getElementById('file-input');
const statusList = document.getElementById('status-list');
const pdfFrame = document.getElementById('pdf-frame');
const menuBtn = document.getElementById('menu-btn');
const sidebar = document.getElementById('sidebar');

// --- 1. Mobile Menu Logic ---
menuBtn.addEventListener('click', () => {
    sidebar.classList.toggle('active');
});

// Close sidebar when clicking outside (optional, for better UX)
document.addEventListener('click', (e) => {
    if (window.innerWidth < 768) {
        if (!sidebar.contains(e.target) && !menuBtn.contains(e.target) && sidebar.classList.contains('active')) {
            sidebar.classList.remove('active');
        }
    }
});

// --- 2. File Upload Logic (With Stop Button) ---
fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Create a controller to allow cancelling
    uploadController = new AbortController();
    const signal = uploadController.signal;

    // Create Status Item with a Stop Button
    const statusItem = document.createElement('div');
    statusItem.className = "status-item processing";
    statusItem.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
            <span><i class="fas fa-spinner fa-spin"></i> Processing ${file.name}...</span>
            <button class="btn-stop" id="stop-btn-${file.name}"><i class="fas fa-times"></i></button>
        </div>
    `;
    statusList.prepend(statusItem);

    // Attach Click Event to the new Stop Button
    const stopBtn = document.getElementById(`stop-btn-${file.name}`);
    stopBtn.addEventListener('click', () => {
        if (uploadController) {
            uploadController.abort(); // KILL THE REQUEST
            uploadController = null;
            statusItem.className = "status-item error";
            statusItem.innerHTML = `<i class="fas fa-ban" style="color: #f87171"></i> Cancelled by user.`;
        }
    });

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_URL}/upload`, {
            method: 'POST',
            body: formData,
            signal: signal // Connect the controller
        });
        
        const data = await response.json();
        
        if (response.ok) {
            statusItem.className = "status-item success";
            statusItem.innerHTML = `<i class="fas fa-check-circle" style="color: #4ade80"></i> ${file.name}`;
            
            // Load PDF Locally
            currentPdfFile = URL.createObjectURL(file);
            pdfFrame.src = currentPdfFile;
            pdfFrame.style.display = "block";
            document.querySelector('.pdf-placeholder').style.display = "none";
            
            // Auto-close sidebar on mobile after success
            if (window.innerWidth < 768) sidebar.classList.remove('active');
        } else {
            throw new Error(data.detail);
        }
    } catch (err) {
        if (err.name === 'AbortError') {
            console.log('Upload cancelled');
        } else {
            statusItem.className = "status-item error";
            statusItem.innerHTML = `<i class="fas fa-exclamation-triangle" style="color: #f87171"></i> Error: ${err.message}`;
        }
    } finally {
        uploadController = null; // Reset controller
    }
});

// --- 3. Chat Logic ---
async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    // Add User Message
    appendMessage(text, 'user');
    userInput.value = '';

    // Create Bot Message Container
    const botMsgDiv = document.createElement('div');
    botMsgDiv.className = 'message bot';
    botMsgDiv.innerText = "...";
    chatBox.appendChild(botMsgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        botMsgDiv.innerText = ""; 

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value);
            botMsgDiv.innerHTML += chunk;
            formatCitations(botMsgDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

    } catch (err) {
        botMsgDiv.innerText = "Error: Could not reach the brain.";
    }
}

function appendMessage(text, sender) {
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    div.innerText = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// --- 4. Smart Scrolling Logic ---
function formatCitations(element) {
    const regex = /\[Page (\d+)\]/g;
    element.innerHTML = element.innerHTML.replace(regex, (match, pageNum) => {
        return `<span class="citation" onclick="jumpToPage(${pageNum})">${match}</span>`;
    });
}

function jumpToPage(pageNum) {
    if (currentPdfFile) {
        pdfFrame.src = `${currentPdfFile}#page=${pageNum}`;
        if (window.innerWidth < 768) {
            // Check if we need to show the PDF section
            const pdfSection = document.getElementById('pdf-viewer');
             // On mobile, you might want to toggle visibility or scroll to it
             pdfSection.scrollIntoView({ behavior: 'smooth' });
        }
    } else {
        alert("No PDF loaded yet!");
    }
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});