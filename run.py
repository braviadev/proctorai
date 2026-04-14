import eventlet
# We add os=False so eventlet doesn't break Windows file reading/writing
eventlet.monkey_patch(os=False)

import os
# This tells the newest TensorFlow to use the Keras 2 compatibility bridge for DeepFace
os.environ["TF_USE_LEGACY_KERAS"] = "1"

from app import create_app, socketio

# Create the application instance
app = create_app()

if __name__ == '__main__':
    # Run the app using SocketIO
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False)