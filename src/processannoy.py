# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from threading import Thread

import numpy as np
import tensorflow as tf
import wx
from annoy import AnnoyIndex
from process import ResultEvent, EVT_RESULT_NEIGHBORS, EVT_RESULT_PROGRESS


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
        # Configuring annoy parameters
        dims = 1792
        n_nearest_neighbors = 10
        trees = 10000
        t = AnnoyIndex(dims, metric='angular')
        # Definition of module with using tfhub.dev handle
        logging.error("Start loading mobilenet...")
        module_handle = "https://tfhub.dev/google/imagenet/mobilenet_v2_140_224/feature_vector/4"
        # module_handle = "4/"
        # Load the module
        import tensorflow_hub as hub
        module = hub.load(module_handle)
        starttime = datetime.now()
        logging.error("Start processing and adding images to AnnoyIndex...")
        for file_index, item in enumerate(list(self._imagedata.getKeys())):
            # Loads and pre-process the image
            btmp = self._imagedata.getThumbnail(item)
            # pil_img = wx2PIL(wx_img)
            image_array = np.fromstring(bytes(btmp.ConvertToImage().GetData()), dtype=np.uint8).reshape(
                (btmp.GetWidth(), btmp.GetHeight(), 3))
            # image_array = tf.keras.preprocessing.image.img_to_array(pil_img)
            image_array = tf.convert_to_tensor(image_array)
            tf_image_array = tf.image.convert_image_dtype(image_array, tf.float32)[tf.newaxis, ...]
            # Calculate the image feature vector of the img
            try:
                features = module(tf_image_array)
            except ValueError as err:
                logging.error("Image too small for feature processing " + item)
                continue
            # Remove single-dimensional entries from the 'features' array
            feature_set = np.squeeze(features)
            # Adds image feature vectors into annoy index
            t.add_item(file_index, feature_set)
            # self._imagedata.addFeatureSetAnnoy(filename,feature_set)
            wx.PostEvent(self._notify_window,
                         ResultEvent((file_index / self._imagedata.getSize()) * 0.5, EVT_RESULT_PROGRESS))
        # Builds annoy index
        logging.error("Building trees...")
        t.build(trees)
        wx.PostEvent(self._notify_window, ResultEvent(0.75, EVT_RESULT_PROGRESS))
        # Loops through all indexed items
        returndata = []
        logging.error("Fetching nearest neighbors...")
        for file_index, filename in enumerate(list(self._imagedata.getKeys())):
            # Calculates the nearest neighbors of the master item
            nearest_neighbors = t.get_nns_by_item(file_index, n_nearest_neighbors)
            thumb_nearest_neighbors = []
            for j in nearest_neighbors:
                neighbor_name = list(self._imagedata.getKeys())[j]
                neighbor_thumb = self._imagedata.getThumbnail(neighbor_name)
                thumb_nearest_neighbors.append(neighbor_name)
            returndata.append(thumb_nearest_neighbors)
            wx.PostEvent(self._notify_window,
                         ResultEvent((file_index / self._imagedata.getSize()) * 0.25 + 0.75, EVT_RESULT_PROGRESS))
        wx.PostEvent(self._notify_window, ResultEvent(returndata, EVT_RESULT_NEIGHBORS))
        wx.PostEvent(self._notify_window, ResultEvent(None, EVT_RESULT_NEIGHBORS))
        wx.PostEvent(self._notify_window, ResultEvent(0.0, EVT_RESULT_PROGRESS))
        stoptime = datetime.now()
        logging.error(
            "ProcessAnnoyWorkerThread took " + str(stoptime - starttime) + " to process " + str(
                len(returndata)) + " image files")
