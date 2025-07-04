from .base_input import BaseInput
from typing import Any, Optional
import soundfile as sf
import numpy as np
import collections

class AudioDeviceInput(BaseInput):
    HISTORY_SIZE = 4  # Class-level constant for buffer history size
    """
    Input class that reads audio from a file for testing and prototyping.
    """
    def __init__(self, file_path: str, chunk_size: int = 1024, config: Optional[dict] = None) -> None:
        """
        :param file_path: Path to the audio file to read.
        :param chunk_size: Number of samples per read.
        :param config: Optional configuration dictionary.
        """
        super().__init__(config)
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.file = None
        self.samplerate = None
        self.channels = None
        self._buffer = None
        self._pos = 0
        self._last_chunk = None # Initialize for peek()
        self._chunk_history = collections.deque(maxlen=self.HISTORY_SIZE)

    def start(self) -> None:
        """
        Open the audio file and prepare for reading.
        """
        self._buffer, self.samplerate = sf.read(self.file_path, always_2d=True)
        self.channels = self._buffer.shape[1]
        self._pos = 0
        self._chunk_history.clear()

    def stop(self) -> None:
        """
        Stop reading and release resources.
        """
        self._buffer = None
        self._pos = 0
        self._last_chunk = None # Clear cached chunk on stop
        self._chunk_history.clear()

    def read(self) -> np.ndarray:
        """
        Read the next chunk of audio data, advancing the buffer position.
        :return: Numpy array of shape (chunk_size, channels)
        """
        if self._buffer is None:
            raise RuntimeError("AudioDeviceInput not started. Call start() first.")
        start = self._pos
        end = min(self._pos + self.chunk_size, self._buffer.shape[0])
        chunk = self._buffer[start:end]
        self._pos = end
        self._last_chunk = chunk  # Cache the last chunk for peek()
        self._chunk_history.append(chunk)
        return chunk

    def peek(self, n_buffers: Optional[int] = None) -> Optional[np.ndarray]:
        """
        Return the most recently read chunk or up to the last n_buffers chunks concatenated.
        :param n_buffers: Number of previous chunks to return (concatenated). If None, returns the most recent chunk.
        :return: Numpy array of shape (n*chunk_size, channels) or None if not available
        """
        if n_buffers is None:
            return self._last_chunk
        if n_buffers <= 0 or len(self._chunk_history) == 0:
            return None
        # Get up to n_buffers most recent chunks
        chunks = list(self._chunk_history)[-n_buffers:]
        if not chunks:
            return None
        return np.concatenate(chunks, axis=0)

if __name__ == "__main__":
    import sys
    import time
    file_path = sys.argv[1] if len(sys.argv) > 1 else "../projects/demo/audio/Just takes one try mix even shorter [master]19.06.2025.wav"
    input_device = AudioDeviceInput(file_path, chunk_size=2048)
    input_device.start()
    print(f"Samplerate: {input_device.samplerate}, Channels: {input_device.channels}")
    for i in range(5):
        chunk = input_device.read()
        print(f"Chunk {i}: shape={chunk.shape}, mean={chunk.mean():.4f}")
        time.sleep(0.1)
    input_device.stop() 