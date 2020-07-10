# -*- coding: utf-8 -*-

import logging
import multiprocessing

import wx
from wx.lib.dragscroller import DragScroller

from process import LoadImagesWorkerThread, EVT_RESULT_ID, ImageData, read_image_oriented, EVT_RESULT_MASTER, \
    EVT_RESULT_PROGRESS
from wxmainframe import MainFrame


def scale_bitmap(bitmap, width, height):
    image = bitmap.ConvertToImage()
    this_w, this_h = image.GetSize()
    factor_h = height / this_h
    factor_w = width / this_w
    factor = min(factor_w, factor_h)
    if factor < 1:
        image = image.Scale(this_w * factor, this_h * factor, wx.IMAGE_QUALITY_HIGH)
    else:
        factor = 1
    gap = (int((width - (this_w * factor)) / 2), int((height - (this_h * factor)) / 2))
    result = wx.Bitmap(image)
    return result, gap


def get_nearest_lower(entrylist, query):
    last = 0
    for entry in entrylist:
        if (query < entry):
            return last
        else:
            last = entry
    return last


class DragScrollerCustom(wx.ScrolledWindow):
    def __init__(self, parent, id, position, size, hints):
        wx.ScrolledWindow.__init__(self, parent, id, position, size, hints)
        self.Bind(wx.EVT_PAINT, self.onPaint)
        self.Bind(wx.EVT_RIGHT_DOWN, self.onRightDown)
        self.Bind(wx.EVT_RIGHT_UP, self.onRightUp)
        self.Bind(wx.EVT_LEFT_UP, self.onLeftUp)
        self.Bind(wx.EVT_LEFT_DCLICK, self.onDoubleClick)

        self.imagedata = None
        self.scroller = DragScroller(self)
        self.poskeydict = {}
        self.linecount = 0

    def onPaint(self, event):
        # print("OnPaint called!")
        dc = wx.PaintDC(self)
        self.DoPrepareDC(dc)
        self.poskeydict = {}

        if self.imagedata is not None:
            canvas_width, canvas_height = self.GetSize()
            drawpoint = (0, 0)
            count = 0
            self.linecount = 0
            month = 0
            year = 0
            dc.SetTextForeground((255, 0, 0))
            ps = dc.GetFont().GetPointSize() * 2
            font = wx.Font(pointSize=ps, family=wx.DEFAULT, style=wx.NORMAL, weight=wx.NORMAL, faceName='Consolas')
            hspace = int(font.GetPixelSize().height / 4)
            dc.SetFont(font)
            for key in self.imagedata.getKeysSortedByTime():
                thisyear, thismonth = self.imagedata.getYearMonth(key)
                # draw text YEAR/MONTH if new combination is detected
                if ((thisyear != year) or (thismonth != month)):
                    pointwidth, pointheight = drawpoint
                    # if the curser is at beginning of a line, not horizontal shift needed
                    if (pointwidth == 0):
                        dc.DrawText(str(thisyear) + "/" + str(thismonth), 0, pointheight + hspace)
                        pointheight = pointheight + hspace + font.GetPixelSize().height
                    # horizontal line break, to put the curser to the next beginning of a line
                    else:
                        dc.DrawText(str(thisyear) + "/" + str(thismonth), 0, pointheight + 241 + hspace)
                        pointheight = pointheight + 241 + hspace + font.GetPixelSize().height
                    pointwidth = 0
                    drawpoint = (pointwidth, pointheight)
                month = thismonth
                year = thisyear
                dc.DrawBitmap(self.imagedata.getThumbnail(key), drawpoint)
                pointwidth, pointheight = drawpoint
                # insert key into posekeydict to retrieve the key for a clicked position
                if (pointheight not in self.poskeydict.keys()):
                    self.poskeydict[pointheight] = {}
                self.poskeydict[pointheight][pointwidth] = key
                # print("Draw: " + str(count) + " " + key)
                count = count + 1
                pointwidth = pointwidth + 241
                if (pointwidth > (canvas_width - 241)):
                    pointwidth = 0
                    pointheight = pointheight + 241
                    if (self.linecount == 0):
                        self.linecount = count
                drawpoint = (pointwidth, pointheight)
            self.SetVirtualSize((canvas_width, pointheight + 241))
            self.Layout()

    def onRightDown(self, event):
        self.scroller.Start(event.GetPosition())

    def onRightUp(self, event):
        self.scroller.Stop()

    def onLeftUp(self, event):
        unscrolled = self.CalcUnscrolledPosition(event.GetPosition())
        logging.debug("OnLeftUp " + str(unscrolled))

    def onDoubleClick(self, event):
        unscrolled = self.CalcUnscrolledPosition(event.GetPosition())
        pointwidth, pointheight = unscrolled
        lomatchheight = get_nearest_lower(self.poskeydict.keys(), pointheight)
        lomatchwidth = get_nearest_lower(self.poskeydict[lomatchheight].keys(), pointwidth)

        key = self.poskeydict[lomatchheight][lomatchwidth]
        logging.debug("OnDoubleClick " + str(unscrolled) + " " + key)
        image = read_image_oriented(key)
        width, height = image.size
        wxbitmap = wx.Bitmap.FromBuffer(width, height, image.tobytes())
        dialog = ImageDialog(self, -1, title=key, bitmap=wxbitmap)
        dialog.Show()

    def redraw(self, imagedata):
        self.imagedata = imagedata
        self.Refresh()
        self.Update()


class ImageDialog(wx.Frame):

    def __init__(
            self, parent=None, id=-1, title="Das Bild", bitmap=None
    ):
        wx.Frame.__init__(self, parent, id, title)
        self.bitmap = bitmap
        width, height = wx.DisplaySize()
        width = width / 3 * 2
        height = height / 3 * 2
        self.SetClientSize((width, height))
        self.Bind(wx.EVT_PAINT, self.onPaint)

    def onPaint(self, event=None):
        dc = wx.PaintDC(self)
        width, height = self.GetSize()
        scaledbitmap, gap = scale_bitmap(self.bitmap, width, height)
        dc.DrawBitmap(scaledbitmap, gap)


class GUIMainFrame(MainFrame):

    def __init__(self, parent):
        super().__init__(parent)
        self.SetTitle("Image Similarity Viewer")
        icon = wx.Icon()
        icon.CopyFromBitmap(wx.Bitmap("isv.ico", wx.BITMAP_TYPE_ANY))
        self.SetIcon(icon)
        # Add the Canvas
        self.m_scrolledWindow = DragScrollerCustom(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
                                                   wx.HSCROLL | wx.VSCROLL)
        self.m_scrolledWindow.SetScrollRate(5, 5)
        self.bSizerImageSection.Add(self.m_scrolledWindow, 1, wx.EXPAND | wx.ALL, 5)

        # Set up event handler for any worker thread results
        self.Connect(-1, -1, EVT_RESULT_ID, self.onResult)
        # And indicate we don't have a worker thread yet
        self.worker = None
        # init data object
        self.imagedata = ImageData()

    def openFolderHandler(self, event):
        """
            Browse for file
        """
        dialog = wx.DirDialog(None, "Choose a folder",
                              style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            logging.info("Open folders non-recursively.. "+dialog.GetPath())
        self.m_staticTextStatus.SetLabel('Loading Images...from ' + dialog.GetPath())

        # start WorkerThread
        self.worker = LoadImagesWorkerThread(self, dialog.GetPath(), self.imagedata)

        dialog.Destroy()
        event.Skip()


    def openFoldersHandler(self, event):
        """
            Browse for file
        """
        dialog = wx.DirDialog(None, "Choose a folder",
                              style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            logging.info("Open folders recursively.. "+dialog.GetPath())
        self.m_staticTextStatus.SetLabel('Loading Images recursively...from ' + dialog.GetPath())

        # start WorkerThread
        self.worker = LoadImagesWorkerThread(self, dialog.GetPath(), self.imagedata, recursive=True)

        dialog.Destroy()
        event.Skip()


    def onResult(self, event):
        """Show Result status."""
        if event.data is None:
            # Thread aborted (using our convention of None return)
            size = self.imagedata.getSize()
            self.m_staticTextStatus.SetLabel('finished.. ' + str(size) + " images")
        elif event.type == EVT_RESULT_PROGRESS:
            data=event.data
            self.m_gaugeStatus.SetValue(data*100)
        elif event.type == EVT_RESULT_MASTER:
            self.m_scrolledWindow.redraw(self.imagedata)



if __name__ == '__main__':
    multiprocessing.freeze_support()
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.WARN)
    app = wx.App(False)
    frame = GUIMainFrame(None)
    frame.Show()
    logging.info("Application started..")
    app.MainLoop()