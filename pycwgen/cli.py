import click

import soundfile

from .morse import stream_morse_code


@click.command()
@click.option('--input', '-i', 'input_file',
              type=click.File('rt'), default='-',
              help='Input text file (defaults to stdin)')
@click.option('--text', '-t', 'input_text',
              help='Input text. Overrides --input.')
@click.option('--speed', '-s', type=int, default=12,
              help='Speed, in words per minute (default: 12)')
@click.option('--tone', type=int, default=600,
              help='Tone frequency, in Hz (default: 600)')
@click.option('--output', '-o', 'output_file',
              type=click.Path(), help='Name of the output file')
@click.option('--format', '-f', 'output_format',
              help='Output format. Use --list-formats to see '
              'the available formats')
@click.option('--subtype', 'output_subtype',
              help='Output format sub-type')
@click.option('--list-formats', is_flag=True, default=False,
              help='List the available formats and exit')
@click.option('--list-subtypes',
              help='List the available sub-types for the specified '
              'format and exit')
def cli(input_file, input_text, speed, tone, output_file, output_format,
        output_subtype, list_formats, list_subtypes):

    if list_formats:
        for key, value in soundfile.available_formats().items():
            click.echo('\x1b[1m{:<10}\x1b[0m {}'.format(key, value))
        return

    if list_subtypes:
        for key, value in soundfile.available_subtypes(list_subtypes).items():
            click.echo('\x1b[1m{:<10}\x1b[0m {}'.format(key, value))
        return

    if not input_text:
        input_text = input_file.read()

    options = dict(
        samplerate=44100,
        channels=1,
        subtype=output_subtype,
        format=output_format)

    with soundfile.SoundFile(output_file, 'w', **options) as fp:
        stream_morse_code(fp, input_text, wpm=speed, tone=tone)


cli()
