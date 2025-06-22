document.getElementById('video-form').addEventListener('submit', async function(event) {
    event.preventDefault();

    const script = document.getElementById('script').value;
    const generateBtn = document.getElementById('generate-btn');
    const statusArea = document.getElementById('status-area');
    let jobId = null;

    if (!script) {
        alert('Please enter a script.');
        return;
    }

    generateBtn.disabled = true;
    generateBtn.textContent = 'Sending to Kitchen...';
    statusArea.innerHTML = '';

    try {
        // Step 1: Send the script to the backend to queue the job
        const response = await fetch('/api/generate-video', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ script: script }),
        });

        if (!response.ok) {
            throw new Error('Failed to queue job.');
        }

        const data = await response.json();
        jobId = data.job_id;
        statusArea.textContent = `Job queued! ID: ${jobId}. Now processing...`;
        generateBtn.textContent = 'Processing...';
        
        // Step 2: Poll for the job status every 5 seconds
        const intervalId = setInterval(async () => {
            const statusResponse = await fetch(`/api/job-status/${jobId}`);
            if (!statusResponse.ok) {
                return;
            }
            
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
                statusArea.textContent = 'Job failed. Please check the script and try again.';
            }

        }, 5000); // Poll every 5 seconds

    } catch (error) {
        statusArea.textContent = 'An error occurred. Please try again.';
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Video';
    }
});