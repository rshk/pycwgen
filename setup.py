from setuptools import setup, find_packages

version = '0.1'

longdesc = """\
PyCWgen
#######

Generate Morse Code (CW) audio files in Python.

Repository and documentation: https://github.com/rshk/pycwgen
"""


setup(
    name='pycwgen',
    version=version,
    packages=find_packages(),
    url='https://github.com/rshk/pycwgen',
    license='BSD License',
    author='Samuele Santi',
    author_email='samuele@samuelesanti.com',
    description='Generate Morse Code (CW) audio files in Python',
    long_description=longdesc,
    install_requires=[
        'PySoundFile',
        'numpy',
        'click',
    ],
    classifiers=[
        'License :: OSI Approved :: BSD License',
        # 'Programming Language :: Python :: 3',
        # 'Programming Language :: Python :: 3.0',
        # 'Programming Language :: Python :: 3.1',
        # 'Programming Language :: Python :: 3.2',
        # 'Programming Language :: Python :: 3.3',
        # 'Programming Language :: Python :: 3.4',
        # 'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        # 'Programming Language :: Python :: 3 :: Only',

        # 'Programming Language :: Python :: Implementation :: CPython',
        # 'Programming Language :: Python :: Implementation :: IronPython',
        # 'Programming Language :: Python :: Implementation :: Jython',
        # 'Programming Language :: Python :: Implementation :: PyPy',
        # 'Programming Language :: Python :: Implementation :: Stackless',
    ],
    entry_points={
        'console_scripts': ['pycwgen=pycwgen.cli:cli'],
    },
    package_data={'': ['README.md']},
    include_package_data=True,
    zip_safe=False)
