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


class AudioGenerator:

    def __init__(self, framerate=DEFAULT_FRAMERATE, samplefmt='s16le'):
        self.framerate = framerate
        if samplefmt not in SAMPLE_FORMATS:
            raise ValueError('Invalid sample format: {}. Supported are: {}.'
                             .format(samplefmt, ', '.join(SAMPLE_FORMATS)))
        self.samplefmt = samplefmt

    def generate_sine_wave(self, freq=440, duration=1000,
                           volume=.9, attack=0, release=0):
        """Generate a sine wave.

        Args:
            freq: frequency, in Hz
            duration: sample duration, in ms
            volume: maximum amplitude for the sample (0-1)
            attack: attack time, in ms
            release: release time, in ms
        """

        assert self.samplefmt == 's16le'
        max_value = 32767

        frames_count = int(self.framerate * duration / 1000)
        sine_wave = self._make_sine_wave(freq=freq, frames=frames_count)
        envelope = self._make_envelope(
            volume=volume, frames_count=frames_count,
            attack_frames=int(attack * self.framerate / 1000),
            release_frames=int(release * self.framerate / 1000))

        for sample, env in zip(sine_wave, envelope):
            yield int(sample * env * max_value)

    def _make_sine_wave(self, freq, frames):
        for i in range(frames):
            yield math.sin(2.0 * math.pi * freq * i / self.framerate)

    def _make_envelope(self, volume, frames_count, attack_frames,
                       release_frames):

        sound_frames = frames_count - attack_frames - release_frames

        if sound_frames < 0:
            attack_time = attack_frames / self.framerate * 1000
            release_time = release_frames / self.framerate * 1000
            audio_time = frames_count / self.framerate * 1000
            raise ValueError(
                'attack ({} ms, {} frames) + release ({} ms, {} frames) time '
                'cannot be longer than sample duration ({} ms, {} frames)'
                .format(attack_time, attack_frames,
                        release_time, release_frames,
                        audio_time, frames_count))

        for x in range(attack_frames):
            yield (volume * x / attack_frames)  # FIXME sine?

        for x in range(sound_frames):
            yield (volume)  # FIXME fmt

        for x in range(release_frames, 0, -1):
            yield (volume * x / release_frames)  # FIXME sine?

    # def generate_silence(self, duration):
    #     for i in range(int(self.framerate * duration / 1000)):
    #         yield 0

    def _make_tone(self, tone, duration, volume=.8, attack=20, release=20):
        sample_gen = self.generate_sine_wave(
            freq=tone, duration=duration, volume=volume, attack=attack,
            release=release)
        audio_data = array('i', sample_gen)
        enc_data = struct.pack('<' + ('h' * len(audio_data)), *audio_data)
        return enc_data

    def _make_silence(self, duration):
        frames = int(self.framerate * duration / 1000)
        return struct.pack('<h', 0) * frames

    def generate_morse(self, text, wpm=12, tone=800):
        dot_duration = 1200 / wpm

        samples = {
            DIT: self._make_tone(tone, dot_duration),
            DAH: self._make_tone(tone, dot_duration * 3),
        }

        silence_1x = self._make_silence(dot_duration)
        silence_2x = self._make_silence(dot_duration * 2)
        silence_4x = self._make_silence(dot_duration * 4)

        for letter in normalize_text(text):
            if letter == ' ':
                # 7dot space, but each character is followed by 3 already
                yield silence_4x
            else:
                morse = MORSE_TABLE.get(letter)
                if not morse:
                    logger.warning('Unsupported symbol: {}'
                                   .format(repr(letter)))
                    continue

                for sym in morse:
                    yield samples[sym]
                    yield silence_1x  # Character separator

                yield silence_2x  # Letter separator: 3dot (one already sent)


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
        for chunk in audio_data:
            fp.write(chunk)


def write_audio_file(audio_data, filename, fmt):
    with outstream(filename) as fp:
        encode_audio(b''.join(audio_data), fp, fmt)


def encode_audio(audio_data, fp, fmt):
    cmd = ['ffmpeg',
#           '-loglevel', 'error',
           '-f', 's16le',
           '-ar', '44.1k', '-ac', '1',
           '-i', '-',
           '-f', fmt,
           '-']
    p = subprocess.Popen(cmd, stdout=fp, stdin=subprocess.PIPE)
    p.stdin.write(audio_data)
    # for sample in audio_data:
    #     p.stdin.write(struct.pack('<h', sample))
    p.stdin.close()
    p.wait()


if __name__ == '__main__':
    main()
