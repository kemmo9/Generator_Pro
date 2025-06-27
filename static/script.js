document.addEventListener('DOMContentLoaded', () => {
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
