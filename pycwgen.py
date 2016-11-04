import argparse
import logging
import math
import re
import struct
import subprocess
import sys
from array import array
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DEFAULT_FRAMERATE = 44100
DEFAULT_ATTACK = .02
DEFAULT_RELEASE = .02

FMT_MP3 = 'mp3'
FMT_OGG = 'ogg'
FMT_WAV = 'wav'
FMT_PCM = 'pcm'

AUDIO_FORMATS = [FMT_PCM, FMT_WAV, FMT_MP3, FMT_OGG]

SAMPLE_FORMATS = [
    # 'u8', 's8',
    # 'u16le', 'u16be',
    's16le',
    # 's16be',
    # 'u24le', 'u24be', 's24le', 's24be',
    # 'u32le', 'u32be', 's32le', 's32be',
    # 'floatle', 'floatbe', 'doublele', 'doublebe',
    # 'u16', 's16',
    # 'u24', 's24',
    # 'u32', 's32',
    # 'float', 'double',
]


DIT = object()
DAH = object()
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


class AudioGenerator:

    def __init__(self, framerate=DEFAULT_FRAMERATE, samplefmt='s16le'):
        self.framerate = framerate
        if samplefmt not in SAMPLE_FORMATS:
            raise ValueError('Invalid sample format: {}. Supported are: {}.'
                             .format(samplefmt, ', '.join(SAMPLE_FORMATS)))
        self.samplefmt = samplefmt

    def generate_sine_wave(self, freq=440, duration=1000):
        """Generate a sine wave.

        Args:
            freq: frequency, in Hertz
            duration: sample duration, in milliseconds
            volume: maximum volume, float between 0 and 1
            attack: attack time, in ms
            release: release time, in ms
        """

        assert self.samplefmt == 's16le'

        for i in range(int(self.framerate * duration / 1000)):
            value = math.sin(2.0 * math.pi * freq * i / self.framerate)
            yield int(value * 32767)  # FIXME respect sample format

    def add_envelope(self, sample, volume=1.0, attack=0, release=0):
        """Add envelope to an audio sample

        Args:
            sample: iterable containing sound samples
            volume: maximum volume for the sample
            attack: attack time, in ms
            release: release time, in ms
        """

        attack_frames = int(self.framerate * attack / 1000)
        release_frames = int(self.framerate * release / 1000)
        sound_frames = len(sample) - attack_frames - release_frames

        if sound_frames < 0:
            raise ValueError(
                'attack ({} ms, {} frames) + release ({} ms, {} frames) time '
                'cannot be longer than sample duration ({} ms, {} frames)'
                .format(attack, attack_frames, release, release_frames,
                        len(sample) / self.framerate * 1000, len(sample)))

        stream = iter(sample)
        for x in range(attack_frames):
            yield int(next(stream) * volume * x / attack_frames)  # FIXME fmt

        for x in range(sound_frames):
            yield int(next(stream) * volume)  # FIXME fmt

        for x in range(release_frames, 0, -1):
            yield int(next(stream) * volume * x / release_frames)  # FIXME fmt

    def generate_silence(self, duration):
        for i in range(int(self.framerate * duration / 1000)):
            yield 0

    def _make_tone(self, tone, duration, volume=.8, attack=20, release=20):
        sample = array('i', self.generate_sine_wave(
            freq=tone, duration=duration))
        wrapped = self.add_envelope(sample, volume=volume, attack=attack,
                                    release=release)
        return array('i', wrapped)

    def generate_morse(self, text, wpm=12, tone=800):
        dot_duration = 1200 / wpm

        dit_sample = self._make_tone(tone, dot_duration)
        dah_sample = self._make_tone(tone, dot_duration * 3)

        for letter in normalize_text(text):
            if letter == ' ':
                # 7dot space, but each character is followed by 3 already
                for x in self.generate_silence(dot_duration * 4):
                    yield x
            else:
                morse = MORSE_TABLE.get(letter)
                if not morse:
                    logger.warning('Unsupported symbol: {}'
                                   .format(repr(letter)))
                    continue

                for sym in morse:
                    if sym is DIT:
                        for x in dit_sample:
                            yield x
                    elif sym is DAH:
                        for x in dah_sample:
                            yield x
                    else:
                        raise ValueError

                    # Character separator
                    for x in self.generate_silence(dot_duration):
                        yield x

                # Letter separator: 3dot, but one was already sent
                for x in self.generate_silence(dot_duration * 2):
                    yield x


def normalize_text(text):
    text = text.lower()
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    return text


@contextmanager
def outstream(filename):
    if not filename or filename == '-':
        yield sys.stdout.buffer
    else:
        with open(filename, 'wb') as fp:
            yield fp


def guess_format_from_filename(filename, default='mp3'):
    if not filename:
        return default
    if '.' in filename:
        ext = filename.rsplit('.', 1)[1]
        if ext:
            return ext
    logger.warning('Unable to guess format from filename. '
                   'Defaulting to {}'.format(default))
    return default


def main():
    parser = argparse.ArgumentParser(
        description='Generate morse code audio files')
    parser.add_argument(
        '--input', '-i', dest='input_file',
        help='Input text file (default: stdin)')
    parser.add_argument(
        '--text', '-t', dest='input_text',
        help='Input text (directly on the command line)')
    parser.add_argument(
        '--speed', '-s', dest='speed', type=int, default=12,
        help='Speed, in words per minute (default: 12)')
    parser.add_argument(
        '--tone', dest='tone', type=int, default=800,
        help='Tone frequency. Defaults to 800 Hz.')
    parser.add_argument(
        '--output', '-o', dest='output_file',
        help='Output file name. Defaults to standard output.')
    parser.add_argument(
        '--format', '-f', dest='output_format', default=None,
        help='Output file format. Can be "pcm", or any format '
        'supported by ffmpeg (see ffmpeg -formats). '
        'Try for example mp3, wav, ogg. '
        'If omitted, will be guessed from file extension.')

    args = parser.parse_args()

    if args.input_text:
        text = args.input_text
    elif args.input_file and (args.input_file != '-'):
        with open(args.input_file, 'r') as fp:
            text = fp.read()
    else:
        text = sys.stdin.read()

    audiogen = AudioGenerator()
    audio_data = audiogen.generate_morse(text, wpm=args.speed, tone=args.tone)

    output_format = args.output_format
    if output_format is None:
        output_format = guess_format_from_filename(args.output_file)

    if output_format == FMT_PCM:
        write_raw_pcm(audio_data, args.output_file)
    else:
        write_audio_file(audio_data, args.output_file, output_format)


def write_raw_pcm(audio_data, filename):
    with outstream(filename) as fp:
        for sample in audio_data:
            fp.write(struct.pack('<h', sample))


def write_audio_file(audio_data, filename, fmt):
    cmd = ['ffmpeg', '-f', 's16le', '-ar', '44.1k', '-ac', '1',
           '-i', '-', '-f', fmt, '-']
    with outstream(filename) as fp:
        p = subprocess.Popen(cmd, stdout=fp, stdin=subprocess.PIPE)
        for sample in audio_data:
            p.stdin.write(struct.pack('<h', sample))
        p.stdin.close()
        p.wait()


if __name__ == '__main__':
    main()
