document.addEventListener('DOMContentLoaded', async () => {
    // --- 1. AUTH0 CONFIGURATION ---
    const auth0Config = {
        domain: "dev-23iqnnqsp0tbnxch.us.auth0.com", // Your real Auth0 Domain
        clientId: "99E30sRywMn8h4uFwa5edAbR27F6NGzU", // Your real Auth0 Client ID
        authorizationParams: {
            redirect_uri: window.location.origin
        }
    };

    let auth0 = null;
    try {
        auth0 = await auth0spa.createAuth0Client(auth0Config);
    } catch (e) {
        console.error("Auth0 SDK failed to initialize:", e);
        alert("Authentication service failed to load. Please try again later.");
        return;
    }

    // --- 2. UI ELEMENTS ---
    const loginButton = document.getElementById('btn-login');
    const logoutButton = document.getElementById('btn-logout');
    const editorContainer = document.querySelector('.editor-container');
    const generateBtn = document.getElementById('generate-btn');
    const generateBtnIcon = generateBtn.querySelector('.icon');
    const generateBtnText = generateBtn.querySelector('.text');
    
    // --- 3. EVENT LISTENERS ---
    loginButton.addEventListener('click', () => auth0.loginWithRedirect());
    logoutButton.addEventListener('click', () => auth0.logout({ logoutParams: { returnTo: window.location.origin } }));

    // --- 4. AUTHENTICATION STATE HANDLING ---
    const handleAuthState = async () => {
        const isAuthenticated = await auth0.isAuthenticated();
        if (isAuthenticated) {
            loginButton.style.display = 'none';
            logoutButton.style.display = 'block';
            editorContainer.style.display = 'block';
            const user = await auth0.getUser();
            console.log('Logged in as:', user);
        } else {
            loginButton.style.display = 'block';
            logoutButton.style.display = 'none';
            editorContainer.style.display = 'none';
        }
    };

    // --- 5. PAGE LOAD LOGIC ---
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has("code") && urlParams.has("state")) {
        try {
            await auth0.handleRedirectCallback();
            window.history.replaceState({}, document.title, "/");
        } catch(e) { console.error("Error handling redirect callback:", e); }
    }
    
    await handleAuthState();
    
    // --- 6. The rest of your editor logic ---
    const dialogueContainer = document.getElementById('dialogue-container');
    const addDialogueBtn = document.getElementById('add-dialogue-btn');
    const statusArea = document.getElementById('status-area');
    const rowTemplate = document.getElementById('dialogue-row-template');

    const setupSelector = (selectorId) => {
        const selector = document.getElementById(selectorId);
        selector.addEventListener('click', (event) => {
            const selectedOption = event.target.closest('.option-box');
            if (!selectedOption) return;
            selector.querySelectorAll('.option-box').forEach(opt => opt.classList.remove('selected'));
            selectedOption.classList.add('selected');
        });
    };
    setupSelector('template-selector');
    setupSelector('background-selector');
    setupSelector('subtitle-selector');

    const addRow = () => dialogueContainer.appendChild(rowTemplate.content.cloneNode(true));
    addRow(); addRow();
    addDialogueBtn.addEventListener('click', addRow);
    dialogueContainer.addEventListener('click', (event) => {
        if (event.target.classList.contains('remove-btn')) {
            event.target.closest('.dialogue-row').remove();
        }
    });

    generateBtn.addEventListener('click', async () => {
        if (document.querySelector('#template-selector .option-box.selected').dataset.template !== 'character') {
            alert('This template is coming soon!'); return;
        }

        generateBtn.disabled = true;
        generateBtnIcon.innerHTML = '<i class="fa-solid fa-spinner spinner"></i>';
        generateBtnText.textContent = 'Generating...';
        statusArea.innerHTML = '';

        const dialoguePayload = Array.from(document.querySelectorAll('.dialogue-row')).map(row => ({
            character: row.querySelector('.character-select').value,
            imagePlacement: row.querySelector('.placement-select').value,
            text: row.querySelector('.dialogue-input').value,
        })).filter(line => line.text.trim() !== '');

        if (dialoguePayload.length === 0) {
            alert('Please enter at least one line of dialogue.');
            generateBtn.disabled = false;
            generateBtnIcon.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i>';
            generateBtnText.textContent = 'Generate Video'; return;
        }

        const optionsPayload = {
            template: document.querySelector('#template-selector .option-box.selected').dataset.template,
            backgroundVideo: document.querySelector('#background-selector .option-box.selected').dataset.video,
            subtitleStyle: document.querySelector('#subtitle-selector .option-box.selected').dataset.style
        };
        
        try {
            const response = await fetch('/api/generate-video', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ dialogue: dialoguePayload, options: optionsPayload }),
            });
            if (!response.ok) throw new Error('Failed to queue job.');
            const data = await response.json();
            const jobId = data.job_id;
            statusArea.textContent = `Job queued! Polling for status...`;
            
            const intervalId = setInterval(async () => {
                try {
                    const statusResponse = await fetch(`/api/job-status/${jobId}`);
                    if (!statusResponse.ok) return;
                    const statusData = await statusResponse.json();
                    statusArea.textContent = `Status: ${statusData.progress}`;
                    if (statusData.status === 'finished' || statusData.status === 'failed') {
                        clearInterval(intervalId);
                        generateBtn.disabled = false;
                        generateBtnIcon.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i>';
                        generateBtnText.textContent = 'Generate Video';
                        if (statusData.status === 'finished') {
                            statusArea.innerHTML = `<p>Video is ready!</p><a href="${statusData.result.video_url}" target="_blank" rel="noopener noreferrer" style="color: var(--primary-color); font-weight: 600;">Click here to Download Your Clip</a>`;
                        } else {
                            statusArea.textContent = `Job failed. Please check the worker logs on Render for details.`;
                        }
                    }
                } catch (pollError) { console.error("Polling error:", pollError); }
            }, 3000);
        } catch (error) {
            statusArea.textContent = 'An error occurred. Please try again.';
            generateBtn.disabled = false;
            generateBtnIcon.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i>';
            generateBtnText.textContent = 'Generate Video';
        }
    });
});
