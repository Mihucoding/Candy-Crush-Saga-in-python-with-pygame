import math
import array
import pygame
import random

_SAMPLE_RATE = 22050


def _synth(notes: list[tuple[float, float]], volume: float = 0.45, harmonics: bool = True) -> pygame.mixer.Sound:
    """Build a Sound from a list of (freq_hz, duration_sec) notes. Supports harmonics."""
    buf = array.array('h')
    for freq, dur in notes:
        n = int(_SAMPLE_RATE * dur)
        attack = int(_SAMPLE_RATE * 0.01)
        release = int(_SAMPLE_RATE * 0.05)
        for i in range(n):
            env = (
                min(1.0, i / attack) *
                min(1.0, (n - i) / max(1, release))
            )
            if freq == 0:
                sample = 0
            else:
                # Fundamental
                s = math.sin(2 * math.pi * freq * i / _SAMPLE_RATE)
                if harmonics:
                    # Add overtones for a richer, "instrumental" feel
                    s += 0.5 * math.sin(4 * math.pi * freq * i / _SAMPLE_RATE)
                    s += 0.25 * math.sin(6 * math.pi * freq * i / _SAMPLE_RATE)
                    s /= 1.75
                sample = int(32767 * volume * env * s)
            buf.append(sample)
    return pygame.mixer.Sound(buffer=buf)


def _chord(freqs: list[float], dur: float, volume: float = 0.35) -> pygame.mixer.Sound:
    """Build a rich chord from multiple frequencies."""
    n = int(_SAMPLE_RATE * dur)
    buf = array.array('h')
    attack = int(_SAMPLE_RATE * 0.05)
    release = int(_SAMPLE_RATE * 0.15)
    for i in range(n):
        env = min(1.0, i / attack) * min(1.0, (n - i) / max(1, release))
        sample_sum = 0.0
        for f in freqs:
            # Each note in chord has its own harmonics
            s = math.sin(2 * math.pi * f * i / _SAMPLE_RATE)
            s += 0.4 * math.sin(4 * math.pi * f * i / _SAMPLE_RATE)
            sample_sum += s
        sample_sum /= len(freqs)
        buf.append(int(32767 * volume * env * sample_sum))
    return pygame.mixer.Sound(buffer=buf)


def _sweep(freq_start: float, freq_end: float, duration: float, volume: float = 0.45) -> pygame.mixer.Sound:
    """Exponential frequency glide — great for special-candy whoosh effects."""
    n       = int(_SAMPLE_RATE * duration)
    attack  = int(_SAMPLE_RATE * 0.015)
    release = int(_SAMPLE_RATE * 0.045)
    buf     = array.array('h')
    phase   = 0.0
    for i in range(n):
        env = (
            min(1.0, i / max(1, attack)) *
            min(1.0, (n - i) / max(1, release))
        )
        t    = i / n
        freq = freq_start * ((freq_end / max(1, freq_start)) ** t)
        phase += 2 * math.pi * freq / _SAMPLE_RATE
        # Add a harmonic shimmer to the sweep
        s = math.sin(phase) + 0.3 * math.sin(2 * phase)
        buf.append(int(32767 * volume * env * s / 1.3))
    return pygame.mixer.Sound(buffer=buf)


def _noise_pop(volume: float = 0.4) -> pygame.mixer.Sound:
    """Improved layered candy pop with a tone and noise component."""
    n = int(_SAMPLE_RATE * 0.12)
    buf = array.array('h')
    # A quick descending pitch sweep + noise
    for i in range(n):
        t = i / n
        env = (1.0 - t) ** 1.5
        # Pitch sweep from 800Hz to 400Hz
        freq = 800 - 400 * t
        tone = math.sin(2 * math.pi * freq * i / _SAMPLE_RATE)
        noise = random.uniform(-1, 1)
        # Mix tone (70%) and noise (30%)
        val = (tone * 0.7 + noise * 0.3) * env
        buf.append(int(32767 * volume * val))
    return pygame.mixer.Sound(buffer=buf)


class SoundManager:
    def __init__(self):
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._enabled = True
        self._build()

    def _build(self) -> None:
        # Basic UI sounds
        self._sounds["select"]  = _synth([(880, 0.05)], volume=0.3)
        self._sounds["swap"]    = _synth([(660, 0.06), (880, 0.08)], volume=0.4)
        self._sounds["invalid"] = _synth([(180, 0.08), (140, 0.12)], volume=0.5, harmonics=False)
        self._sounds["button"]  = _synth([(600, 0.05)], volume=0.3)
        
        # Pop & Combos
        self._sounds["pop"]     = _noise_pop()
        self._sounds["combo2"]  = _synth([(440, 0.08), (554.37, 0.08)], volume=0.45) # A4, C#5
        self._sounds["combo3"]  = _synth([(554.37, 0.07), (659.25, 0.07), (880, 0.1)], volume=0.45) # C#5, E5, A5
        self._sounds["combo4"]  = _synth([(440, 0.05), (554.37, 0.05), (659.25, 0.05), (880, 0.05), (1108.73, 0.1)], volume=0.45)
        
        # Special Effects — rising sweep for a dramatic whoosh
        self._sounds["special"] = _sweep(400, 1800, 0.28, volume=0.52)
        
        # Win / Game Over
        self._sounds["win"]      = _chord([523.25, 659.25, 783.99, 1046.50], 0.8, volume=0.5) # C Major chord
        self._sounds["gameover"] = _chord([220, 233.08, 261.63], 1.2, volume=0.4) # Discordant low chord

    def play(self, name: str) -> None:
        if not self._enabled:
            return
        sound = self._sounds.get(name)
        if sound:
            sound.play()

    def play_combo(self, combo: int) -> None:
        if combo >= 4:
            self.play("combo4")
        elif combo == 3:
            self.play("combo3")
        elif combo == 2:
            self.play("combo2")

    def toggle(self) -> bool:
        self._enabled = not self._enabled
        return self._enabled
