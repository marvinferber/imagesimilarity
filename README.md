# Image Similarity Viewer

## Features 

This program is intended to find and view images that are "similar".
It offers:
* an image gallery view based on image record dates (like a calendar)
* a similarity viewer showing the 10 most similar images based on ML and nearest neighbor approximation
* a similarity viewer showing the 10 most similar images based on the Haar wavelet-based perceptual similarity index (HaarPSI)
* a similarity viewer showing the 10 most similar images based on AKAZE local image features

## Download

The latest release binaries can be found here. Windows and Linux binaries are available. On Windows, the maximum number of images is restricted to 1000 images. MacOS is not supported. 

## Develop

Stable releases can be found in the master branch. The current state of development is in the develop branch. 
Check out th development branch `git clone -b develop https://github.com/marvinferber/imagesimilarity` 
`cd imagesimilarity`
Create a Python3 venv `mkdir venv` `python -m venv venv` and activate it. Linux: `source venv/bin/activate` Windows CMD:`venv\Scripts\activate.bat`
`cd src`
Install dependencies, first general dependecies:
* `pip install --upgrade pip` (pip version 19 or higher)
* `pip install wheel`

Program dependecies:
* `pip install .` (reads setup.py dependencies)
Run the program:
* `python guimain.py`

Since annoy cannot be installed via pip on Windows, there is a fixed whl package for Python 3.7 included in setup.py.
