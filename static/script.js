document.addEventListener('DOMContentLoaded', () => {
    const dialogueContainer = document.getElementById('dialogue-container');
    const addDialogueBtn = document.getElementById('add-dialogue-btn');
    const generateBtn = document.getElementById('generate-btn');
    const statusArea = document.getElementById('status-area');
    const rowTemplate = document.getElementById('dialogue-row-template');
    const backgroundSelector = document.getElementById('background-selector');

    // --- Background Selection Logic ---
    backgroundSelector.addEventListener('click', (event) => {
        const selectedOption = event.target.closest('.background-option');
        if (!selectedOption) return;

        // Remove 'selected' class from all options
        document.querySelectorAll('.background-option').forEach(opt => opt.classList.remove('selected'));
        
        // Add 'selected' class to the clicked option
        selectedOption.classList.add('selected');
    });

    // --- Dialogue Row Logic ---
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

    // --- Main Generate Logic ---
    generateBtn.addEventListener('click', async () => {
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating...';
        statusArea.innerHTML = '';

        // 1. Gather dialogue data
        const dialogueRows = document.querySelectorAll('.dialogue-row');
        const dialoguePayload = [];
        dialogueRows.forEach(row => {
            const character = row.querySelector('.character-select').value;
            const imagePlacement = row.querySelector('.placement-select').value;
            const text = row.querySelector('.dialogue-input').value;
            if (text.trim() !== '') {
                dialoguePayload.push({ character, text, imagePlacement });
            }
        });

        if (dialoguePayload.length === 0) {
            alert('Please enter at least one line of dialogue.');
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Generate Video';
            return;
        }

        // 2. Gather global options
        const selectedBackground = document.querySelector('.background-option.selected').dataset.video;
        const subtitleStyle = document.getElementById('subtitle-style-select').value;
        const optionsPayload = {
            backgroundVideo: selectedBackground,
            subtitleStyle: subtitleStyle
        };
        
        // 3. Send everything to the backend
        try {
            const response = await fetch('/api/generate-video', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ dialogue: dialoguePayload, options: optionsPayload }),
            });

            if (!response.ok) throw new Error('Failed to queue job.');

            const data = await response.json();
            const jobId = data.job_id;
            statusArea.textContent = `Job queued! Now processing...`;
            
            // 4. Poll for status
            const intervalId = setInterval(async () => {
                const statusResponse = await fetch(`/api/job-status/${jobId}`);
                if (!statusResponse.ok) return;
                
                const statusData = await statusResponse.json();
                statusArea.textContent = `Job Status: ${statusData.status}...`;

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
                    statusArea.textContent = `Job failed. Please check the worker logs on Render.`;
                }
            }, 5000);

        } catch (error) {
            statusArea.textContent = 'An error occurred. Please try again.';
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Generate Video';
        }
    });
});
