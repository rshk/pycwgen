import numpy

DEFAULT_SAMPLE_RATE = 44100


def generate_sine_wave(
        frequency, duration,
        volume=1.0,
        attack=0,
        release=0,
        sample_rate=DEFAULT_SAMPLE_RATE):

    """Generate a sine wave.

    Args:
        frequency: frequency, in Hz
        duration: duration, in seconds
        volume: maximum volume
        attack: attack time, in seconds
        release: release time, in seconds
        sample_rate: number of samples per second

    Returns:
        (numpy.array): the generated audio data
    """

    samples = volume * numpy.sin(
        2 * numpy.pi *
        numpy.arange(sample_rate * duration) *
        frequency / sample_rate,
    ).astype(numpy.float32)

    if (attack + release) > duration:
        raise ValueError('Attack + release times cannot be > total time')

    if attack > 0:
        attack_samples_num = int(attack * sample_rate)
        attack_samples = samples[:attack_samples_num]
        other_samples = samples[attack_samples_num:]
        attack_envelope = (numpy.arange(attack_samples_num)
                           / attack_samples_num)
        samples = numpy.concatenate((
            (attack_samples * attack_envelope), other_samples))

    if release > 0:
        release_samples_num = int(release * sample_rate)
        release_samples = samples[-release_samples_num:]
        other_samples = samples[:-release_samples_num]
        release_envelope = (numpy.arange(release_samples_num - 1, -1, -1) /
                            release_samples_num)
        samples = numpy.concatenate((
            other_samples, (release_samples * release_envelope)))

    return samples


def generate_silence(duration, sample_rate=int(DEFAULT_SAMPLE_RATE)):
    return numpy.zeros(int(duration * sample_rate)).astype(numpy.float32)


def generate_noise(duration, sample_rate=int(DEFAULT_SAMPLE_RATE), level=.1):
    return level * (numpy
                    .random.randn(int(duration * sample_rate))
                    .astype(numpy.float32))
