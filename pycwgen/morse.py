import logging
import re

import numpy

from .synth import generate_silence, generate_sine_wave

logger = logging.getLogger(__name__)

DIT = object()
DAH = object()
SYMBOL_SPACE = object()
LETTER_SPACE = object()
WORD_SPACE = object()

MORSE_TABLE = {
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
    'w': (DIT, DAH, DAH),
    'x': (DAH, DIT, DIT, DAH),
    'y': (DAH, DIT, DAH, DAH),
    'z': (DAH, DAH, DIT, DIT),
    # '\n': (DIT, DAH, DIT, DAH),
    # '\r': (),
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


def generate_morse_code(text, wpm, tone=600, normalize=True):
    if normalize:
        text = normalize_text(text)
    samples = list(_generate_morse_samples(text, wpm, tone))
    return numpy.concatenate(samples)


def stream_morse_code(fp, text, wpm, tone=600, normalize=True):
    if normalize:
        text = normalize_text(text)
    for sample in _generate_morse_samples(text, wpm, tone):
        fp.write(sample)


def _generate_morse_samples(text, wpm, tone):
    dit_duration = 1.2 / wpm
    dah_duration = dit_duration * 3
    symbol_space_duration = dit_duration
    letter_space_duration = (dit_duration * 3) - symbol_space_duration
    word_space_duration = (dit_duration * 7) - letter_space_duration

    audio_params = {
        'attack': dit_duration / 10,
        'release': dit_duration / 10,
        'volume': .9,
    }

    samples = {
        DIT: generate_sine_wave(tone, dit_duration, **audio_params),
        DAH: generate_sine_wave(tone, dah_duration, **audio_params),
        SYMBOL_SPACE: generate_silence(symbol_space_duration),
        LETTER_SPACE: generate_silence(letter_space_duration),
        WORD_SPACE: generate_silence(word_space_duration),
    }

    def _encode_letter(letter):
        if letter == ' ':
            yield samples[WORD_SPACE]
            return

        symbols = MORSE_TABLE.get(letter)
        if not symbols:
            logger.warning('Unsupported symbol: {}'.format(repr(letter)))
            return

        for symbol in symbols:
            yield samples[symbol]
            yield samples[SYMBOL_SPACE]
        yield samples[LETTER_SPACE]

    for letter in normalize_text(text):
        yield from _encode_letter(letter)


def normalize_text(text):
    text = text.lower()
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    return text
