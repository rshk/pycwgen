#!/bin/bash
rm -rf dist/*
python setup.py sdist bdist_wheel
# gpg --detach-sign -a dist/*.tar.gz
twine upload dist/*
rm -rf build dist .egg *.egg-info
