# -*- coding: utf-8 -*-
import logging
import time
import math
from datetime import datetime
from threading import Thread
from multiprocessing import Pool, cpu_count

import numpy as np
import tensorflow as tf
import wx
from annoy import AnnoyIndex
from process import ResultEvent, EVT_RESULT_NEIGHBORS, EVT_RESULT_PROGRESS, THUMBNAIL_MAX_SIZE

from functools import partial

DIMS = 1792
n_nearest_neighbors = 10


def get_nns(annoyindex_tempfile, img_list):
    # Calculates the nearest neighbors of the master item
    t = AnnoyIndex(DIMS, metric='angular')
    t.load(annoyindex_tempfile)
    list_of_thumb_nearest_neighbors = []
    for item in img_list:
        nearest_neighbors = t.get_nns_by_item(item, n_nearest_neighbors)
        thumb_nearest_neighbors = []
        for j in nearest_neighbors:
            thumb_nearest_neighbors.append(j)
        list_of_thumb_nearest_neighbors.append(thumb_nearest_neighbors)
    return list_of_thumb_nearest_neighbors


class ProcessAnnoyWorkerThread(Thread):
    """Worker Thread Class."""

    def __init__(self, notify_window, imagedata):
        """Init Worker Thread Class."""
        Thread.__init__(self)

        # Configuring annoy parameters

        self._n_nearest_neighbors = 10
        self._trees = 10000
        self._t = AnnoyIndex(DIMS, metric='angular')

        self._notify_window = notify_window
        self._imagedata = imagedata
        self._want_abort = 0
        # This starts the thread running on creation, but you could
        # also make the GUI thread responsible for calling this
        self.start()

    def run(self):
        """Run Worker Thread."""
        # Definition of module with using tfhub.dev handle
        logging.error("Start loading mobilenet...")
        module_handle = "https://tfhub.dev/google/imagenet/mobilenet_v2_140_224/feature_vector/4"
        # module_handle = "4/"
        # Load the module
        import tensorflow_hub as hub
        module = hub.load(module_handle)
        starttime = datetime.now()
        ################################################
        logging.error("Start processing and adding images to AnnoyIndex...")
        for file_index, item in enumerate(list(self._imagedata.getKeys())):
            # Loads and pre-process the image
            btmp = self._imagedata.getThumbnail(item)
            # pil_img = wx2PIL(wx_img)
            image_array = np.fromstring(bytes(btmp), dtype=np.uint8).reshape(
                (THUMBNAIL_MAX_SIZE, THUMBNAIL_MAX_SIZE, 3))
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
            self._t.add_item(file_index, feature_set)
            # self._imagedata.addFeatureSetAnnoy(filename,feature_set)
            wx.PostEvent(self._notify_window,
                         ResultEvent((file_index / self._imagedata.getSize()) * 0.5, EVT_RESULT_PROGRESS))
        # Builds annoy index
        logging.error("Building trees...")
        self._t.build(self._trees,n_jobs=-1)
        # save annoy index to file for multiprocessing
        self._t.save(self._imagedata.getAnnoyIndexTempFile())
        wx.PostEvent(self._notify_window, ResultEvent(0.75, EVT_RESULT_PROGRESS))
        # Loops through all indexed items
        returndata = []
        logging.error("Fetching nearest neighbors...")
        img_list_of_lists = []
        img_list = []
        window_size = math.floor(len(self._imagedata.getKeys())/cpu_count())
        i = 1
        for file_index, filename in enumerate(list(self._imagedata.getKeys())):
            if file_index < (window_size * i):
                img_list.append(file_index)
            else:
                img_list_of_lists.append(img_list)
                img_list = []
                i = i + 1
                img_list.append(file_index)
        img_list_of_lists.append(img_list)
        # read files separately using multithreaded pool
        pool = Pool(cpu_count())
        func = partial(get_nns, self._imagedata.getAnnoyIndexTempFile())
        load_results = pool.map_async(func, img_list_of_lists)
        pool.close()  # 'TERM'
        # maintain status gauge here
        while True:
            if load_results.ready() or self._want_abort == 1: break
            time.sleep(0.3)
            remaining = min(load_results._number_left * load_results._chunksize, len(img_list_of_lists))
            # print("Waiting for", remaining, "tasks to complete...")
            # wx.PostEvent(self._notify_window,
            #                  ResultEvent((len(img_list_of_lists) - remaining) / len(img_list_of_lists), EVT_RESULT_PROGRESS))
        if self._want_abort == 1:
            pool.terminate()
        pool.join()  # 'KILL'

        for list_of_thumb_nearest_neighbors in load_results.get():
            for thumb_nearest_neighbors in list_of_thumb_nearest_neighbors:
                names_list = []
                for item in thumb_nearest_neighbors:
                    name = list(self._imagedata.getKeys())[item]
                    names_list.append(name)
                returndata.append(names_list)
            # wx.PostEvent(self._notify_window,
            #              ResultEvent((file_index / self._imagedata.getSize()) * 0.25 + 0.75, EVT_RESULT_PROGRESS))
        wx.PostEvent(self._notify_window, ResultEvent(returndata, EVT_RESULT_NEIGHBORS))
        wx.PostEvent(self._notify_window, ResultEvent(None, EVT_RESULT_NEIGHBORS))
        wx.PostEvent(self._notify_window, ResultEvent(0.0, EVT_RESULT_PROGRESS))
        ################################################
        stoptime = datetime.now()
        logging.error(
            "ProcessAnnoyWorkerThread took " + str(stoptime - starttime) + " to process " + str(
                len(returndata)) + " image files")
