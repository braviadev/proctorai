// proctoring_system/static/script.js
const socket = io();

socket.on('connect', () => {
    console.log('Socket connected!');
});

socket.on('disconnect', (reason) => {
    console.log('Socket disconnected! Reason:', reason);
});

document.getElementById('start').addEventListener('click', () => {
    socket.emit('start_detection');
    document.getElementById('result').textContent = 'Detecting...';
});

socket.on('detection_result', (data) => {
    document.getElementById('result').textContent = `RMS: ${data.rms}, Noise Detected: ${data.noise_detected}`;

    if(data.noise_detected){
        alert("This enviroment is not permissive for writing examinations");
    } else {
        alert("Environment is quiet and serene");
    }
});

socket.on('detection_error', (data) => {
    document.getElementById('result').textContent = `Error: ${data.error}`;
});