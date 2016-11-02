import math
import struct
import wave
from contextlib import contextmanager

DEFAULT_FRAMERATE = 44100
DEFAULT_ATTACK = .02
DEFAULT_RELEASE = .02


def generate_sine_wave(
        freq=440,
        duration=10,
        framerate=DEFAULT_FRAMERATE,
        sample_width=2,
        volume=.8,
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
        # yield int(math.sin(2 * math.pi * f / attack_frames)) * volume

    for f in range(sound_frames):
        yield volume

    for f in range(release_frames, 0, -1):
        yield volume * f / release_frames
        # yield int(math.sin(2 * math.pi * f / release_frames)) * volume


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


def generate_morse(text, fp, wpm=60, tone=800):

    # dit: 10
    # dah: 1110
    # letter A: 10111000
    # letter S: 10101000
    # -> Space between letters is 3D, becomes 2
    # -> Space between words is 7D, becomes 4

    DOT_LENGTH = 1.2 / wpm
    DOT_SPACE = encode_fragment(generate_silence(duration=DOT_LENGTH))
    LETTER_SPACE = DOT_SPACE * 2  # DOT_SPACE + 2
    WORD_SPACE = DOT_SPACE * 2  # DOT_SPACE + LETTER_SPACE + 2 + DOT_SPACE
    DIT = encode_fragment(generate_sine_wave(tone, duration=DOT_LENGTH)) \
        + DOT_SPACE
    DAH = encode_fragment(generate_sine_wave(tone, duration=DOT_LENGTH * 3)) \
        + DOT_SPACE

    SOUND_TABLE = {
        'a': (DIT, DAH),
        'b': (DAH, DIT, DIT, DIT),
        'c': (DAH, DIT, DAH, DIT),
        'd': (DAH, DIT, DIT),
        'e': (DIT, ),
        'f': (DIT, DIT, DAH, DIT),
        'g': (DAH, DAH, DIT),
        'h': (DIT, DIT, DIT, DIT),
        'i': (DIT, DIT),
        'j': (DIT, DAH, DAH, DAH),
        'k': (DAH, DIT, DAH),
        'l': (DIT, DAH, DIT, DIT),
        'm': (DAH, DAH),
        'n': (DAH, DIT),
        'o': (DAH, DAH, DAH),
        'p': (DIT, DAH, DAH, DIT),
        'q': (DAH, DAH, DIT, DAH),
        'r': (DIT, DAH, DIT),
        's': (DIT, DIT, DIT),
        't': (DAH, ),
        'u': (DIT, DIT, DAH),
        'v': (DIT, DIT, DIT, DAH),
        'w': (DAH, DIT, DIT),
        'x': (DAH, DIT, DIT, DAH),
        'y': (DAH, DIT, DAH, DAH),
        'z': (DAH, DAH, DIT, DIT),
        ' ': (WORD_SPACE, ),
        '\n': (DIT, DAH, DIT, DAH),
        '\r': (),
        '0': (DAH, DAH, DAH, DAH, DAH),
        '1': (DIT, DAH, DAH, DAH, DAH),
        '2': (DIT, DIT, DAH, DAH, DAH),
        '3': (DIT, DIT, DIT, DAH, DAH),
        '4': (DIT, DIT, DIT, DIT, DAH),
        '5': (DIT, DIT, DIT, DIT, DIT),
        '6': (DAH, DIT, DIT, DIT, DIT),
        '7': (DAH, DAH, DIT, DIT, DIT),
        '8': (DAH, DAH, DAH, DIT, DIT),
        '9': (DAH, DAH, DAH, DAH, DIT),
        '.': (DIT, DAH, DIT, DAH, DIT, DAH),
        ',': (DAH, DAH, DIT, DIT, DAH, DAH),
        '/': (DAH, DIT, DIT, DAH, DIT),
        '?': (DIT, DIT, DAH, DAH, DIT, DIT),
        '=': (DAH, DIT, DIT, DIT, DAH),
        "'": (DIT, DAH, DAH, DAH, DAH, DIT),
        '!': (DAH, DIT, DAH, DIT, DAH, DAH),
        '(': (DAH, DIT, DAH, DAH, DIT),
        ')': (DAH, DIT, DAH, DAH, DIT, DAH),
        '&': (DIT, DAH, DIT, DIT, DIT),
        ':': (DAH, DAH, DAH, DIT, DIT, DIT),
        ';': (DAH, DIT, DAH, DIT, DAH, DIT),
        '+': (DIT, DAH, DIT, DAH, DIT),
        '-': (DAH, DIT, DIT, DIT, DIT, DAH),
        '_': (DIT, DIT, DAH, DAH, DIT, DAH),
        '"': (DIT, DAH, DIT, DIT, DAH, DIT),
        '$': (DIT, DIT, DIT, DAH, DIT, DIT, DAH),
    }

    for letter in text.lower():
        sound = SOUND_TABLE.get(letter)
        if sound is None:
            print('Unknown letter or symbol: {}'.format(sound))
            continue
        for elem in sound:
            fp.writeframes(elem)
        fp.writeframes(LETTER_SPACE)


def example():

    with wavewriter('hello.wav') as fp:
        fp.writeframes(encode_fragment(generate_silence(1)))
        text = 'cq cq cq cq = The quick brown fox jumps over the lazy dog'
        generate_morse(text, fp, wpm=20, tone=600)

if __name__ == '__main__':
    example()
