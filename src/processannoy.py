# -*- coding: utf-8 -*-
from threading import Thread
from annoy import AnnoyIndex
import tensorflow_hub as hub
import tensorflow as tf
import numpy as np
import wx
from process import ResultEvent, EVT_RESULT_NEIGHBORS


def load_img(path):
    # Reads the image file and returns data type of string
    img = tf.io.read_file(path)
    # Decodes the image to W x H x 3 shape tensor with type of uint8
    try:
        img = tf.io.decode_jpeg(img, channels=3)
    except:
        return None
    # Resize the image to 224 x 244 x 3 shape tensor
    img = tf.image.resize_with_pad(img, 224, 224)
    # Converts the data type of uint8 to float32 by adding a new axis
    # This makes the img 1 x 224 x 224 x 3 tensor with the data type of float32
    # This is required for the mobilenet model we are using
    img = tf.image.convert_image_dtype(img, tf.float32)[tf.newaxis, ...]
    return img


class ProcessAnnoyWorkerThread(Thread):
    """Worker Thread Class."""

    def __init__(self, notify_window, imagedata):
        """Init Worker Thread Class."""
        Thread.__init__(self)

        self._notify_window = notify_window
        self._imagedata = imagedata
        self._want_abort = 0
        # This starts the thread running on creation, but you could
        # also make the GUI thread responsible for calling this
        self.start()

    def run(self):
        """Run Worker Thread."""
        # Definition of module with using tfhub.dev handle
        module_handle = "https://tfhub.dev/google/imagenet/mobilenet_v2_140_224/feature_vector/4"
        #module_handle = "4/"
        # Load the module
        module = hub.load(module_handle)
        # Configuring annoy parameters
        dims = 1792
        n_nearest_neighbors = 10
        trees = 10000
        t = AnnoyIndex(dims, metric='angular')
        for file_index, filename in enumerate(list(self._imagedata.getKeys())):
            # Loads and pre-process the image
            img = load_img(filename)
            if img is None:
                print("JPEG Image cannot be loaded...", filename)
                continue
            # Calculate the image feature vector of the img
            features = module(img)
            # Remove single-dimensional entries from the 'features' array
            feature_set = np.squeeze(features)
            # Adds image feature vectors into annoy index
            t.add_item(file_index, feature_set)
            # self._imagedata.addFeatureSetAnnoy(filename,feature_set)
        # Builds annoy index
        t.build(trees)
        # Loops through all indexed items
        returndata = []
        for file_index, filename in enumerate(list(self._imagedata.getKeys())):
            # Calculates the nearest neighbors of the master item
            nearest_neighbors = t.get_nns_by_item(file_index, n_nearest_neighbors)
            thumb_nearest_neighbors = []
            for j in nearest_neighbors:
                neighbor_name = list(self._imagedata.getKeys())[j]
                neighbor_thumb = self._imagedata.getThumbnail(neighbor_name)
                thumb_nearest_neighbors.append(neighbor_thumb)
            returndata.append(thumb_nearest_neighbors)
        wx.PostEvent(self._notify_window, ResultEvent(returndata, EVT_RESULT_NEIGHBORS))
        wx.PostEvent(self._notify_window, ResultEvent(None, EVT_RESULT_NEIGHBORS))
