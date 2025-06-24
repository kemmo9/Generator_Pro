document.addEventListener('DOMContentLoaded', () => {
    const dialogueContainer = document.getElementById('dialogue-container');
    const addDialogueBtn = document.getElementById('add-dialogue-btn');
    const generateBtn = document.getElementById('generate-btn');
    const statusArea = document.getElementById('status-area');
    const rowTemplate = document.getElementById('dialogue-row-template');
    const subtitleStyleSelect = document.getElementById('subtitle-style');

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
        generateBtn.disabled = true;
        generateBtn.textContent = 'Gathering Data...';
        statusArea.innerHTML = '';

        // Collect dialogue data INCLUDING individual image placement
        const dialogueRows = document.querySelectorAll('.dialogue-row');
        const dialoguePayload = [];
        dialogueRows.forEach(row => {
            const character = row.querySelector('.character-select').value;
            const imagePlacement = row.querySelector('.image-placement-select').value;
            const text = row.querySelector('.dialogue-input').value;
            if (text.trim() !== '') {
                dialoguePayload.push({ character, text, imagePlacement });
            }
        });

        if (dialoguePayload.length === 0) {
            alert('Please enter at least one line of dialogue.');
            generateBtn.disabled = false;
            generateBtn.textContent = '✨ Generate Your Viral Video ✨';
            return;
        }

        // Collect global options
        const optionsPayload = {
            subtitleStyle: subtitleStyleSelect.value
        };

        // Create the final payload to send to the backend
        const finalPayload = {
            dialogue: dialoguePayload,
            options: optionsPayload
        };

        generateBtn.textContent = 'Sending to Kitchen...';
        
        try {
            const response = await fetch('/api/generate-video', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(finalPayload),
            });

            if (!response.ok) throw new Error('Failed to queue job.');

            const data = await response.json();
            const jobId = data.job_id;
            statusArea.textContent = `Job queued! Now processing...`;
            generateBtn.textContent = 'Processing...';
            
            // Polling logic remains the same and is robust
            const intervalId = setInterval(async () => {
                const statusResponse = await fetch(`/api/job-status/${jobId}`);
                if (!statusResponse.ok) return;
                
                const statusData = await statusResponse.json();
                statusArea.textContent = `Job Status: ${statusData.status}...`;

                if (statusData.status === 'finished') {
                    clearInterval(intervalId);
                    generateBtn.disabled = false;
                    generateBtn.textContent = '✨ Generate Your Viral Video ✨';
                    statusArea.innerHTML = `
                        <p style="font-size: 1.2rem;">Video is ready!</p>
                        <a href="${statusData.result.video_url}" target="_blank" rel="noopener noreferrer" download="made_with_makeaclip.mp4" 
                           style="display: inline-block; padding: 10px 20px; background-color: var(--button-secondary); color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">
                            ⬇️ Download Video
                        </a>`;
                } else if (statusData.status === 'failed') {
                    clearInterval(intervalId);
                    generateBtn.disabled = false;
                    generateBtn.textContent = '✨ Generate Your Viral Video ✨';
                    statusArea.textContent = `Job failed. The AI might be tired. Please check the logs or try again.`;
                }
            }, 5000);

        } catch (error) {
            statusArea.textContent = 'An error occurred. Please try again.';
            generateBtn.disabled = false;
            generateBtn.textContent = '✨ Generate Your Viral Video ✨';
        }
    });
});
