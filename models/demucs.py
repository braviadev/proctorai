import torch
import torchaudio
from demucs import pretrained

class DemucsModel:
    def __init__(self):
        """Load the pretrained Demucs model."""
        self.model = pretrained.get_model(name="htdemucs")
        self.model.to("cpu").eval()  # Use CPU (change to 'cuda' for GPU)

    def separate(self, audio_np, sample_rate=16000):
        """Perform source separation on the given audio."""
        # Convert NumPy array to PyTorch tensor
        audio_tensor = torch.tensor(audio_np, dtype=torch.float32).unsqueeze(0)
        
        # Resample if needed
        if sample_rate != 44100:
            audio_tensor = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=44100)(audio_tensor)
        
        # Run the model
        with torch.no_grad():
            sources = self.model(audio_tensor)
        
        # Convert output to dictionary
        separated_sources = {"vocals": sources[0][0].numpy(), "accompaniment": sources[0][1].numpy()}
        return separated_sources

# Example usage:
# demucs = DemucsModel()
# separated = demucs.separate(audio_np, sample_rate=16000)
