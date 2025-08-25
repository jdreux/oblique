from enum import IntEnum, unique
from typing import List, Optional

from core.logger import error, info, warning
from inputs.audio.core import AudioDeviceInput, list_audio_devices
from inputs.audio.core.audio_device_channel_input import AudioDeviceChannelInput
from inputs.midi.core.midi_input import MidiInput, list_midi_input_ports


@unique
class SyntaktChannel(IntEnum):
    MAIN_L = 0
    MAIN_R = 1
    TRACK_1 = 2
    TRACK_2 = 3
    TRACK_3 = 4
    TRACK_4 = 5
    TRACK_5 = 6
    TRACK_6 = 7
    TRACK_7 = 8
    TRACK_8 = 9
    TRACK_9 = 10
    TRACK_10 = 11
    TRACK_11 = 12
    TRACK_12 = 13
    FX_TRACK_L = 14
    FX_TRACK_R = 15
    DELAY_REVERB_L = 16
    DELAY_REVERB_R = 17
    INPUT_L = 18
    INPUT_R = 19

    @classmethod
    def main_lr_channels(cls) -> List[int]:
        """Return a list of the main L/R channel enums."""
        return [cls.MAIN_L.value, cls.MAIN_R.value]



class SyntaktDevice:
    """
    Wrapper class for Elektron Syntakt devices connected in Overbridge mode.
    
    Provides unified access to both audio and MIDI inputs from a Syntakt device.
    Can auto-discover Syntakt devices or use specified device IDs.
    """


    def __init__(
        self,
        audio_device_id: Optional[int] = None,
        midi_port_name: Optional[str] = None,
        samplerate: int = 44100,
        chunk_size: int = 256
    ):
        """
        Initialize Syntakt device wrapper.
        
        Args:
            audio_device_id: Specific audio device ID. If None, auto-discovers Syntakt audio device.
            midi_port_name: Specific MIDI port name. If None, auto-discovers Syntakt MIDI port.
            audio_channels: List of audio channels to capture. If None, captures all available channels.
            samplerate: Audio sample rate in Hz.
            chunk_size: Audio chunk size for real-time processing.
        """
        self.audio_device_id = audio_device_id
        self.midi_port_name = midi_port_name
        self.samplerate = samplerate
        self.chunk_size = chunk_size

        # Initialize inputs as None
        self.audio_input: Optional[AudioDeviceInput] = None
        self.midi_input: Optional[MidiInput] = None

        # Device discovery if not explicitly provided
        if self.audio_device_id is None:
            self.audio_device_id = self._discover_syntakt_audio_device()

        if self.midi_port_name is None:
            self.midi_port_name = self._discover_syntakt_midi_port()

        # Initialize inputs with discovered or provided device IDs
        self._initialize_inputs()

    def _discover_syntakt_audio_device(self) -> Optional[int]:
        """
        Auto-discover Syntakt audio device by searching for 'syntakt' in device names.
        
        Returns:
            Device ID if found, None otherwise.
        """
        audio_devices = list_audio_devices()

        for device in audio_devices:
            device_name = device['name'].lower()
            if 'syntakt' in device_name:
                info(f"Found Syntakt audio device: {device['name']} (ID: {device['id']})")
                return device['id']

        warning("No Syntakt audio device found. Available devices:")
        for device in audio_devices:
            info(f"  - {device['name']} (ID: {device['id']})")

        return None

    def _discover_syntakt_midi_port(self) -> Optional[str]:
        """
        Auto-discover Syntakt MIDI port by searching for 'syntakt' in port names.
        
        Returns:
            MIDI port name if found, None otherwise.
        """
        midi_ports = list_midi_input_ports()

        for port_name in midi_ports:
            if 'syntakt' in port_name.lower():
                info(f"Found Syntakt MIDI port: {port_name}")
                return port_name

        warning("No Syntakt MIDI port found. Available ports:")
        for port_name in midi_ports:
            info(f"  - {port_name}")

        return None

    def _initialize_inputs(self) -> None:
        """Initialize audio and MIDI inputs with discovered or provided device information."""
        if self.audio_device_id is not None:
            try:
                self.audio_input = AudioDeviceInput(
                    device_id=self.audio_device_id,
                    samplerate=self.samplerate,
                    chunk_size=self.chunk_size
                )

                expected_channel_count = len([member for member in SyntaktChannel])
                assert (
                    self.audio_input.num_channels == expected_channel_count
                ), (
                    f"Syntakt audio input has {self.audio_input.num_channels} channels, "
                    f"expected {expected_channel_count} - are you connected in Overbridge mode?"
                )
                info(f"Initialized Syntakt audio input: {self.audio_input.device_name}")
            except Exception as e:
                error(f"Failed to initialize Syntakt audio input: {e}")
                self.audio_input = None

        if self.midi_port_name is not None:
            try:
                self.midi_input = MidiInput(port_name=self.midi_port_name)
                info(f"Initialized Syntakt MIDI input: {self.midi_port_name}")
            except Exception as e:
                error(f"Failed to initialize Syntakt MIDI input: {e}")
                self.midi_input = None

    @property
    def device_name(self) -> str:
        """Get a human-readable name for the Syntakt device."""
        audio_name = self.audio_input.device_name if self.audio_input else "No Audio"
        midi_name = self.midi_input.device_name if self.midi_input else "No MIDI"
        return f"Syntakt Device (Audio: {audio_name}, MIDI: {midi_name})"

    @property
    def is_connected(self) -> bool:
        """Check if both audio and MIDI connections are available."""
        return self.audio_input is not None and self.midi_input is not None

    @property
    def has_audio(self) -> bool:
        """Check if audio connection is available."""
        return self.audio_input is not None

    @property
    def has_midi(self) -> bool:
        """Check if MIDI connection is available."""
        return self.midi_input is not None

    def start(self) -> None:
        """Start both audio and MIDI input streams."""
        if self.audio_input:
            try:
                self.audio_input.start()
                info("Started Syntakt audio input")
            except Exception as e:
                error(f"Failed to start Syntakt audio input: {e}")

        if self.midi_input:
            try:
                self.midi_input.start()
                info("Started Syntakt MIDI input")
            except Exception as e:
                error(f"Failed to start Syntakt MIDI input: {e}")

    def stop(self) -> None:
        """Stop both audio and MIDI input streams."""
        if self.audio_input:
            try:
                self.audio_input.stop()
                info("Stopped Syntakt audio input")
            except Exception as e:
                error(f"Failed to stop Syntakt audio input: {e}")

        if self.midi_input:
            try:
                self.midi_input.stop()
                info("Stopped Syntakt MIDI input")
            except Exception as e:
                error(f"Failed to stop Syntakt MIDI input: {e}")

    def get_main_lr_track(self) ->  AudioDeviceChannelInput:
        """Get the mix L/R audio device channel input."""
        return self.get_audio_device.get_channel_audio_input(channels=SyntaktChannel.main_lr_channels())

    def get_track(self, track_number: SyntaktChannel) -> AudioDeviceChannelInput:
        """Get the track L/R audio device channel input."""
        return self.get_audio_device.get_channel_audio_input(channels=[track_number.value])


    @property
    def get_audio_device(self) -> AudioDeviceInput:
        """Get the audio device input for direct manipulation."""
        if self.audio_input is None:
            raise ValueError("Audio device not found - check that Syntakt is connected in Overbridge mode")
        return self.audio_input

    @property
    def get_midi_device(self) -> MidiInput:
        """Get the MIDI input."""
        if self.midi_input is None:
            raise ValueError("MIDI device not found - check if Syntakt is connected in Overbridge mode")
        return self.midi_input
