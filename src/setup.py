from setuptools import setup

setup(
    name='imagesimilarity',
    version='0.1',
    packages=[''],
    url='https://github.com/marvinferber/imagesimilarity',
    license='Apache License 2.0',
    author='ferber',
    author_email='ferbhome@freenet.de',
    description='Find and display images that are similar.',
    install_requires=[
        'wxPython>=4',
        'Pillow>=7',
        'tensorflow==2.0.2',
        'tensorflow_hub',
        'annoy @ https://download.lfd.uci.edu/pythonlibs/w3jqiv8s/annoy-1.16.3-cp37-cp37m-win_amd64.whl',
		'pywin32',
		'setuptools<45',
		'pyinstaller'
    ]
)
