document.addEventListener("DOMContentLoaded", () => {
    const API_URL = "http://127.0.0.1:8000";
    let currentPdfUrl = null;

    // --- DOM Elements ---
    const chatBox = document.getElementById('chat-box');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const fileInput = document.getElementById('file-upload');
    
    // PDF & UI Elements
    const pdfFrame = document.getElementById('pdf-frame');
    const sidebar = document.querySelector('aside');
    const menuBtn = document.querySelector('.mobile-menu-btn');
    const pdfSection = document.querySelector('.pdf-section');
    const backBtn = document.getElementById('back-btn'); // Mobile Back Button

    // --- 1. THE CLICK FIX (Event Delegation) ---
    chatBox.addEventListener('click', (e) => {
        // Check if the clicked item is a citation span
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

        // 1. Create a FRESH iframe element ("Nuclear Option")
        // This forces the browser to treat this as a brand new page load
        const newFrame = document.createElement('iframe');
        newFrame.id = 'pdf-frame';
        newFrame.src = `${currentPdfUrl}#page=${pageNum}`;
        newFrame.style.display = "block"; 

        // 2. Swap the old frame with the new one
        if (oldFrame) {
            if (pdfSection.contains(oldFrame)) {
                pdfSection.replaceChild(newFrame, oldFrame);
            } else {
                pdfSection.appendChild(newFrame);
            }
        } else {
            pdfSection.appendChild(newFrame);
        }

        // 3. Mobile Support: Show the PDF Section
        if (window.innerWidth < 768) {
            if (pdfSection) {
                pdfSection.classList.add('active'); // CSS makes it visible
                // No need to scrollIntoView because absolute positioning covers the screen
            }
        }
    }

    // --- 2. Mobile Logic (Menu & Back Button) ---
    if (menuBtn) {
        menuBtn.addEventListener('click', () => {
            sidebar.classList.toggle('active');
        });
    }

    // "Back to Chat" Button Logic
    if (backBtn) {
        backBtn.addEventListener('click', () => {
            // Hide the PDF section to reveal the chat
            if (pdfSection) {
                pdfSection.classList.remove('active');
            }
        });
    }

    // --- 3. File Upload Logic ---
    if (fileInput) {
        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            // Simple Status Update
            const statusArea = document.querySelector('.status-box');
            statusArea.innerHTML = `<div style="color: yellow;">⏳ Uploading ${file.name}...</div>`;

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

                    // SAVE THE URL LOCALLY
                    currentPdfUrl = URL.createObjectURL(file);
                    
                    // Show PDF Frame (Default View)
                    const pdfFrame = document.getElementById('pdf-frame');
                    if (pdfFrame) {
                        pdfFrame.src = currentPdfUrl;
                        document.querySelector('.pdf-placeholder').style.display = 'none';
                        pdfFrame.style.display = 'block';
                    }

                    // Mobile: Close sidebar automatically
                    if (window.innerWidth < 768) sidebar.classList.remove('active');

                    appendMessage(`I have read <strong>${data.filename}</strong>. Ask me anything!`, 'bot');

                } else {
                    statusArea.innerHTML = `<div style="color: red;">❌ Upload Failed</div>`;
                }
            } catch (err) {
                console.error(err);
                statusArea.innerHTML = `<div style="color: red;">❌ Error connecting to server</div>`;
            }
        });
    }

    // --- 4. Chat Logic ---
    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        userInput.value = '';
        appendMessage(text, 'user');

        // Create Bot Message Bubble
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
            
            // Clear "Thinking..."
            content.innerHTML = "";
            let fullText = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                fullText += chunk;
                
                // Stream text
                content.innerHTML = fullText.replace(/\n/g, "<br>");
                chatBox.scrollTop = chatBox.scrollHeight;
            }

            // --- Apply Links (Runs once at the end) ---
            formatCitations(content);

        } catch (err) {
            content.innerHTML = "⚠️ Error: Could not reach the brain.";
        }
    }

    // --- 5. Helper Functions ---
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
        // THE FIX:
        // 1. "Pages?" with a question mark means the 's' is optional.
        // 2. We added the 'i' flag at the end to make it Case-Insensitive (Page vs page).
        const regex = /\[Pages?\s+([\d,\s]+)\]/gi;
        
        element.innerHTML = element.innerHTML.replace(regex, (match, group) => {
            // 'group' captures just the numbers, e.g., "1, 7"
            
            // 1. Split by comma to handle multiple numbers
            const pageNumbers = group.split(',');

            // 2. Create a link for EACH number
            const links = pageNumbers.map(num => {
                const n = num.trim();
                // Check if n is actually a number (prevents empty links)
                if (n) {
                    return `<span class="citation" data-page="${n}" title="Jump to Page ${n}" style="color: #3b82f6; cursor: pointer; text-decoration: underline; font-weight: bold;">${n}</span>`;
                }
                return n;
            });

            // 3. Reconstruct the string. We keep the original "Page" or "Pages" prefix if we want, 
            // or we can just standardize it to "Page". Let's standardize it:
            return `[Page ${links.join(', ')}]`;
        });
    }

    // Event Listeners
    if (sendBtn) sendBtn.addEventListener('click', sendMessage);
    if (userInput) userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
});