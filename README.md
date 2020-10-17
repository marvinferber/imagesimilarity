# Image Similarity Viewer

## Features 

This program is intended to find and view images that are "similar".
It offers:
* an image gallery view based on image record dates (like a calendar)
* a similarity viewer showing the 10 most similar images based on ML and nearest neighbor approximation
* (not yet implemented) a similarity viewer showing the 10 most similar images based on the Haar wavelet-based perceptual similarity index (HaarPSI)
* (not yet implemented) a similarity viewer showing the 10 most similar images based on AKAZE local image features

## Download

The latest release binaries can be found [here](https://github.com/marvinferber/imagesimilarity/releases). 
Windows and Linux binaries are available. 

MacOS is not supported, yet. Feel free to contribute. 

## Develop

Stable releases can be found in the master branch. The current state of development is in the develop branch. 
Check out the development branch 

`git clone -b develop https://github.com/marvinferber/imagesimilarity` 

`cd imagesimilarity`

Create a Python3 venv 

`mkdir venv` 

`python -m venv venv` 

and activate it. 

Linux: `source venv/bin/activate` 

Windows CMD:`venv\Scripts\activate.bat`

`cd src`

Since Annoy (Approximate Nearest Neighbors Oh Yeah) needs C++14 support to compile on Windows, 
it is necessary to install [Visual Studio Build Tools 2019](https://visualstudio.microsoft.com/downloads/) 
on Windows at first.
Install Python package dependencies, first general dependencies:
* `pip install --upgrade pip` (pip version 19 or higher)
* `pip install wheel`

Program dependencies:
* `pip install .` (reads setup.py dependencies)

Run the program:
* `python guimain.py`


## Release/Install

Pyinstaller can be used to create a distributable package both on Windows and Linux. 
However, the latest pyinstaller devel is necessary to handle TensorFlow dependencies correctly. 
Pyinstaller devel will be installed as described above using pip and setup.py for this purpose. 
Just type `pyinstaller src/guimain.py` to create the distributable package. 
It will be located in a dist folder.

On Windows, it is necessary to have 
[Microsoft Visual C++ 2019 Redistributable](https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads) components installed 
in order to run the distributable binary package.
