/*static/script.js*/
const toggleButton = document.getElementById('toggleButton');
const warningDiv = document.getElementById('warning');

toggleButton.addEventListener('click', async () => {
    const response = await fetch('/toggle_detection', { method: 'POST' });
    const data = await response.json();
    if (data.status === 'ok') {
        if (toggleButton.textContent === 'Start Detection') {
            toggleButton.textContent = 'Stop Detection';
            checkWarning();
        } else {
            toggleButton.textContent = 'Start Detection';
        }
    }
});

async function checkWarning() {
    const response = await fetch('/get_warning');
    const data = await response.json();
    console.log("Warning Data:", data);
    warningDiv.textContent = data.warning || '';
    if (toggleButton.textContent === 'Stop Detection') {
        setTimeout(checkWarning, 500);
    }
}