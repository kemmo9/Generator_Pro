let auth0 = null;

const auth0Config = {
    domain: "dev-23iqnnqsp0tbnxch.us.auth0.com", // Your CORRECTED domain
    clientId: "99E30sRywMn8h4uFwa5edAbR27F6NGzU", // Your CORRECTED Client ID
    authorizationParams: {
        redirect_uri: window.location.origin
    }
};

/**
 * This is the main application function. It will only be called
 * after the Auth0 client has been confirmed to exist.
 */
const runApp = async () => {
    // --- AUTHENTICATION LOGIC ---
    const loginButton = document.getElementById('btn-login');
    const logoutButton = document.getElementById('btn-logout');

    loginButton.addEventListener('click', () => auth0.loginWithRedirect());
    logoutButton.addEventListener('click', () => auth0.logout({ logoutParams: { returnTo: window.location.origin } }));

    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has("code") && urlParams.has("state")) {
        await auth0.handleRedirectCallback();
        window.history.replaceState({}, document.title, "/");
    }

    const isAuthenticated = await auth0.isAuthenticated();
    if (isAuthenticated) {
        loginButton.style.display = 'none';
        logoutButton.style.display = 'block';
    } else {
        loginButton.style.display = 'block';
        logoutButton.style.display = 'none';
    }

    // --- EDITOR LOGIC ---
    const generateBtn = document.getElementById('generate-btn');
    generateBtn.addEventListener('click', async () => {
        const isAuth = await auth0.isAuthenticated();
        if (!isAuth) {
            alert("Please log in to generate a video.");
            return auth0.loginWithRedirect();
        }
        
        const generateBtnIcon = generateBtn.querySelector('.icon');
        const generateBtnText = generateBtn.querySelector('.text');
        
        generateBtn.disabled = true;
        generateBtnIcon.innerHTML = '<i class="fa-solid fa-spinner spinner"></i>';
        generateBtnText.textContent = 'Generating...';
        const statusArea = document.getElementById('status-area');
        statusArea.innerHTML = 'Starting...';

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
            const accessToken = await auth0.getTokenSilently();
            const response = await fetch('/api/generate-video', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${accessToken}`},
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
                            statusArea.textContent = `Job failed: ${statusData.progress}`;
                        }
                    }
                } catch (pollError) { console.error("Polling error:", pollError); }
            }, 3000);
        } catch (error) {
            console.error("Generate error:", error);
            statusArea.textContent = 'An error occurred. Please try again.';
            generateBtn.disabled = false;
            generateBtnIcon.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i>';
            generateBtnText.textContent = 'Generate Video';
        }
    });

    const dialogueContainer = document.getElementById('dialogue-container');
    const addDialogueBtn = document.getElementById('add-dialogue-btn');
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
        if (event.target.classList.contains('remove-btn')) event.target.closest('.dialogue-row').remove();
    });
};

/**
 * This is the entry point. It waits for the Auth0 SDK to be ready.
 */
window.addEventListener('load', async () => {
    try {
        // Attempt to create the Auth0 client. This will fail until the SDK is loaded.
        auth0 = await createAuth0Client(auth0Config);
        // If it succeeds, run the main app logic.
        runApp();
    } catch (e) {
        // If it fails, it's likely because the SDK isn't ready. We will wait and retry.
        console.log("Auth0 SDK not ready yet, will retry...");
        const startupInterval = setInterval(async () => {
            try {
                auth0 = await createAuth0Client(auth0Config);
                clearInterval(startupInterval); // Stop polling
                runApp(); // Run the app
            } catch (err) {
                // Still not ready, do nothing and wait for the next interval.
            }
        }, 500); // Check every 500ms
    }
});
