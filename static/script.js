document.addEventListener('DOMContentLoaded', () => {
    // ... (All your element getters are the same) ...
    const dialogueContainer = document.getElementById('dialogue-container');
    const addDialogueBtn = document.getElementById('add-dialogue-btn');
    const generateBtn = document.getElementById('generate-btn');
    const statusArea = document.getElementById('status-area');
    const rowTemplate = document.getElementById('dialogue-row-template');

    // ... (The setupSelector and dialogue row logic are unchanged) ...

    generateBtn.addEventListener('click', async () => {
        // ... (The data gathering logic is unchanged) ...
        const dialoguePayload = ...
        const optionsPayload = ...

        // --- Main Generate Logic ---
        try {
            const response = await fetch('/api/generate-video', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ dialogue: dialoguePayload, options: optionsPayload }),
            });

            if (!response.ok) throw new Error('Failed to queue job.');

            const data = await response.json();
            const jobId = data.job_id;
            statusArea.textContent = `Job queued! Polling for status...`; // Initial message
            
            const intervalId = setInterval(async () => {
                const statusResponse = await fetch(`/api/job-status/${jobId}`);
                if (!statusResponse.ok) return;
                
                const statusData = await statusResponse.json();
                
                // NEW: Display the detailed progress message
                statusArea.textContent = `Status: ${statusData.progress}`;

                if (statusData.status === 'finished') {
                    clearInterval(intervalId);
                    generateBtn.disabled = false;
                    generateBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Generate Video';
                    statusArea.innerHTML = `
                        <p>Video is ready!</p>
                        <a href="${statusData.result.video_url}" target="_blank" rel="noopener noreferrer" style="color: var(--primary-color); font-weight: 600;">
                            Click here to Download Your Clip
                        </a>`;
                } else if (statusData.status === 'failed') {
                    clearInterval(intervalId);
                    generateBtn.disabled = false;
                    generateBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Generate Video';
                    statusArea.textContent = `Job failed. Please check the worker logs on Render for details.`;
                }
            }, 3000); // Poll every 3 seconds for faster feedback

        } catch (error) {
            // ... (Error handling is unchanged) ...
        }
    });
});
