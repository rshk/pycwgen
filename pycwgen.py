import math
import struct
import wave
from contextlib import contextmanager

DEFAULT_FRAMERATE = 44100
DEFAULT_ATTACK = .03
DEFAULT_RELEASE = .03


def generate_sine_wave(
        freq=440,
        duration=10,
        framerate=DEFAULT_FRAMERATE,
        sample_width=2,
        volume=.9,
        attack=DEFAULT_ATTACK,
        release=DEFAULT_RELEASE):

    max_ampl = (2 ** (sample_width * 8 - 1))
    envelope = iter(generate_envelope(
        framerate, duration, volume, attack, release))
    return [
        int(math.sin(2 * math.pi * freq * i / framerate)
            * max_ampl * next(envelope))
        for i in range(int(framerate * duration))]


def generate_envelope(framerate, duration, volume, attack, release):
    if (attack + release) > duration:
        raise ValueError('Attack and release cannot be > duration')
    attack_frames = int(attack * framerate)
    release_frames = int(release * framerate)
    sound_frames = int(framerate * duration) - attack_frames - release_frames

    for f in range(0, attack_frames, 1):
        yield volume * f / attack_frames

    for f in range(sound_frames):
        yield volume

    for f in range(release_frames, 0, -1):
        yield volume * f / release_frames


def generate_silence(duration=10, framerate=DEFAULT_FRAMERATE):
    return [0 for i in range(int(framerate * duration))]


def convert_sample(sample, bits=16):
    return int(sample * (2 ** (bits - 1) - 1))


@contextmanager
def wavewriter(filename, channels=1, sample_width=2,
               framerate=DEFAULT_FRAMERATE):

    assert channels == 1  # Not supported otherwise

    fp = wave.open(filename, 'wb')
    fp.setnchannels(channels)
    fp.setsampwidth(sample_width)
    fp.setframerate(framerate)
    yield fp
    fp.close()


def encode_fragment(fragment, sample_width=2):
    if sample_width == 1:
        fmt = 'b'
    elif sample_width == 2:
        fmt = 'h'
    elif sample_width == 4:
        fmt = 'i'
    else:
        raise ValueError('Unsupported sample width')

    return struct.pack('<' + (fmt * len(fragment)), *fragment)


def example():

    WPM = 12
    FREQ = 600

    DOT_LENGTH = 1.2 / WPM
    DOT_SPACE = encode_fragment(generate_silence(duration=DOT_LENGTH))
    LETTER_SPACE = DOT_SPACE * 2
    WORD_SPACE = DOT_SPACE * 4
    DIT = encode_fragment(generate_sine_wave(FREQ, duration=DOT_LENGTH)) \
        + DOT_SPACE
    DAH = encode_fragment(generate_sine_wave(FREQ, duration=DOT_LENGTH * 3)) \
        + DOT_SPACE

    LETTER_C = DAH + DIT + DAH + DIT + LETTER_SPACE
    LETTER_Q = DAH + DAH + DIT + DAH + LETTER_SPACE

    with wavewriter('hello.wav') as fp:
        fp.writeframes(encode_fragment(generate_silence(1)))
        for i in range(4):
            fp.writeframes(LETTER_C)
            fp.writeframes(LETTER_Q)
            fp.writeframes(WORD_SPACE)

if __name__ == '__main__':
    example()
