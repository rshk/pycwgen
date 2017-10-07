#!/bin/bash
rm -rf dist/*
python setup.py sdist
# gpg --detach-sign -a dist/*.tar.gz
twine upload dist/*
