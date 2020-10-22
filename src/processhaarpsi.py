# -*- coding: utf-8 -*-
import logging
import time
from datetime import datetime
from multiprocessing import cpu_count
from multiprocessing.pool import Pool
from threading import Thread

import numpy as np
from process import MAX_NEIGHBOR_DISPLAY, ResultEvent, EVT_RESULT_NEIGHBORS, EVT_RESULT_MASTER, THUMBNAIL_MAX_SIZE
import wx

import haarPsi



class ProcessHaarPSIWorkerThread(Thread):
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
        start_time = time.time()
        dict_filename_ocvimg = {}

        starttime = datetime.now()
        ################################################
        logging.error("Start processing HaarPSI...")
        for item in self._imagedata.getKeys():
            # Loads and pre-process the image
            btmp = self._imagedata.getThumbnail(item)
            image_array = np.fromstring(bytes(btmp), dtype=np.uint8).reshape(
                (THUMBNAIL_MAX_SIZE, THUMBNAIL_MAX_SIZE, 3))
            dict_filename_ocvimg[item] = image_array

        returndata = []
        for file1 in dict_filename_ocvimg.keys():
            thumb_nearest_neighbors = []
            similarities = {}
            pool = Pool(cpu_count())
            results = pool.starmap(haarPsi.haar_psi,
                                   [(dict_filename_ocvimg[file1], dict_filename_ocvimg[file2], file2) for file2 in
                                    dict_filename_ocvimg.keys()])
            pool.close()  # 'TERM'
            pool.join()  # 'KILL'
            for item in results:
                (similarity, local_similarities, weights), file2_name = item
                similarities[similarity] = file2_name
            i = 0
            for key in sorted(similarities.keys(), reverse=True):
                neighbor_name = similarities[key]
                #neighbor_thumb = self._imagedata.getThumbnail(neighbor_name)
                thumb_nearest_neighbors.append(neighbor_name)
                i = i + 1
                if i == MAX_NEIGHBOR_DISPLAY:
                    break
            returndata.append(thumb_nearest_neighbors)
        wx.PostEvent(self._notify_window, ResultEvent(returndata, EVT_RESULT_NEIGHBORS))
        wx.PostEvent(self._notify_window, ResultEvent(None, EVT_RESULT_MASTER))
        print("--- %.2f seconds passed ---------" % (time.time() - start_time))
