import collections
from pathlib import Path
from typing import List, Optional

import numpy as np
import soundfile as sf

from core.logger import debug, info
from core.paths import resolve_asset_path

from .base_audio_input import BaseAudioInput

SUPPORTED_FORMATS = ('.wav', '.flac', '.aiff', '.aif', '.ogg')

class AudioFileInput(BaseAudioInput):
    HISTORY_SIZE = 4  # Class-level constant for buffer history size
    """
    Input class that reads audio from a file for testing and prototyping.
    """

    def __init__(
        self, file_path: str, chunk_size: int = 1024
    ) -> None:
        """
        :param file_path: Path to the audio file to read.
        :param chunk_size: Number of samples per read.
        :param config: Optional configuration dictionary.
        """
        super().__init__(chunk_size=chunk_size)
        # Validate supported audio file formats
        if not file_path.lower().endswith(SUPPORTED_FORMATS):
            raise ValueError(
                f"Unsupported audio file format for '{file_path}'. "
                f"Supported formats are: {', '.join(SUPPORTED_FORMATS)}"
            )

        source_path = Path(file_path)
        candidate_paths = [source_path]
        if not source_path.is_absolute():
            asset_candidate = resolve_asset_path(file_path)
            if asset_candidate not in candidate_paths:
                candidate_paths.append(asset_candidate)

        for candidate in candidate_paths:
            if candidate.exists():
                source_path = candidate
                break
        else:
            searched = ", ".join(str(path) for path in candidate_paths)
            raise FileNotFoundError(
                f"Audio file '{file_path}' was not found. Checked: {searched}."
            )

        self.file_path = str(source_path)
        self.file = None
        self.samplerate = None
        self.channels = None
        self._buffer = None
        self._pos = 0
        self._last_chunk = None  # Initialize for peek()
        self._chunk_history = collections.deque(maxlen=self.HISTORY_SIZE)    
        try:
            self._buffer, self.samplerate = sf.read(self.file_path, always_2d=True)
        except Exception as e:
            error_msg = f"Failed to read audio file '{self.file_path}': {e}"
            info(error_msg)
            raise RuntimeError(error_msg) from e
        self.channels = self._buffer.shape[1]

    def start(self) -> None:
        """
        Open the audio file and prepare for reading.
        """
        self._pos = 0
        self._chunk_history.clear()

    def stop(self) -> None:
        """
        Stop reading and release resources.
        """
        self._buffer = None
        self._pos = 0
        self._last_chunk = None  # Clear cached chunk on stop
        self._chunk_history.clear()

    def read(self, channels=None) -> np.ndarray:
        """
        Read the next chunk of audio data, advancing the buffer position.
        :param channels: Ignored for file input (all channels are returned).
        :return: Numpy array of shape (chunk_size, channels)
        """
        if self._buffer is None:
            raise RuntimeError("AudioFileInput not started. Call start() first.")
        start = self._pos
        end = min(self._pos + self.chunk_size, self._buffer.shape[0])
        chunk = self._buffer[start:end]
        self._pos = end
        self._last_chunk = chunk  # Cache the last chunk for peek()
        self._chunk_history.append(chunk)
        return chunk

    def peek(self, n_buffers: int = 1, channels: Optional[List[int]] = None) -> Optional[np.ndarray]:
        """
        Return the most recently read chunk or up to the last n_buffers chunks concatenated. Does not advance the buffer position.
        :param n_buffers: Number of previous chunks to return (concatenated). If None, returns the most recent chunk.
        :param channels: Ignored for file input (all channels are returned).
        :return: Numpy array of shape (n*chunk_size, channels) or None if not available
        """
        if n_buffers == 1:
            return self._last_chunk
        if n_buffers <= 0 or len(self._chunk_history) == 0:
            return None
        # Get up to n_buffers most recent chunks
        chunks = list(self._chunk_history)[-n_buffers:]
        if not chunks:
            return None
        return np.concatenate(chunks, axis=0)

    @property
    def sample_rate(self) -> int:
        """
        Get the sample rate of the input source in Hz.
        :return: Sample rate in Hz.
        """
        if self.samplerate is None:
            raise RuntimeError("AudioFileInput not started. Call start() first.")
        return int(self.samplerate)

    @property
    def num_channels(self) -> int:
        """
        Get the number of audio channels in the input source.
        :return: Number of channels (1 for mono, 2 for stereo, etc.).
        """
        if self.channels is None:
            raise RuntimeError("AudioFileInput not started. Call start() first.")
        return self.channels

    @property
    def device_name(self) -> str:
        """
        Get a human-readable name for the input device/source.
        :return: Human-readable device name.
        """
        import os
        filename = os.path.basename(self.file_path)
        return f"File: {filename}"


if __name__ == "__main__":
    import sys
    import time

    file_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else str(
            resolve_asset_path(
                "projects/demo/audio/Just takes one try mix even shorter [master]19.06.2025.wav"
            )
        )
    )
    input_device = AudioFileInput(file_path, chunk_size=2048)
    input_device.start()
    info(f"File Input - Samplerate: {input_device.samplerate}, Channels: {input_device.channels}")
    for i in range(5):
        chunk = input_device.read()
        debug(f"Chunk {i}: shape={chunk.shape}, mean={chunk.mean():.4f}")
        time.sleep(0.1)
    input_device.stop()
