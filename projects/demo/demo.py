patch = ObliquePatch()

# Inputs
audio = patch.input(AudioIn(device="Elektron", channel=3))
midi = patch.input(MidiIn(port="MIDI Device 1"))

# Feature extraction
amp = patch.add(Amplitude(), inputs=[audio])
bands = patch.add(FFT(bands=16), inputs=[audio])
impulses = patch.add(ImpulseDetect(), inputs=[audio])

# Rendering
grid = patch.add(GridRenderer(grid_size=(8,8)), inputs=[bands, amp, impulses, midi])

# Post FX: frame shake triggered by kick band (assume bands[0] = kick)
frame_shake = patch.render(FrameShaker(source_band=0), inputs=[grid, bands])


# patch.run()