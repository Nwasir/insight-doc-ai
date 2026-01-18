document.addEventListener("DOMContentLoaded", () => {
    const API_URL = "http://127.0.0.1:8000";
    let currentPdfUrl = null;

    // --- DOM Elements ---
    const chatBox = document.getElementById('chat-box');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const fileInput = document.getElementById('file-upload');
    const uploadZone = document.querySelector('.upload-zone'); // <--- NEW
    
    // PDF & UI Elements
    const pdfFrame = document.getElementById('pdf-frame');
    const sidebar = document.querySelector('aside');
    const menuBtn = document.querySelector('.mobile-menu-btn');
    const pdfSection = document.querySelector('.pdf-section');
    const backBtn = document.getElementById('back-btn');

    // --- 1. DRAG & DROP LOGIC (NEW) ---
    
    // Prevent default browser behavior for all drag events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Add visual highlight when dragging over
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadZone.addEventListener(eventName, () => {
            uploadZone.classList.add('dragging');
        }, false);
    });

    // Remove highlight when dragging leaves or drops
    ['dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, () => {
            uploadZone.classList.remove('dragging');
        }, false);
    });

    // Handle the actual file drop
    uploadZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleUpload(files[0]);
        }
    });

    // Handle the standard click upload
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) handleUpload(file);
        });
    }

    // --- 2. UNIFIED UPLOAD FUNCTION ---
    async function handleUpload(file) {
        // Simple Status Update
        const statusArea = document.querySelector('.status-box');
        statusArea.innerHTML = `<div style="color: yellow;">⏳ Uploading & Converting...</div>`;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`${API_URL}/upload`, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                
                statusArea.innerHTML = `<div style="color: #4ade80;">✅ Ready: ${data.filename}</div>`;

                // --- THE FIX ---
                // OLD: currentPdfUrl = URL.createObjectURL(file); 
                // NEW: Use the file served by the backend
                currentPdfUrl = `${API_URL}/files/${data.filename}`;
                
                // Show PDF Frame
                const pdfFrame = document.getElementById('pdf-frame');
                if (pdfFrame) {
                    pdfFrame.src = currentPdfUrl;
                    document.querySelector('.pdf-placeholder').style.display = 'none';
                    pdfFrame.style.display = 'block';
                }

                if (window.innerWidth < 768) sidebar.classList.remove('active');

                appendMessage(`I have read <strong>${data.original_name}</strong>. Ask me anything!`, 'bot');

            } else {
                statusArea.innerHTML = `<div style="color: red;">❌ Upload Failed</div>`;
            }
        } catch (err) {
            console.error(err);
            statusArea.innerHTML = `<div style="color: red;">❌ Error connecting to server</div>`;
        }
    }


    // --- 3. THE CLICK FIX (Event Delegation) ---
    chatBox.addEventListener('click', (e) => {
        if (e.target.classList.contains('citation')) {
            const pageNum = e.target.getAttribute('data-page');
            console.log(`🖱️ Click detected on Page ${pageNum}`);
            jumpToPage(pageNum);
        }
    });

    function jumpToPage(pageNum) {
        if (!currentPdfUrl) {
            alert("⚠️ No PDF loaded yet. Please upload a file.");
            return;
        }

        console.log(`🚀 Forcing Jump to Page ${pageNum}`);

        const pdfSection = document.querySelector('.pdf-section');
        const oldFrame = document.getElementById('pdf-frame');

        const newFrame = document.createElement('iframe');
        newFrame.id = 'pdf-frame';
        newFrame.src = `${currentPdfUrl}#page=${pageNum}`;
        newFrame.style.display = "block"; 

        if (oldFrame) {
            if (pdfSection.contains(oldFrame)) {
                pdfSection.replaceChild(newFrame, oldFrame);
            } else {
                pdfSection.appendChild(newFrame);
            }
        } else {
            pdfSection.appendChild(newFrame);
        }

        if (window.innerWidth < 768) {
            if (pdfSection) {
                pdfSection.classList.add('active'); 
            }
        }
    }

    // --- 4. Mobile Logic ---
    if (menuBtn) {
        menuBtn.addEventListener('click', () => {
            sidebar.classList.toggle('active');
        });
    }

    if (backBtn) {
        backBtn.addEventListener('click', () => {
            if (pdfSection) {
                pdfSection.classList.remove('active');
            }
        });
    }

    // --- 5. Chat Logic ---
    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        userInput.value = '';
        appendMessage(text, 'user');

        const botMsgDiv = document.createElement('div');
        botMsgDiv.className = 'message bot';
        
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.innerHTML = '🤖';
        
        const content = document.createElement('div');
        content.className = 'content';
        content.innerHTML = "Thinking..."; 
        
        botMsgDiv.appendChild(avatar);
        botMsgDiv.appendChild(content);
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
            
            content.innerHTML = "";
            let fullText = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                fullText += chunk;
                
                content.innerHTML = fullText.replace(/\n/g, "<br>");
                chatBox.scrollTop = chatBox.scrollHeight;
            }

            formatCitations(content);

        } catch (err) {
            content.innerHTML = "⚠️ Error: Could not reach the brain.";
        }
    }

    function appendMessage(text, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}`;

        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.innerHTML = sender === 'user' ? '👤' : '🤖';

        const content = document.createElement('div');
        content.className = 'content';
        content.innerHTML = text;

        msgDiv.appendChild(avatar);
        msgDiv.appendChild(content);
        chatBox.appendChild(msgDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function formatCitations(element) {
        const regex = /\[Pages?\s+([\d,\s]+)\]/gi;
        
        element.innerHTML = element.innerHTML.replace(regex, (match, group) => {
            const pageNumbers = group.split(',');
            const links = pageNumbers.map(num => {
                const n = num.trim();
                if (n) {
                    return `<span class="citation" data-page="${n}" title="Jump to Page ${n}" style="color: #3b82f6; cursor: pointer; text-decoration: underline; font-weight: bold;">${n}</span>`;
                }
                return n;
            });
            return `[Page ${links.join(', ')}]`;
        });
    }

    if (sendBtn) sendBtn.addEventListener('click', sendMessage);
    if (userInput) userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
});