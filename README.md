# Image Similarity Viewer

## Features 

This program is intended to find and view images that are "similar".
It offers:
* an image gallery view based on image record dates (like a calendar)
* a similarity viewer showing the 10 most similar images based on ML and nearest neighbor approximation
* (not yet implemented) a similarity viewer showing the 10 most similar images based on the Haar wavelet-based perceptual similarity index (HaarPSI)
* (not yet implemented) a similarity viewer showing the 10 most similar images based on AKAZE local image features

## Download

The latest release binaries can be found [here](https://github.com/marvinferber/imagesimilarity/releases). Windows and Linux binaries are available. On Windows, the maximum number of images is restricted to 1000 images. MacOS is not supported. 

## Develop

Stable releases can be found in the master branch. The current state of development is in the develop branch. 
Check out th development branch 

`git clone -b develop https://github.com/marvinferber/imagesimilarity` 

`cd imagesimilarity`

Create a Python3 venv 

`mkdir venv` 

`python -m venv venv` 

and activate it. 

Linux: `source venv/bin/activate` 

Windows CMD:`venv\Scripts\activate.bat`

`cd src`

Install dependencies, first general dependecies:
* `pip install --upgrade pip` (pip version 19 or higher)
* `pip install wheel`

Program dependecies:
* `pip install .` (reads setup.py dependencies)

Run the program:
* `python guimain.py`

Since annoy cannot be installed via pip on Windows, there is a fixed whl package for Python 3.7 included in setup.py.

## Release/Install

Pyinstaller can be used to create a distributable package both on Windows and Linux. However, the latest pyinstaller devel is necessary to handle TensorFlow dependencies correctly. Pyinstaller devel will be installed as described above using pip and setup.py for this purpose. Just type `pyinstaller src/guimain.py` to create the distributable package. It will be located in a dist folder.
