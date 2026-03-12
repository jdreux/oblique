from core.oblique_patch import ObliquePatch
from inputs.audio.core.audio_file_input import AudioFileInput
from modules.composition.composite_module import CompositeOp
from modules.core.base_av_module import BaseAVModule
from modules.effects.barrel_distortion import BarrelDistortionModule
from modules.effects.feedback import FeedbackModule
from modules.effects.level_module import LevelModule
from modules.generative.calabi_yau import CalabiYau, CalabiYauParams
from modules.generative.rotating_cube import RotatingCube, RotatingCubeParams
from processing.fft_bands import FFTBands
from processing.normalized_amplitude import NormalizedAmplitudeOperator
from processing.spectral_centroid import SpectralCentroid


class Smooth:
    """Exponential moving average — fast attack, slow release."""

    def __init__(self, attack: float = 0.3, release: float = 0.05):
        self._attack = attack
        self._release = release
        self._value = 0.0

    def update(self, raw: float) -> float:
        coeff = self._attack if raw > self._value else self._release
        self._value += coeff * (raw - self._value)
        return self._value


def oblique_patch(width: int, height: int) -> ObliquePatch:
    audio = AudioFileInput(
        file_path="projects/demo/audio/"
        "Just takes one try mix even shorter [master]19.06.2025.wav"
    )

    amplitude = NormalizedAmplitudeOperator(audio)
    fft = FFTBands(audio, num_bands=8)
    centroid = SpectralCentroid(audio)

    smooth_amp = Smooth(attack=0.4, release=0.04)
    smooth_bass = Smooth(attack=0.5, release=0.03)
    smooth_cent = Smooth(attack=0.15, release=0.02)
    smooth_mix = Smooth(attack=0.08, release=0.02)

    # --- Tesseract: sharp, geometric, cold-blue ---
    tess = RotatingCube(
        RotatingCubeParams(
            width=width,
            height=height,
            speed=0.8,
            edge_width=1.5,
            cube_size=0.18,
            explode=0.7,
        )
    )

    # --- Calabi-Yau: organic, folded, warm-pink ---
    cy = CalabiYau(
        CalabiYauParams(
            width=width,
            height=height,
            speed=0.6,
            fold_depth=0.22,
            scale=0.4,
        )
    )

    mix_amount = [0.5]

    def tick(t: float) -> BaseAVModule:
        amp = smooth_amp.update(amplitude.process())
        bands = fft.process()
        bass = smooth_bass.update((bands[0] + bands[1]) * 0.5)
        cent = smooth_cent.update(centroid.process())

        tess.params.amplitude = amp
        tess.params.bass = bass
        tess.params.centroid = cent

        cy.params.amplitude = amp
        cy.params.bass = bass
        cy.params.centroid = cent

        # Crossfade: bass-heavy → tesseract, bright/high → CY
        target = cent * 0.6 + (1.0 - bass) * 0.4
        mix_amount[0] = smooth_mix.update(target)

        # Mix raw modules first, then shared post-processing
        scene = (
            tess
            .mix(cy, amount=mix_amount[0], op=CompositeOp.SCREEN)
            .to(FeedbackModule, feedback_strength=0.75, direction=(0.0, -0.0005))
            .to(BarrelDistortionModule, strength=0.06 + amp * 0.1)
            .to(LevelModule, contrast=1.1)
        )

        return scene

    return ObliquePatch(audio_output=audio, tick_callback=tick)
