// static/script.js

// This function will run once the main HTML document is fully loaded.
document.addEventListener('DOMContentLoaded', async () => {

    // --- 1. AUTH0 CONFIGURATION ---
    // You must replace these placeholders with the values from your Auth0 Application settings.
    const auth0Config = {
        domain: "dev-23iqnnqsp0tbnxch.us.auth0.com", // <-- REPLACE with your Auth0 Domain
        clientId: "99E30sRywMn8h4uFwa5edAbR27F6NGzU", // <-- REPLACE with your Auth0 Client ID
        authorizationParams: {
            redirect_uri: window.location.origin // The page to return to after login
        }
    };

    let auth0 = null;
    try {
        auth0 = await auth0spa.createAuth0Client(auth0Config);
    } catch (e) {
        console.error("Auth0 SDK failed to initialize:", e);
        return; // Stop if Auth0 fails
    }

    // --- 2. UI ELEMENTS ---
    const loginButton = document.getElementById('btn-login');
    const logoutButton = document.getElementById('btn-logout');
    const editorContainer = document.querySelector('.editor-container'); // The main editor area

    // --- 3. EVENT LISTENERS ---
    loginButton.addEventListener('click', async () => {
        // This redirects the user to the Auth0 Universal Login page.
        // Auth0 will handle showing the Google button.
        await auth0.loginWithRedirect(); 
    });

    logoutButton.addEventListener('click', () => {
        // This logs the user out and returns them to your main page.
        auth0.logout({
            logoutParams: {
                returnTo: window.location.origin
            }
        });
    });

    // --- 4. AUTHENTICATION STATE HANDLING ---
    const handleAuthState = async () => {
        const isAuthenticated = await auth0.isAuthenticated();
        
        if (isAuthenticated) {
            // If the user is logged in:
            loginButton.style.display = 'none';
            logoutButton.style.display = 'block';
            editorContainer.style.display = 'block'; // Show the editor

            // You can get user profile information like this.
            const user = await auth0.getUser();
            console.log('Logged in as:', user);
            
            // This is where you would get the secure token to send to your backend API
            // const accessToken = await auth0.getTokenSilently();
            // Your fetch requests would include this token in the header.

        } else {
            // If the user is NOT logged in:
            loginButton.style.display = 'block';
            logoutButton.style.display = 'none';
            editorContainer.style.display = 'none'; // Hide the editor
        }
    };

    // --- 5. PAGE LOAD LOGIC ---
    // This part handles the redirect back from Auth0 after a successful login.
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has("code") && urlParams.has("state")) {
        try {
            await auth0.handleRedirectCallback();
            // Clean up the URL by removing the code and state parameters
            window.history.replaceState({}, document.title, "/");
        } catch(e) {
            console.error("Error handling redirect callback:", e);
        }
    }
    
    // Finally, check the authentication state and update the UI accordingly.
    await handleAuthState();
    
    // =================================================================================
    // Your existing video generation editor logic goes here.
    // NOTE: It is now wrapped inside the main function, so it only runs
    // after the authentication check is complete.
    // =================================================================================
    
    const dialogueContainer = document.getElementById('dialogue-container');
    const addDialogueBtn = document.getElementById('add-dialogue-btn');
    const generateBtn = document.getElementById('generate-btn');
    const statusArea = document.getElementById('status-area');
    const rowTemplate = document.getElementById('dialogue-row-template');
    const generateBtnIcon = generateBtn.querySelector('.icon');
    const generateBtnText = generateBtn.querySelector('.text');

    const setupSelector = (selectorId) => {
        const selector = document.getElementById(selectorId);
        if (!selector) return;
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

    const addRow = () => {
        const templateClone = rowTemplate.content.cloneNode(true);
        dialogueContainer.appendChild(templateClone);
    };
    addRow();
    addRow();

    addDialogueBtn.addEventListener('click', addRow);
    dialogueContainer.addEventListener('click', (event) => {
        if (event.target.classList.contains('remove-btn')) {
            event.target.closest('.dialogue-row').remove();
        }
    });

    generateBtn.addEventListener('click', async () => {
        const selectedTemplate = document.querySelector('#template-selector .option-box.selected').dataset.template;
        if (selectedTemplate !== 'character') {
            alert('This template is coming soon! Please select "Character Dialogue" to continue.');
            return;
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
            generateBtnText.textContent = 'Generate Video';
            return;
        }

        const optionsPayload = {
            template: selectedTemplate,
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
                } catch (pollError) {
                    console.error("Polling error:", pollError);
                }
            }, 3000);
        } catch (error) {
            statusArea.textContent = 'An error occurred. Please try again.';
            generateBtn.disabled = false;
            generateBtnIcon.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i>';
            generateBtnText.textContent = 'Generate Video';
        }
    });
});
