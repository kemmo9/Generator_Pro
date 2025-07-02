#!/usr/bin/env bash
# exit on error
set -o errexit

# This line tells Render's build server to install the ImageMagick software
apt-get update && apt-get install -y imagemagick

# This line installs all your Python packages from requirements.txt
pip install -r requirements.txt
