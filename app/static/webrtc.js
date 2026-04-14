let socket = io.connect("http://localhost:5000");

navigator.mediaDevices.getUserMedia({ audio: true })
  .then(function (stream) {
    let mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm; codecs=opus" });

    mediaRecorder.ondataavailable = function (event) {
      if (event.data.size > 0) {
        event.data.arrayBuffer().then(buffer => {
          socket.emit("audio_data", new Uint8Array(buffer));
        });
      }
    };

    // **Increase recording chunk size to capture better audio**
    mediaRecorder.start(1000); // 1-second intervals

    setInterval(() => {
      mediaRecorder.stop();
      mediaRecorder.start();
    }, 3000); // Restart every 3 seconds to avoid gaps
  })
  .catch(function (err) {
    console.error("Error accessing microphone:", err);
  });

socket.on("audio_event", function (data) {
  console.log("Transcription:", data.transcription);
});
