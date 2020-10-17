# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version 3.9.0 Jan 14 2020)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc


###########################################################################
## Class MainFrame
###########################################################################

class MainFrame(wx.Frame):

    def __init__(self, parent):
        wx.Frame.__init__(self, parent, id=wx.ID_ANY, title=wx.EmptyString, pos=wx.DefaultPosition,
                          size=wx.Size(1280, 720), style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        self.m_menubar = wx.MenuBar(0)
        # File menu
        self.file = wx.Menu()
        self.openFolder = wx.MenuItem(self.file, wx.ID_ANY, u"Open Folder", wx.EmptyString, wx.ITEM_NORMAL)
        self.file.Append(self.openFolder)

        self.openFolders = wx.MenuItem(self.file, wx.ID_ANY, u"Open Folders ...", wx.EmptyString, wx.ITEM_NORMAL)
        self.file.Append(self.openFolders)

        self.m_menubar.Append(self.file, u"File")
        # Process menu
        self.process = wx.Menu()
        self.processAnnoy = wx.MenuItem(self.process, wx.ID_ANY, u"Process Annoy", wx.EmptyString, wx.ITEM_NORMAL)
        self.process.Append(self.processAnnoy)

        self.m_menubar.Append(self.process, u"Process")

        self.SetMenuBar(self.m_menubar)

        self.bSizerMainFrame = wx.BoxSizer(wx.VERTICAL)

        self.bSizerImageSection = wx.BoxSizer(wx.HORIZONTAL)

        self.bSizerMainFrame.Add(self.bSizerImageSection, 1, wx.ALIGN_TOP | wx.EXPAND | wx.TOP, 5)

        self.bSizerStatusFooter = wx.BoxSizer(wx.HORIZONTAL)

        self.m_staticTextStatus = wx.StaticText(self, wx.ID_ANY, u"status message", wx.DefaultPosition, wx.DefaultSize,
                                                0)
        self.m_staticTextStatus.Wrap(-1)

        self.bSizerStatusFooter.Add(self.m_staticTextStatus, 0, wx.ALL, 5)

        self.m_gaugeStatus = wx.Gauge(self, wx.ID_ANY, 100, wx.DefaultPosition, wx.DefaultSize, wx.GA_HORIZONTAL)
        self.m_gaugeStatus.SetValue(0)
        self.bSizerStatusFooter.AddStretchSpacer()
        self.bSizerStatusFooter.Add(self.m_gaugeStatus, 0, wx.ALL, 5)

        self.bSizerMainFrame.Add(self.bSizerStatusFooter, 0,  wx.EXPAND, 5)

        self.SetSizer(self.bSizerMainFrame)
        self.Layout()

        self.Centre(wx.BOTH)

        # Connect Events
        self.Bind(wx.EVT_MENU, self.openFolderHandler, id=self.openFolder.GetId())
        self.Bind(wx.EVT_MENU, self.openFoldersHandler, id=self.openFolders.GetId())
        self.Bind(wx.EVT_MENU, self.processAnnoyHandler, id=self.processAnnoy.GetId())
        self.Bind(wx.EVT_CLOSE, self.onClose)

    def __del__(self):
        pass

    # Virtual event handlers, overide them in your derived class
    def openFolderHandler(self, event):
        event.Skip()

    def openFoldersHandler(self, event):
        event.Skip()

    def processAnnoyHandler(self, event):
        event.Skip()

    def onClose(self, event):
        event.Skip()
