import torch
import numpy as np
from df.model import init_model  # Correct import

class DeepFilterNetWrapper:
    def __init__(self):
        """
        Initialize the DeepFilterNet model.
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = init_model().to(self.device)  # Use init_model() instead of DeepFilterNet2
        self.model.eval()

    def enhance(self, audio_np, sample_rate):
        """
        Enhance the input audio using DeepFilterNet.
        
        Parameters:
            audio_np (numpy.ndarray): Input audio waveform.
            sample_rate (int): Sample rate of the audio.

        Returns:
            numpy.ndarray: Enhanced audio waveform.
        """
        try:
            # Convert NumPy array to Torch tensor
            audio_tensor = torch.tensor(audio_np, dtype=torch.float32).unsqueeze(0).to(self.device)
            
            # Process audio through DeepFilterNet
            with torch.no_grad():
                enhanced_audio = self.model(audio_tensor).squeeze(0).cpu().numpy()
            
            return enhanced_audio
        except Exception as e:
            print(f"DeepFilterNet processing error: {e}")
            return audio_np  # Return original audio in case of error
