# -*- coding: utf-8 -*-
import platform
import fnmatch
import logging
import os
import re
import time
import math
from datetime import datetime
from multiprocessing import Pool, cpu_count
from threading import Thread

import PIL
import PIL.ExifTags
import wx
from PIL import Image, UnidentifiedImageError

EVT_RESULT_MASTER = 1
EVT_RESULT_NEIGHBORS = 2
EVT_RESULT_PROGRESS = 3
EVT_RESULT_ID = wx.NewId()

MAX_NEIGHBOR_DISPLAY = 10
THUMBNAIL_MAX_SIZE = 224


def find_files_current(which, where='.'):
    """Returns list of filenames from `where` path matched by 'which'
    shell pattern. Matching is case-insensitive.
    see: https://stackoverflow.com/a/47601700"""

    rule = re.compile(fnmatch.translate(which), re.IGNORECASE)
    return [os.path.join(where, name) for name in os.listdir(where) if rule.match(name)]


def find_files_recursive(which, where='.'):
    """Returns list of filenames from `where` path matched by 'which'
    shell pattern. Matching is case-insensitive.
    Method walks all underlying file tree."""

    rule = re.compile(fnmatch.translate(which), re.IGNORECASE)
    matches = []
    for root, dirnames, filenames in os.walk(where):
        for filename in filenames:
            if rule.match(filename):
                matches.append(os.path.join(root, filename))
    return matches


def read_thumb_oriented_exif(jpg):
    """Reads an image from PATH 'jpg'. Can be any PIL compatible image.
    Extracts EXIF information and rotates correspondingly.
    Also creates thumbnail for gallery (crops to square format)
    see: https://stackoverflow.com/a/13893303"""

    # Let's get the orientation
    orientation = 1
    imagedate_original = None
    imagedate = None # in case the image is unreadable
    img_w = 0
    img_h = 0
    img_bytes = None

    # Read Metadata from the image
    try:
        with Image.open(jpg) as img:
            if img.mode != "RGB":
                logging.error("Image mode "+img.mode+"is unsupported at image " + jpg)
                return jpg, None, None, None, None
            if min(img.width , img.height) < THUMBNAIL_MAX_SIZE:
                logging.error("Image too small at image " + jpg)
                return jpg, None, None, None, None
            if img._getexif() is not None:
                exif = {
                    PIL.ExifTags.TAGS[k]: v
                    for k, v in img._getexif().items()
                    if k in PIL.ExifTags.TAGS
                }
                if 'Orientation' in exif:
                    orientation = exif["Orientation"]
                if 'DateTimeOriginal' in exif:
                    imagedate_original = exif["DateTimeOriginal"]
                if 'DateTimeDigitized' in exif:
                    imagedate_digitized = exif["DateTimeDigitized"]

            if imagedate_original is not None:
                try:
                    std_fmt = '%Y:%m:%d %H:%M:%S'
                    imagedate = datetime.strptime(imagedate_original, std_fmt)
                except ValueError as err:
                    logging.debug("EXIF DateTimeOriginal error: {0}".format(err) + " at image " + jpg)
                    try:
                        std_fmt = '%Y:%m:%d %H:%M:%S'
                        imagedate = datetime.strptime(imagedate_digitized, std_fmt)
                    except ValueError as err:
                        logging.debug("EXIF DateTimeDigitized error: {0}".format(err) + " at image " + jpg)
                        imagedate = datetime.fromtimestamp(os.path.getmtime(jpg))
            else:
                imagedate = datetime.fromtimestamp(os.path.getmtime(jpg))

            # crop square format for thumbnail
            if img.width > img.height:
                gap_low = int(math.ceil((img.width - img.height) / 2))
                gap_high = int(math.floor((img.width - img.height) / 2))
                img = img.crop((0 + gap_low, 0, img.width - gap_high, img.height))
            else:
                gap_low= int(math.ceil((img.height - img.width) / 2))
                gap_high = int(math.floor((img.height - img.width) / 2))
                img = img.crop((0, 0 + gap_low, img.width, img.height - gap_high))
            # resize
            size = THUMBNAIL_MAX_SIZE, THUMBNAIL_MAX_SIZE
            img.thumbnail(size, Image.ANTIALIAS)
            # Landscape Left : Do nothing
            if orientation == 1 or orientation == 0:  # ORIENTATION_NORMAL:
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
            else:
                logging.error(
                    "EXIF Orientation tag " + orientation + " unexpected " + " at image " + jpg)
            # prepare return
            img_w = img.width
            img_h = img.height
            img_bytes = img.tobytes()
    except UnidentifiedImageError as err:
        logging.error("UnidentifiedImageError error: {0}".format(err) + " at image " + jpg)
    except OSError as err:
        logging.error("OSError error: {0}".format(err) + " at image " + jpg)

    return jpg, img_bytes, imagedate, img_w, img_h


def read_image_oriented(jpg):
    # Read Metadata from the image
    try:
        raw = Image.open(jpg)
    except UnidentifiedImageError as err:
        logging.error("UnidentifiedImageError error: {0}".format(err) + " at image " + jpg)
        return None

    # Let's get the orientation
    orientation = 1
    if (raw._getexif() is not None):
        exif = {
            PIL.ExifTags.TAGS[k]: v
            for k, v in raw._getexif().items()
            if k in PIL.ExifTags.TAGS
        }
        if 'Orientation' in exif:
            orientation = exif["Orientation"]

    try:
        # Landscape Left : Do nothing
        if orientation == 1 or orientation == 0:  # ORIENTATION_NORMAL:
            img = raw.copy()
            # Portrait Normal : Rotate Right
        elif orientation == 6:  # ORIENTATION_LEFT:
            img = raw.transpose(Image.ROTATE_270)
        # Landscape Right : Rotate Right Twice
        elif orientation == 3:  # ORIENTATION_DOWN:
            img = raw.transpose(Image.ROTATE_180)
        # Portrait Upside Down : Rotate Left
        elif orientation == 8:  # ORIENTATION_RIGHT:
            img = raw.transpose(Image.ROTATE_90)
        else:
            logging.error(
                "EXIF Orientation tag " + orientation + " unexpected " + " at image " + jpg + " --> this may cause problems")
    except OSError as err:
        logging.error("OSError error: {0}".format(err) + " at image " + jpg)
        img = None
    raw.close()
    return img


class LoadImagesWorkerThread(Thread):
    """Worker Thread Class."""

    def __init__(self, notify_window, path, imagedata, recursive=False):
        """Init Worker Thread Class."""
        Thread.__init__(self)

        self._platform = platform.system()
        if self._platform == 'Windows':
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Windows")
            value, value_type = winreg.QueryValueEx(key, "GDIProcessHandleQuota")
            #self._abort_value = max(int(value) - 100, 0)
            self._abort_value = 100000

        self._notify_window = notify_window
        self._path = path
        self._imagedata = imagedata
        self._loadfunc = find_files_current
        if recursive:
            self._loadfunc = find_files_recursive
        self._want_abort = 0
        # This starts the thread running on creation, but you could
        # also make the GUI thread responsible for calling this
        self.start()

    def run(self):
        """Run Worker Thread."""

        starttime = datetime.now()
        self._want_abort = 0
        ################################################
        folder_path = self._path
        img_list = []

        i = 0
        for file in self._loadfunc("*.jpg", folder_path):
            img_list.append(file)
            i = i + 1
            # Avoid to load more images than handles available on Windows
            if self._platform == 'Windows':
                if i >= self._abort_value:
                    logging.warn("Loading only " + str(
                        i) + " images due to limited handles on Windows. --> Increase HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Windows\\GDIProcessHandleQuota")
                    break
        img_list.sort()
        # read files separately using multithreaded pool
        pool = Pool(cpu_count())
        load_results = pool.map_async(read_thumb_oriented_exif, img_list)
        pool.close()  # 'TERM'
        # maintain status gauge here
        while True:
            if load_results.ready() or self._want_abort == 1: break
            time.sleep(0.3)
            remaining = min(load_results._number_left * load_results._chunksize, len(img_list))
            # print("Waiting for", remaining, "tasks to complete...")
            wx.PostEvent(self._notify_window,
                         ResultEvent((len(img_list) - remaining) / len(img_list), EVT_RESULT_PROGRESS))
        if self._want_abort == 1:
            pool.terminate()
        pool.join()  # 'KILL'
        #
        wx.PostEvent(self._notify_window, ResultEvent(0.99, EVT_RESULT_PROGRESS))
        self._imagedata.clear()
        for item in load_results.get():
            filename, thumb, imagedate, width, height = item
            if thumb is not None:
                # width, height = thumb.size
                # try:
                #     wxbitmap = wx.Bitmap.FromBuffer(THUMBNAIL_MAX_SIZE, THUMBNAIL_MAX_SIZE, thumb)
                # except ValueError as err:
                #     logging.warn("ValueError error: {0}".format(err) + " at image " + filename)
                #     continue
                # except RuntimeError as err:
                #     logging.warn(
                #         "RuntimeError error: {0}".format(err) + " at image " + filename + "(insufficient memory?)")
                #     continue
                self._imagedata.addThumbnail(filename, thumb)
                self._imagedata.addDateTime(filename, imagedate)
            else:
                logging.warn("File damaged..cannot load JPEG " + filename)
        wx.PostEvent(self._notify_window, ResultEvent("", EVT_RESULT_MASTER))
        wx.PostEvent(self._notify_window, ResultEvent(None, EVT_RESULT_MASTER))
        wx.PostEvent(self._notify_window, ResultEvent(0.0, EVT_RESULT_PROGRESS))

        stoptime = datetime.now()
        logging.error(
            "LoadImagesWorkerThread took " + str(stoptime-starttime) + " to load " + str(self._imagedata.getSize())+ " image files")

    def abort(self):
        """abort worker thread."""
        # Method for use by main thread to signal an abort
        self._want_abort = 1


class ResultEvent(wx.PyEvent):
    """Simple event to carry arbitrary result data."""

    def __init__(self, data, result_type):
        """Init Result Event."""
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_RESULT_ID)
        self.data = data
        self.type = result_type


class ImageData():
    """Data structure to carry all data of the images
    └── imagedict
        └── path[n]
            ├── featuresannoy
            ├── image
            ├── thumbnail
            └── datetime
    └── datetimedict
        └── datetime[n]
            └── path
    """

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
