# background_activities_detection_model
# audio_processing/audio_processing.py
import sounddevice as sd
import numpy as np

def capture_audio(duration=1, sample_rate=44100):
    """Captures audio from the microphone."""
    try:
        audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
        sd.wait()
        print("Audio captured.")
        return audio_data.flatten()
    except Exception as e:
        print(f"Error capturing audio: {e}")
        return None

def detect_voice_activity(audio_data, threshold=0.01):
    """Detects voice activity based on signal energy."""
    if audio_data is None:
        return False  # Return False if no audio data
    energy = np.mean(np.abs(audio_data))
    print(f"Energy: {energy}")
    return energy > threshold

def detect_silence(audio_data, threshold=0.001):
    """Detects silence based on signal energy."""
    if audio_data is None:
        return True #return true if no audio data
    energy = np.mean(np.abs(audio_data))
    print(f"Energy: {energy}")
    return energy < threshold