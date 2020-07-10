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
        'Pillow>=7'
    ]
)
