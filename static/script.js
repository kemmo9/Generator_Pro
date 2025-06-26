document.addEventListener('DOMContentLoaded', () => {
    // Get all interactive elements
    const dialogueContainer = document.getElementById('dialogue-container');
    const addDialogueBtn = document.getElementById('add-dialogue-btn');
    const generateBtn = document.getElementById('generate-btn');
    const statusArea = document.getElementById('status-area');
    const rowTemplate = document.getElementById('dialogue-row-template');
    
    // --- Universal Selector Logic ---
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
        // 1. Gather all selections
        const selectedTemplate = document.querySelector('#template-selector .option-box.selected').dataset.template;
        const selectedBackground = document.querySelector('#background-selector .option-box.selected').dataset.video;
        const selectedSubtitle = document.querySelector('#subtitle-selector .option-box.selected').dataset.style;
        
        // --- TEMPLATE CHECK ---
        // For now, only the 'character' template is implemented.
        if (selectedTemplate !== 'character') {
            alert('This template is coming soon! Please select "Character Dialogue" to continue.');
            return;
        }

        generateBtn.disabled = true;
        generateBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating...';
        statusArea.innerHTML = '';

        // 2. Gather dialogue data
        const dialoguePayload = Array.from(document.querySelectorAll('.dialogue-row')).map(row => ({
            character: row.querySelector('.character-select').value,
            imagePlacement: row.querySelector('.placement-select').value,
            text: row.querySelector('.dialogue-input').value,
        })).filter(line => line.text.trim() !== '');

        if (dialoguePayload.length === 0) {
            alert('Please enter at least one line of dialogue.');
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Generate Video';
            return;
        }

        // 3. Create options payload
        const optionsPayload = {
            template: selectedTemplate,
            backgroundVideo: selectedBackground,
            subtitleStyle: selectedSubtitle
        };
        
        // 4. Send to backend and poll for status (same as before)
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
            
            const intervalId = setInterval(async () => {
                const statusResponse = await fetch(`/api/job-status/${jobId}`);
                if (!statusResponse.ok) return;
                const statusData = await statusResponse.json();
                statusArea.textContent = `Job Status: ${statusData.status}...`;

                if (statusData.status === 'finished') {
                    clearInterval(intervalId);
                    generateBtn.disabled = false;
                    generateBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Generate Video';
                    statusArea.innerHTML = `<p>Video is ready!</p><a href="${statusData.result.video_url}" target="_blank" rel="noopener noreferrer" style="color: var(--primary-color); font-weight: 600;">Click here to Download Your Clip</a>`;
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
