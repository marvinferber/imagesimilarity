from setuptools import setup
import platform

if platform.system() == 'Windows':
    setup(
        name='imagesimilarity',
        version='0.1',
        packages=[''],
        url='https://github.com/marvinferber/imagesimilarity',
        license='Apache License 2.0',
        author='Marvin Ferber',
        author_email='ferbhome@freenet.de',
        description='Find and display images that are similar.',
        install_requires=[
            'wxPython>=4',
            'Pillow>=7',
            'tensorflow==2.0.2',
            'tensorflow_hub',
            'annoy @ https://download.lfd.uci.edu/pythonlibs/x2tqcw5k/annoy-1.17.0-cp37-cp37m-win_amd64.whl',
		    'pywin32',
		    'setuptools==44',
		    'pyinstaller @ https://github.com/pyinstaller/pyinstaller/archive/develop.tar.gz'
        ]
    )
else:
    setup(
        name='imagesimilarity',
        version='0.1',
        packages=[''],
        url='https://github.com/marvinferber/imagesimilarity',
        license='Apache License 2.0',
        author='Marvin Ferber',
        author_email='ferbhome@freenet.de',
        description='Find and display images that are similar.',
        install_requires=[
            'wxPython>=4',
            'Pillow>=7',
            'tensorflow==2.0.2',
            'tensorflow_hub',
            'annoy>=1.17',
		    'setuptools==44',
		    'pyinstaller @ https://github.com/pyinstaller/pyinstaller/archive/develop.tar.gz'
        ]
    )
