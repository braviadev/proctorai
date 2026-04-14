# proctoring_system/audio_processing/audio_utils.py
import sounddevice as sd
import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft
import time

def capture_audio(duration=15, samplerate=44100):
    """Captures audio from the microphone."""
    print("Recording...")
    time.sleep(0.5)
    audio_data = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1)
    sd.wait()
    print("Recording finished.")
    audio = audio_data.flatten()
    print(f"Captured audio data: {audio}")

    plt.plot(audio)
    plt.show()

    return audio

def calculate_rms(audio_data):
    """Calculates the RMS of the audio data."""
    rms = np.sqrt(np.mean(audio_data**2))
    return rms

def is_noise_detected(rms, threshold=0.00005):
    """Checks if the RMS exceeds a threshold."""
    print(f"RMS: {rms}, Threshold: {threshold}")
    return rms > threshold

def calculate_baseline_rms(duration=3, samplerate=44100):
    """Calculates the baseline RMS in a quiet environment."""
    audio = capture_audio(duration, samplerate)
    return calculate_rms(audio)

def is_noise_detected_dynamic(audio_data, baseline_rms, threshold_factor=1.0):
    """Checks if noise is detected using a dynamic threshold."""
    rms = calculate_rms(audio_data)
    threshold = baseline_rms * threshold_factor
    return rms > threshold

def analyze_frequencies(audio_data, samplerate=44100):
    """Analyzes frequencies in the audio data."""
    frequencies = fft(audio_data)
    return frequencies

def calculate_rms_sliding_window(audio_data, window_size=1000, spike_threshold=0.00005):
    """Calculates RMS using a sliding window with spike handling."""
    rms_values = []
    for i in range(0, len(audio_data) - window_size, window_size):
        window = audio_data[i:i + window_size]
        if np.max(np.abs(window)) > spike_threshold:
            pass
        else:
            rms = calculate_rms(window)
            rms_values.append(rms)
    print(f"Sliding window RMS list: {rms_values}")
    return rms_values

def is_noise_detected_sliding_window(rms_values, threshold=0.00005):
    """Checks if noise is detected using sliding window RMS."""
    print(f"RMS Values: {rms_values}, Threshold: {threshold}")
    for rms in rms_values:
        if rms > threshold:
            return True
    return False