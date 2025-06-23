document.addEventListener('DOMContentLoaded', () => {
    const dialogueContainer = document.getElementById('dialogue-container');
    const addDialogueBtn = document.getElementById('add-dialogue-btn');
    const generateBtn = document.getElementById('generate-btn');
    const statusArea = document.getElementById('status-area');
    const rowTemplate = document.getElementById('dialogue-row-template');

    // Function to add a new dialogue row
    const addRow = () => {
        const templateClone = rowTemplate.content.cloneNode(true);
        dialogueContainer.appendChild(templateClone);
    };

    // Add the first two rows automatically on page load
    addRow();
    addRow();

    // Event listener for the "Add Dialogue" button
    addDialogueBtn.addEventListener('click', addRow);

    // Event listener to handle removing rows (using event delegation)
    dialogueContainer.addEventListener('click', (event) => {
        if (event.target.classList.contains('remove-btn')) {
            event.target.closest('.dialogue-row').remove();
        }
    });

    // Event listener for the main "Generate Video" button
    generateBtn.addEventListener('click', async () => {
        generateBtn.disabled = true;
        generateBtn.textContent = 'Gathering Data...';
        statusArea.innerHTML = '';

        // 1. Collect all dialogue data into an array of objects
        const dialogueRows = document.querySelectorAll('.dialogue-row');
        const dialoguePayload = [];
        dialogueRows.forEach(row => {
            const character = row.querySelector('.character-select').value;
            const text = row.querySelector('.dialogue-input').value;
            if (text.trim() !== '') {
                dialoguePayload.push({ character, text });
            }
        });

        if (dialoguePayload.length === 0) {
            alert('Please enter at least one line of dialogue.');
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate Video';
            return;
        }

        generateBtn.textContent = 'Sending to Kitchen...';
        
        // 2. The rest of the process is the same as before
        try {
            const response = await fetch('/api/generate-video', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ dialogue: dialoguePayload }),
            });

            if (!response.ok) throw new Error('Failed to queue job.');

            const data = await response.json();
            const jobId = data.job_id;
            statusArea.textContent = `Job queued! Now processing...`;
            generateBtn.textContent = 'Processing...';
            
            const intervalId = setInterval(async () => {
                const statusResponse = await fetch(`/api/job-status/${jobId}`);
                if (!statusResponse.ok) return;
                
                const statusData = await statusResponse.json();
                statusArea.textContent = `Job Status: ${statusData.status}...`;

                if (statusData.status === 'finished') {
                    clearInterval(intervalId);
                    generateBtn.disabled = false;
                    generateBtn.textContent = 'Generate Video';
                    statusArea.innerHTML = `
                        <p>Video is ready!</p>
                        <a href="${statusData.result.video_url}" target="_blank" rel="noopener noreferrer" download="ai_generated_video.mp4" style="color: #1877f2; text-decoration: none; font-weight: bold;">
                            Click here to Download
                        </a>`;
                } else if (statusData.status === 'failed') {
                    clearInterval(intervalId);
                    generateBtn.disabled = false;
                    generateBtn.textContent = 'Generate Video';
                    statusArea.textContent = `Job failed. Please check the worker logs on Render.`;
                }
            }, 5000);

        } catch (error) {
            statusArea.textContent = 'An error occurred. Please try again.';
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate Video';
        }
    });
});
