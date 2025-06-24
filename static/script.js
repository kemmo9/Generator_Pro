document.addEventListener('DOMContentLoaded', () => {
    const dialogueContainer = document.getElementById('dialogue-container');
    const addDialogueBtn = document.getElementById('add-dialogue-btn');
    const generateBtn = document.getElementById('generate-btn');
    const statusArea = document.getElementById('status-area');
    const rowTemplate = document.getElementById('dialogue-row-template');
    
    // Get the new option elements
    const imagePlacementSelect = document.getElementById('image-placement');
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

        // 1. Collect dialogue data
        const dialogueRows = document.querySelectorAll('.dialogue-row');
        const dialoguePayload = [];
        dialogueRows.forEach(row => {
            const character = row.querySelector('.character-select').value;
            // Get value from textarea now
            const text = row.querySelector('.dialogue-input').value;
            if (text.trim() !== '') {
                dialoguePayload.push({ character, text });
            }
        });

        if (dialoguePayload.length === 0) {
            alert('Please enter at least one line of dialogue.');
            generateBtn.disabled = false;
            generateBtn.textContent = '✨ Generate Your Viral Video ✨';
            return;
        }

        // 2. Collect options data
        const optionsPayload = {
            imagePlacement: imagePlacementSelect.value,
            subtitleStyle: subtitleStyleSelect.value
        };

        // 3. Combine payloads and send to backend
        const fullPayload = {
            dialogue: dialoguePayload,
            options: optionsPayload
        };

        generateBtn.textContent = 'Sending to Kitchen...';
        
        try {
            const response = await fetch('/api/generate-video', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(fullPayload),
            });

            if (!response.ok) throw new Error('Failed to queue job.');

            const data = await response.json();
            const jobId = data.job_id;
            statusArea.textContent = `Job queued! Your masterpiece is being rendered...`;
            generateBtn.textContent = 'Processing...';
            
            // Polling logic remains the same
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
                        <p>Video is ready! Go viral!</p>
                        <a href="${statusData.result.video_url}" target="_blank" rel="noopener noreferrer" style="color: #1877f2; text-decoration: none; font-weight: bold;">
                            Click to Download Your Clip
                        </a>`;
                } else if (statusData.status === 'failed') {
                    clearInterval(intervalId);
                    generateBtn.disabled = false;
                    generateBtn.textContent = '✨ Generate Your Viral Video ✨';
                    statusArea.textContent = `Job failed. Please check worker logs.`;
                }
            }, 5000);

        } catch (error) {
            statusArea.textContent = 'An error occurred. Please try again.';
            generateBtn.disabled = false;
            generateBtn.textContent = '✨ Generate Your Viral Video ✨';
        }
    });
});
