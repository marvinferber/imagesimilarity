import fnmatch
import os
import re
import time
from datetime import datetime
from multiprocessing import Pool, cpu_count
from threading import Thread
import logging

import wx
from PIL import Image, UnidentifiedImageError
from pyexiv2 import Image as ExifData
import pyexiv2

EVT_RESULT_MASTER = 1
EVT_RESULT_NEIGHBORS = 2
EVT_RESULT_PROGRESS = 3
EVT_RESULT_ID = wx.NewId()

MAX_NEIGHBOR_DISPLAY = 10
THUMBNAIL_MAX_SIZE = 240

pyexiv2.core.set_log_level(4)


def findfilescurrent(which, where='.'):
    '''Returns list of filenames from `where` path matched by 'which'
       shell pattern. Matching is case-insensitive.'''

    rule = re.compile(fnmatch.translate(which), re.IGNORECASE)
    return [os.path.join(where, name) for name in os.listdir(where) if rule.match(name)]


def findfilesrecursive(which, where='.'):
    rule = re.compile(fnmatch.translate(which), re.IGNORECASE)
    matches = []
    for root, dirnames, filenames in os.walk(where):
        for filename in filenames:
            if rule.match(filename):
                matches.append(os.path.join(root, filename))
    return matches


def read_thumb_oriented_exif(jpg):
    # Read Metadata from the image
    try:
        exif = ExifData(jpg)
        metadata = exif.read_exif()
    except RuntimeError as err:
        logging.error("EXIF error: {0}".format(err) + " at image " + jpg)
        metadata = {}
    except UnicodeDecodeError as err:
        logging.error("EXIF error: {0}".format(err) + " at image " + jpg)
        metadata = {}
    # Let's get the orientation
    orientation = 1
    imagedate = None
    try:
        orientation = int(metadata.__getitem__("Exif.Image.Orientation"))
        imagedate = metadata.__getitem__("Exif.Image.DateTime")
    except KeyError as err:
        logging.error("EXIF error: {0}".format(err) + " at image " + jpg)

    if imagedate is not None:
        std_fmt = '%Y:%m:%d %H:%M:%S'
        try:
            imagedate = datetime.strptime(imagedate, std_fmt)
        except ValueError as err:
            logging.error("DateTime error: {0}".format(err) + " at image " + jpg)
            imagedate = datetime.fromtimestamp(os.path.getmtime(jpg))
    else:
        imagedate = datetime.fromtimestamp(os.path.getmtime(jpg))
    try:
        img = Image.open(jpg)
    except UnidentifiedImageError as err:
        logging.error("PIL error: {0}".format(err) + " at image " + jpg)
        return jpg, None, imagedate
    # Landscape Left : Do nothing
    if orientation == 1:  # ORIENTATION_NORMAL:
        pass
        # Portrait Normal : Rotate Right
    elif orientation == 6:  # ORIENTATION_LEFT:
        img = img.transpose(Image.ROTATE_270)
    # Landscape Right : Rotate Right Twice
    elif orientation == 3:  # ORIENTATION_DOWN:
        img = img.transpose(Image.ROTATE_180)
    # Portrait Upside Down : Rotate Left
    elif orientation == 8:  # ORIENTATION_RIGHT:
        img = img.transpose(Image.ROTATE_90)

    try:
        # crop quadrat
        if img.width > img.height:
            gap = int((img.width - img.height) / 2)
            img = img.crop((0 + gap, 0, img.width - gap, img.height))
        else:
            gap = int((img.height - img.width) / 2)
            img = img.crop((0, 0 + gap, img.width, img.height - gap))
        # resize
        size = THUMBNAIL_MAX_SIZE, THUMBNAIL_MAX_SIZE
        img.thumbnail(size, Image.ANTIALIAS)
    except OSError as err:
        logging.error("OSError error: {0}".format(err) + " at image " + jpg)
        img = None
    return jpg, img, imagedate


def read_image_oriented(jpg):
    # Read Metadata from the image
    exif = ExifData(jpg)
    metadata = exif.read_exif()
    # Let's get the orientation
    orientation = 1
    try:
        orientation = int(metadata.__getitem__("Exif.Image.Orientation"))
    except KeyError as err:
        logging.error("EXIF error: {0}".format(err) + " at image " + jpg)
    img = Image.open(jpg)
    # Landscape Left : Do nothing
    if orientation == 1:  # ORIENTATION_NORMAL:
        pass
        # Portrait Normal : Rotate Right
    elif orientation == 6:  # ORIENTATION_LEFT:
        img = img.transpose(Image.ROTATE_270)
    # Landscape Right : Rotate Right Twice
    elif orientation == 3:  # ORIENTATION_DOWN:
        img = img.transpose(Image.ROTATE_180)
    # Portrait Upside Down : Rotate Left
    elif orientation == 8:  # ORIENTATION_RIGHT:
        img = img.transpose(Image.ROTATE_90)
    return img


class LoadImagesWorkerThread(Thread):
    """Worker Thread Class."""

    def __init__(self, notify_window, path, imagedata, recursive=False):
        """Init Worker Thread Class."""
        Thread.__init__(self)

        self._notify_window = notify_window
        self._path = path
        self._imagedata = imagedata
        self._loadfunc = findfilescurrent
        if (recursive):
            self._loadfunc = findfilesrecursive
        self._want_abort = 0
        # This starts the thread running on creation, but you could
        # also make the GUI thread responsible for calling this
        self.start()

    def run(self):
        """Run Worker Thread."""

        # if self._want_abort:
        # img___jpg = "/home/ferber/PycharmProjectocv_feature/test/IMG_8802.JPG"
        # img = self.read_image_oriented(img___jpg)

        # wx.PostEvent(self._notify_window, ResultEvent(img))
        self._imagedata.clear()
        ################################################
        folder_path = self._path
        img_list = []
        for file in self._loadfunc("*.jpg", folder_path):
            img_list.append(file)
        img_list.sort()
        #
        pool = Pool(cpu_count())
        load_results = pool.map_async(read_thumb_oriented_exif, img_list)
        pool.close()  # 'TERM'
        # maintain status gauge here
        while (True):
            if (load_results.ready()): break
            time.sleep(0.3)
            remaining = load_results._number_left
            # print("Waiting for", remaining, "tasks to complete...")
            wx.PostEvent(self._notify_window,
                         ResultEvent((len(img_list) - remaining) / len(img_list), EVT_RESULT_PROGRESS))
        pool.join()  # 'KILL'
        #
        for item in load_results.get():
            filename, thumb, imagedate = item
            if thumb is not None:
                width, height = thumb.size
                try:
                    wxbitmap = wx.Bitmap.FromBuffer(width, height, thumb.tobytes())
                except ValueError as err:
                    logging.error("ValueError error: {0}".format(err) + " at image " + filename)
                    continue
                self._imagedata.addThumbnail(filename, wxbitmap)
                self._imagedata.addDateTime(filename, imagedate)
            else:
                logging.warn("File damaged..cannot load JPEG ", filename)
        wx.PostEvent(self._notify_window, ResultEvent("", EVT_RESULT_MASTER))
        wx.PostEvent(self._notify_window, ResultEvent(None, EVT_RESULT_MASTER))

    def abort(self):
        """abort worker thread."""
        # Method for use by main thread to signal an abort
        self._want_abort = 1


class ResultEvent(wx.PyEvent):
    """Simple event to carry arbitrary result data."""

    def __init__(self, data, type):
        """Init Result Event."""
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_RESULT_ID)
        self.data = data
        self.type = type



class ImageData():
    """Data structure to carry all data of the images"""

    def __init__(self):
        self.imagedict = {}
        self.datetimedict = {}
        self.sortedkeys = None

    def addFeatureSetAnnoy(self, key, featureset):
        if not key in self.imagedict.keys():
            self.imagedict[key] = {}
        self.imagedict[key]["featuresetannoy"] = featureset

    def addImage(self, key, imageobject):
        if not key in self.imagedict.keys():
            self.imagedict[key] = {}
        self.imagedict[key]["image"] = imageobject

    def addThumbnail(self, key, imageobject):
        if not key in self.imagedict.keys():
            self.imagedict[key] = {}
        self.imagedict[key]["thumbnail"] = imageobject

    def addDateTime(self, key, imagedate):
        self.datetimedict[imagedate] = key
        self.sortedkeys = None
        if not key in self.imagedict.keys():
            self.imagedict[key] = {}
        self.imagedict[key]["datetime"] = imagedate

    def getYearMonth(self, key):
        imagedate: datetime = self.imagedict[key]["datetime"]
        return imagedate.year, imagedate.month

    def getSize(self):
        return len(self.imagedict)

    def getKeys(self):
        return self.imagedict.keys()

    def getKeysSortedByTime(self):
        if self.sortedkeys is None:
            self.sortedkeys = [self.datetimedict[imagedate] for imagedate in sorted(self.datetimedict.keys())]
        return self.sortedkeys

    def getThumbnail(self, key):
        return self.imagedict[key]["thumbnail"]

    def clear(self):
        self.imagedict = {}
        self.datetimedict = {}
