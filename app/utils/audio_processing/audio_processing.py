# audio_utils/audio_processing.py
import sounddevice as sd
import numpy as np

def capture_audio(duration=1, sample_rate=44100):
    """Captures audio from the microphone."""
    audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
    sd.wait()
    print("Audio captured.")
    return audio_data.flatten()

def detect_voice_activity(audio_data, threshold=0.0003):
    """Detects voice activity based on signal energy."""
    energy = np.mean(np.abs(audio_data))
    print(f"Voice Activity Energy: {energy}")
    print(f"Min Energy: {np.min(np.abs(audio_data))}, Max Energy: {np.max(np.abs(audio_data))}")
    return energy > threshold

def detect_silence(audio_data, threshold=0.0001):
    """Detects silence based on signal energy."""
    energy = np.mean(np.abs(audio_data))
    print(f"Silence Energy: {energy}")
    print(f"Min Energy: {np.min(np.abs(audio_data))}, Max Energy: {np.max(np.abs(audio_data))}")
    return energy < threshold