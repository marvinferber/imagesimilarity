# -*- coding: utf-8 -*-

import logging
import multiprocessing
import os
import math
import shutil

import wx
from wx.lib.dragscroller import DragScroller

import process
import processannoy
from wxmainframe import MainFrame
from isv import isv
from PIL import ImageDraw, ImageFont

THUMBNAIL_MAX_SIZE = process.THUMBNAIL_MAX_SIZE

def draw_month_year_top_right(image, year, month,
                              margin=10,
                              color=(255, 179, 186)):
    """
    Zeichnet 'YYYY-MM' oben rechts in roter Schrift in das PIL-Image.
    Die Schriftgröße wird dynamisch aus der Bildhöhe abgeleitet.
    """
    draw = ImageDraw.Draw(image)
    text = f"{year:04d}-{month:02d}"

    # dynamische Schriftgröße, z.B. 1/25 der Bildhöhe
    img_w, img_h = image.size
    font_size = max(12, img_h // 18)  # Mindestgröße 12px

    try:
        # Pfad ggf. anpassen oder andere Standard-Schrift nutzen
        #font = ImageFont.truetype("/usr/share/fonts/opentype/opendyslexic/OpenDyslexic-Bold.otf",font_size) #truetype("/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf", font_size)
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", font_size)
    except IOError:
        # Fallback, falls TTF nicht gefunden wird
        logging.warn("ImageFont arial.ttf not found --> using default")
        font = ImageFont.load_default()

    # Textgröße bestimmen (per getbbox oder textbbox, je nach Pillow-Version)
    try:
        # moderne Variante
        bbox = font.getbbox(text)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except AttributeError:
        # Fallback für ältere Versionen
        text_w, text_h = draw.textsize(text, font=font)

    x = img_w - text_w - margin
    y = margin

    draw.text((x, y), text, fill=color, font=font)
    return image

def scale_bitmap(bitmap, width, height):
    image = bitmap.ConvertToImage()
    this_w, this_h = image.GetSize()
    factor_h = height / this_h
    factor_w = width / this_w
    factor = min(factor_w, factor_h)
    if factor < 1:
        image = image.Scale(int(this_w * factor),
                            int(this_h * factor),
                            wx.IMAGE_QUALITY_HIGH)
    else:
        factor = 1
    gap = (int((width - (this_w * factor)) / 2),
           int((height - (this_h * factor)) / 2))
    result = wx.Bitmap(image)
    return result, gap


def get_nearest_lower(entrylist, query):
    last = 0
    for entry in entrylist:
        if query < entry:
            return last
        else:
            last = entry
    return last


class DragScrollerGallery(wx.ScrolledWindow):
    """
    Thumbnail-Galerie mit:
    - Jahr/Monat-Header-Zeilen,
    - virtueller Darstellung (nur sichtbare Zeilen zeichnen),
    - Bitmap-Cache pro Bild.
    """

    def __init__(self, imagedata, parent, id, position, size, hints):
        super().__init__(parent, id, position, size, hints)

        self.imagedata = imagedata
        self.scroller = DragScroller(self)

        # Thumbnail-Layout
        self.thumb_w = THUMBNAIL_MAX_SIZE
        self.thumb_h = THUMBNAIL_MAX_SIZE
        self.step_x = self.thumb_w + 1
        self.step_y = self.thumb_h + 1

        # Daten & Layoutstruktur
        self.keys = []
        if self.imagedata is not None:
            self.keys = list(self.imagedata.getKeysSortedByTime())

        self.thumbs_per_row = 1
        self.row_height = self.step_y
        # rows = Liste von Zeilen:
        # {"type": "header", "year": y, "month": m}
        # {"type": "thumbs", "keys": [k1, k2, ...]}
        self.rows = []

        # Cache für Thumbnails
        self.bitmap_cache = {}  # key -> wx.Bitmap

        # Events
        self.Bind(wx.EVT_PAINT, self.onPaint)
        self.Bind(wx.EVT_RIGHT_DOWN, self.onRightDown)
        self.Bind(wx.EVT_RIGHT_UP, self.onRightUp)
        self.Bind(wx.EVT_LEFT_UP, self.onLeftUp)
        self.Bind(wx.EVT_LEFT_DCLICK, self.onDoubleClick)
        self.Bind(wx.EVT_SIZE, self.onSize)

        # Double Buffering
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)

        # Layout initial berechnen
        self._update_layout()

    # ---------------------------------------------------------
    # Layout-Berechnung
    # ---------------------------------------------------------
    def _rebuild_rows(self):
        """
        Baut self.rows aus self.keys und self.thumbs_per_row,
        inkl. Jahr/Monat-Header-Zeilen.
        """
        self.rows = []

        if not self.keys or self.imagedata is None:
            return

        current_month = None
        current_year = None
        current_row_keys = []
        col = 0

        for key in self.keys:
            year, month = self.imagedata.getYearMonth(key)

            # Bei neuem Jahr/Monat: Header-Zeile einfügen
            if (year != current_year) or (month != current_month):
                # laufende Thumb-Zeile abschließen
                if current_row_keys:
                    self.rows.append({"type": "thumbs",
                                      "keys": current_row_keys})
                    current_row_keys = []
                    col = 0

                # Header-Zeile für neuen Monat
                self.rows.append({"type": "header",
                                  "year": year,
                                  "month": month})
                current_year, current_month = year, month

            # Key in aktuelle Thumb-Zeile aufnehmen
            current_row_keys.append(key)
            col += 1

            # Zeile voll -> als eigene Zeile speichern
            if col >= self.thumbs_per_row:
                self.rows.append({"type": "thumbs",
                                  "keys": current_row_keys})
                current_row_keys = []
                col = 0

        # Reste (nicht voll gefüllte Zeile) anhängen
        if current_row_keys:
            self.rows.append({"type": "thumbs",
                              "keys": current_row_keys})

    def _update_layout(self):
        """
        Aktualisiert thumbs_per_row, rows und VirtualSize.
        """
        client_w, client_h = self.GetClientSize()
        if client_w <= 0:
            client_w = 1

        self.thumbs_per_row = max(1, client_w // self.step_x)

        # Zeilenstruktur neu aufbauen
        self._rebuild_rows()

        rows_count = len(self.rows)
        if rows_count <= 0:
            rows_count = 1

        # row_height konstant (hier: Höhe einer Thumbnail-Zeile)
        self.row_height = self.step_y

        virtual_h = rows_count * self.row_height
        if virtual_h <= 0:
            virtual_h = self.row_height

        self.SetVirtualSize((client_w, virtual_h))

    # ---------------------------------------------------------
    # Bild-Cache
    # ---------------------------------------------------------
    def _get_bitmap(self, key):
        bmp = self.bitmap_cache.get(key)
        if bmp is None:
            try:
                buffer = self.imagedata.getThumbnail(key)
                bmp = wx.Bitmap.FromBuffer(self.thumb_w,
                                           self.thumb_h,
                                           buffer)
                self.bitmap_cache[key] = bmp
            except (ValueError, RuntimeError) as err:
                logging.warn("Thumbnail error: {0} at image {1}".format(err, key))
                return None
        return bmp

    # ---------------------------------------------------------
    # Event-Handler
    # ---------------------------------------------------------
    def onSize(self, event):
        self._update_layout()
        self.Refresh()
        event.Skip()

    def onPaint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        self.DoPrepareDC(dc)
        dc.Clear()

        if self.imagedata is None or not self.rows:
            return

        client_w, client_h = self.GetClientSize()
        if client_w <= 0 or client_h <= 0:
            return

        # Scrollposition (virtuell -> Pixel)
        vx, vy = self.GetViewStart()
        sx, sy = self.GetScrollPixelsPerUnit()
        offset_y = vy * sy

        rows_count = len(self.rows)
        if rows_count == 0:
            return

        visible_top = offset_y
        visible_bottom = offset_y + client_h

        first_row = max(0, (visible_top // self.row_height) - 1)
        last_row = min(rows_count - 1, (visible_bottom // self.row_height) + 1)

        # Schrift für Header
        dc.SetTextForeground((255, 0, 0))
        ps = dc.GetFont().GetPointSize() * 2
        font = wx.Font(pointSize=ps,
                       family=wx.DEFAULT,
                       style=wx.NORMAL,
                       weight=wx.NORMAL,
                       faceName='Consolas')
        dc.SetFont(font)
        hspace = int(font.GetPixelSize().height / 4)

        for row_idx in range(first_row, last_row + 1):
            row = self.rows[row_idx]
            row_y = row_idx * self.row_height

            if row["type"] == "header":
                text = "{}/{}".format(row["year"], row["month"])
                # Text mit etwas Abstand zeichnen
                dc.DrawText(text, 0, row_y + hspace)
            else:
                # Thumbnail-Zeile
                keys_in_row = row["keys"]
                for col, key in enumerate(keys_in_row):
                    x = col * self.step_x
                    y = row_y
                    bmp = self._get_bitmap(key)
                    if bmp:
                        dc.DrawBitmap(bmp, x, y)

        # zur Sicherheit VirtualSize aktuell halten
        self._update_layout()

    def onRightDown(self, event):
        self.scroller.Start(event.GetPosition())

    def onRightUp(self, event):
        self.scroller.Stop()

    def onLeftUp(self, event):
        unscrolled = self.CalcUnscrolledPosition(event.GetPosition())
        logging.debug("OnLeftUp " + str(unscrolled))

    def onDoubleClick(self, event):
        if self.imagedata is None or not self.rows:
            return

        ux, uy = self.CalcUnscrolledPosition(event.GetPosition())
        if ux < 0 or uy < 0:
            return

        row_idx = uy // self.row_height
        if row_idx < 0 or row_idx >= len(self.rows):
            return

        row = self.rows[row_idx]
        if row["type"] != "thumbs":
            # Klick auf Header-Zeile -> ignorieren
            return

        col = ux // self.step_x
        if col < 0 or col >= len(row["keys"]):
            return

        filename = row["keys"][col]
        logging.debug("OnDoubleClick " + str((ux, uy)) + " " + filename)
        image = process.read_image_oriented(filename)
        width, height = image.size
        wxbitmap = wx.Bitmap.FromBuffer(width, height, image.tobytes())
        dialog = ImageDialog(self, -1, title=filename, bitmap=wxbitmap)
        dialog.Show()

    def redraw(self, data=None):
        # Daten neu aus imagedata holen
        if self.imagedata is not None:
            self.keys = list(self.imagedata.getKeysSortedByTime())
        else:
            self.keys = []
        self.bitmap_cache.clear()
        self._update_layout()
        self.Refresh()
        self.Update()


class DragScrollerSimilarity(wx.ScrolledWindow):
    """
    Ähnlichkeitsansicht mit Bitmap-Cache und AutoBufferedPaintDC.
    """

    def __init__(self, imagedata, parent, id, position, size, hints):
        super().__init__(parent, id, position, size, hints)

        self.imagedata = imagedata
        self.similaritydata = None
        self.scroller = DragScroller(self)
        self.bitmap_cache = {}
        self.poskeydict = {}
        self.linecount = 0

        self.Bind(wx.EVT_PAINT, self.onPaint)
        self.Bind(wx.EVT_RIGHT_DOWN, self.onRightDown)
        self.Bind(wx.EVT_RIGHT_UP, self.onRightUp)
        self.Bind(wx.EVT_LEFT_UP, self.onLeftUp)
        self.Bind(wx.EVT_LEFT_DCLICK, self.onDoubleClick)

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)

    def _get_bitmap(self, key):
        bmp = self.bitmap_cache.get(key)
        if bmp is None:
            try:
                buffer = self.imagedata.getThumbnail(key)
                bmp = wx.Bitmap.FromBuffer(THUMBNAIL_MAX_SIZE,
                                           THUMBNAIL_MAX_SIZE,
                                           buffer)
                self.bitmap_cache[key] = bmp
            except (ValueError, RuntimeError) as err:
                logging.warn("Thumbnail error: {0} at image {1}".format(err, key))
                return None
        return bmp

    def onPaint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        self.DoPrepareDC(dc)
        self.poskeydict = {}
        dc.Clear()

        if self.similaritydata is not None:
            canvas_width, canvas_height = self.GetSize()

            # heading
            dc.SetTextForeground((255, 0, 0))
            ps = dc.GetFont().GetPointSize() * 2
            font = wx.Font(pointSize=ps,
                           family=wx.DEFAULT,
                           style=wx.NORMAL,
                           weight=wx.NORMAL,
                           faceName='Consolas')
            hspace = int(font.GetPixelSize().height / 4)
            dc.SetFont(font)
            dc.DrawText("original", 0, hspace)
            dc.DrawText("--> approximate most similar images",
                        THUMBNAIL_MAX_SIZE,
                        hspace)
            pointheight = (hspace * 2) + font.GetPixelSize().height

            # set cursor
            drawpoint = (0, pointheight)

            for line in self.similaritydata:
                first = True
                for key in line:
                    bmp = self._get_bitmap(key)
                    if not bmp:
                        continue
                    dc.DrawBitmap(bmp, drawpoint)
                    pointwidth, pointheight = drawpoint
                    # insert key into poskeydict to retrieve the key for a clicked position
                    if pointheight not in self.poskeydict:
                        self.poskeydict[pointheight] = {}
                    self.poskeydict[pointheight][pointwidth] = key

                    if first:
                        pointwidth = int(pointwidth + THUMBNAIL_MAX_SIZE +
                                         THUMBNAIL_MAX_SIZE / 4 + 1)
                        first = False
                    else:
                        pointwidth = pointwidth + THUMBNAIL_MAX_SIZE + 1
                    drawpoint = (pointwidth, pointheight)

                pointwidth, pointheight = drawpoint
                pointwidth = 0
                pointheight = pointheight + THUMBNAIL_MAX_SIZE + 1
                drawpoint = (pointwidth, pointheight)

            self.SetVirtualSize((canvas_width,
                                 pointheight + THUMBNAIL_MAX_SIZE + 1))
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
        lomatchheight = get_nearest_lower(self.poskeydict.keys(),
                                          pointheight)
        lomatchwidth = get_nearest_lower(self.poskeydict[lomatchheight].keys(),
                                         pointwidth)

        key = self.poskeydict[lomatchheight][lomatchwidth]
        logging.debug("OnDoubleClick " + str(unscrolled) + " " + key)
        image = process.read_image_oriented(key)
        width, height = image.size
        wxbitmap = wx.Bitmap.FromBuffer(width, height, image.tobytes())
        dialog = ImageDialog(self, -1, title=key, bitmap=wxbitmap)
        dialog.Show()

    def redraw(self, data):
        self.similaritydata = data
        self.bitmap_cache.clear()
        self.Refresh()
        self.Update()


class ImageDialog(wx.Frame):

    def __init__(self, parent=None, id=-1, title="Das Bild", bitmap=None):
        self.image_path = title
        frame_title = os.path.basename(title) if title else "Das Bild"

        wx.Frame.__init__(self, parent, id, frame_title)
        self.bitmap = bitmap

        width, height = wx.DisplaySize()
        width = int(width / 3 * 2)
        height = int(height / 3 * 2)
        self.SetClientSize((width, height))

        self.Bind(wx.EVT_PAINT, self.onPaint)
        self.Bind(wx.EVT_RIGHT_DOWN, self.onRightClick)

    def onPaint(self, event=None):
        dc = wx.PaintDC(self)
        width, height = self.GetSize()
        scaledbitmap, gap = scale_bitmap(self.bitmap, width, height)
        dc.DrawBitmap(scaledbitmap, gap)

    def onRightClick(self, event):
        if not self.image_path or not os.path.isfile(self.image_path):
            wx.MessageBox("Original image file not found.",
                          "Error",
                          wx.OK | wx.ICON_ERROR)
            return

        default_name = os.path.basename(self.image_path)
        wildcard = ("Image files|*.jpg;*.jpeg;*.png;*.bmp;*.tif;*.tiff|"
                    "All files|*.*")

        with wx.FileDialog(
            self,
            message="Bild speichern unter...",
            defaultFile=default_name,
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        ) as dlg:
            if dlg.ShowModal() == wx.ID_CANCEL:
                return

            shutil.copy2(self.image_path, dlg.GetPath())


class GUIMainFrame(MainFrame):

    def __init__(self, parent):
        super().__init__(parent)
        self.SetTitle("Image Similarity Viewer")
        icon = isv.GetIcon()
        self.SetIcon(icon)

        # init data object
        self.imagedata = process.ImageData()

        # Add the Canvas
        self.m_scrolledWindow = DragScrollerGallery(
            self.imagedata,
            self,
            wx.ID_ANY,
            wx.DefaultPosition,
            wx.DefaultSize,
            wx.HSCROLL | wx.VSCROLL
        )
        self.m_scrolledWindow.SetScrollRate(15, 15)
        self.bSizerImageSection.Add(self.m_scrolledWindow,
                                    1,
                                    wx.EXPAND | wx.ALL,
                                    5)

        # Set up event handler for any worker thread results
        self.Connect(-1, -1, process.EVT_RESULT_ID, self.onResult)
        self.worker = None

    def processAnnoyHandler(self, event):
        """
            Compute similar images
        """
        self.m_staticTextStatus.SetLabel('Computing similarities annoy... ')

        # start WorkerThread
        self.worker = processannoy.ProcessAnnoyWorkerThread(self,
                                                            self.imagedata)
        event.Skip()

    def openFolderHandler(self, event):
        """
            Browse for file
        """
        dialog = wx.DirDialog(None,
                              "Choose a folder",
                              style=(wx.DD_DEFAULT_STYLE |
                                     wx.DD_DIR_MUST_EXIST))
        if dialog.ShowModal() == wx.ID_OK:  # only start loading on OK
            logging.info("Open folders non-recursively.. " + dialog.GetPath())
            self.m_staticTextStatus.SetLabel('Loading Images...from ' +
                                             dialog.GetPath())
            # start WorkerThread
            self.worker = process.LoadImagesWorkerThread(self,
                                                         dialog.GetPath(),
                                                         self.imagedata)

        dialog.Destroy()
        event.Skip()

    def openFoldersHandler(self, event):
        """
            Browse for file
        """
        dialog = wx.DirDialog(None,
                              "Choose a folder",
                              style=(wx.DD_DEFAULT_STYLE |
                                     wx.DD_DIR_MUST_EXIST))
        if dialog.ShowModal() == wx.ID_OK:
            logging.info("Open folders recursively.. " + dialog.GetPath())
            self.m_staticTextStatus.SetLabel(
                'Loading Images recursively...from ' + dialog.GetPath()
            )
            # start WorkerThread
            self.worker = process.LoadImagesWorkerThread(self,
                                                         dialog.GetPath(),
                                                         self.imagedata,
                                                         recursive=True)

        dialog.Destroy()
        event.Skip()
    
    def exportImagesHandler(self, event):
        """
            Exportiert alle geladenen Bilder in einen Zielordner.
            Optional wird 'YYYY-MM' oben rechts in jedes Bild gezeichnet.
        """
        # Prüfen, ob überhaupt Bilder geladen sind
        if self.imagedata is None or self.imagedata.getSize() == 0:
            wx.MessageBox("Es sind keine Bilder geladen.",
                          "Export",
                          wx.OK | wx.ICON_INFORMATION)
            return

        # Nutzer fragen, ob Datum-Overlay gewünscht ist
        dlg = wx.MessageDialog(
            self,
            "Möchten Sie Monat und Jahr der Bildaufnahme "
            "oben rechts in jedes Bild einblenden?",
            "Export-Option",
            style=wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION
        )
        res = dlg.ShowModal()
        dlg.Destroy()

        if res == wx.ID_CANCEL:
            return
        annotate = (res == wx.ID_YES)

        # Zielordner vom Nutzer abfragen
        with wx.DirDialog(
            self,
            "Exportordner wählen",
            style=wx.DD_DEFAULT_STYLE | wx.DD_NEW_DIR_BUTTON
        ) as dir_dlg:
            if dir_dlg.ShowModal() != wx.ID_OK:
                return
            target_dir = dir_dlg.GetPath()

        # Dateien nach Zeit sortiert holen
        keys = list(self.imagedata.getKeysSortedByTime())

        # Anzahl Stellen für führende Nullen berechnen (0001, 0002, ...)
        if len(keys) > 0:
            digits = int(math.log10(len(keys))) + 1
        else:
            digits = 1
        logging.error(f"Es werden {len(keys)} Dateien für den Export vorbereitet")
        exported_count = 0

        for idx, key in enumerate(keys, start=1):
            src = key  # key ist hier der Dateipfad

            if not os.path.isfile(src):
                continue

            basename = os.path.basename(src)
            prefix = f"{idx:0{digits}d}_"
            dst_path = os.path.join(target_dir, prefix + basename)

            try:
                if annotate:
                    # Jahr/Monat aus imagedata holen
                    year, month = self.imagedata.getYearMonth(key)

                    # Bild laden, Datum zeichnen und speichern
                    image = process.read_image_oriented(src)
                    image = draw_month_year_top_right(image, year, month)
                    image.save(dst_path)
                else:
                    # Nur kopieren (mit Metadaten)
                    shutil.copy2(src, dst_path)

                exported_count += 1
            except Exception as e:
                logging.error("Fehler beim Export %s -> %s: %s",
                                src, dst_path, e)

        wx.MessageBox(
            f"{exported_count} Dateien exportiert nach:\n{target_dir}",
            "Export abgeschlossen",
            wx.OK | wx.ICON_INFORMATION
        )
        
        
    def onResult(self, event):
        """Show Result status."""
        if event.data is None:
            # Thread aborted (using our convention of None return)
            size = self.imagedata.getSize()
            self.m_staticTextStatus.SetLabel('finished.. ' +
                                             str(size) + " images")
        elif event.type == process.EVT_RESULT_PROGRESS:
            data = int(event.data)
            self.m_gaugeStatus.SetValue(data * 100)
        elif event.type == process.EVT_RESULT_MASTER:
            # reinitialize DragScroller (Galerie)
            self.bSizerImageSection.Hide(self.m_scrolledWindow)
            self.bSizerImageSection.Remove(0)
            self.m_scrolledWindow = DragScrollerGallery(
                self.imagedata,
                self,
                wx.ID_ANY,
                wx.DefaultPosition,
                wx.DefaultSize,
                wx.HSCROLL | wx.VSCROLL
            )
            self.m_scrolledWindow.SetScrollRate(15, 15)
            self.bSizerImageSection.Add(self.m_scrolledWindow,
                                        1,
                                        wx.EXPAND | wx.ALL,
                                        5)
            self.bSizerImageSection.Layout()
            # actual redraw with new data
            self.m_scrolledWindow.redraw(None)

        elif event.type == process.EVT_RESULT_NEIGHBORS:
            self.bSizerImageSection.Hide(self.m_scrolledWindow)
            self.bSizerImageSection.Remove(0)
            self.m_scrolledWindow = DragScrollerSimilarity(
                self.imagedata,
                self,
                wx.ID_ANY,
                wx.DefaultPosition,
                wx.DefaultSize,
                wx.HSCROLL | wx.VSCROLL
            )
            self.m_scrolledWindow.SetScrollRate(15, 15)
            self.bSizerImageSection.Add(self.m_scrolledWindow,
                                        1,
                                        wx.EXPAND | wx.ALL,
                                        5)
            self.bSizerImageSection.Layout()
            self.m_scrolledWindow.redraw(event.data)

    def onClose(self, event):
        logging.error("delete AnnoyIndex file (if exists)" +
                      self.imagedata.getAnnoyIndexTempFile())
        if os.path.exists(self.imagedata.getAnnoyIndexTempFile()):
            os.remove(self.imagedata.getAnnoyIndexTempFile())
        self.Destroy()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',
                        level=logging.WARN)
    app = wx.App(False)
    frame = GUIMainFrame(None)
    frame.Show()
    logging.info("Application started..")
    app.MainLoop()