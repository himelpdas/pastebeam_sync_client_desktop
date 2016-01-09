from application_widgets import *

class UIMixin(QtGui.QMainWindow): #AccountMixin): #handles menubar and statusbar, which qwidget did not do
    #SLOT IS A QT TERM MEANING EVENT
    def init_ui(self):
        self.stacked_widget = LockoutStackedWidget(self)

        self.init_panel()
        self.init_menu_bar()
        self.init_status_bar()
        self.init_window_features()

        self.setCentralWidget(self.stacked_widget)

        self.init_tray_icon()

        self.show()

        self.lock_on_start()

    def init_window_features(self):
        desk = self.desktop.availableGeometry()
        desk_w = desk.width()
        desk_h = desk.height()
        app_w = desk_w * 0.55
        app_h = desk_h * 0.66
        app_x = desk_w / 2.0 - app_w / 2.0
        app_y = desk_h / 2.0 - app_h / 2.0
        self.setGeometry(app_x, app_y, app_w, app_h)
        self.setWindowTitle('PasteBeam 1.0.0')



    def lock_on_start(self):
        """Will show lock widget if settings.is_locked is True"""
        try:
            if settings.is_locked:
                self.lockout_widget.on_show_lockout_slot()
        except KeyError:
            pass

    def init_panel(self):
        self.panel_tab_widget = PanelTabWidget(QtCore.QSize(self.px_to_dp(24) , self.px_to_dp(24) ), self)
        self.lockout_widget = LockoutWidget(self)
        #for each in self.panel_tab_widget.panels:
        #    each.itemDoubleClicked.connect(each.on_item_double_click_slot) #textChanged() is emited whenever the contents of the widget changes (even if its from the app itself) whereas textEdited() is emited only when the user changes the text using mouse and keyboard (so it is not emitted when you call QtGui.QLineEdit::setText()).
        self.stacked_widget.addWidget(self.panel_tab_widget)
        self.stacked_widget.addWidget(self.lockout_widget)

    def init_menu_bar(self):
        """this is better in a mixin since menubar instance is accessed externally via self.menuBar()"""

        menubar = self.menuBar()

        ### file ###

        file_menu = menubar.addMenu('&File')

        lockout_action = QtGui.QAction(AppIcon("safe"), '&Lock', self)
        lockout_action.setStatusTip('Lock the application')
        lockout_action.triggered.connect(self.lockout_widget.on_show_lockout_slot )

        file_menu.addAction(lockout_action)
        file_menu.addSeparator()

        exit_action = QtGui.QAction(AppIcon("exit"), '&Exit', self)    #http://ubuntuforums.org/archive/index.php/t-724672.htmls
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(self.closeReal) #exit_action.triggered.connect(QtGui.qApp.quit) #does not trigger closeEvent()

        file_menu.addAction(exit_action)

        ### edit ###
        settings_action = QtGui.QAction(AppIcon("settings"), "&Settings", self)
        settings_action.setStatusTip('Edit settings')
        settings_action.triggered.connect(lambda:SettingsDialog.show(self))

        contacts_action = QtGui.QAction(AppIcon("contacts"), "&Contacts", self)
        contacts_action.triggered.connect(lambda:ContactsDialog.show(self))
        contacts_action.setStatusTip("Edit your contacts")

        edit_menu = menubar.addMenu('&Edit')
        edit_menu.addAction(contacts_action)
        edit_menu.addSeparator()
        edit_menu.addAction(settings_action)

        ### view ###

        self.view_menu = view_menu = menubar.addMenu('&View')
        self.view_menu.aboutToShow.connect(self.on_view_menu_about_to_show) #todo implement device filter #http://stackoverflow.com/questions/22197496/how-to-perform-action-on-clicking-a-qmenu-object-only
        self.view_action_group = view_action_group = QtGui.QActionGroup(self)
        view_action_group.setExclusive(False)
        show_files_action = QtGui.QAction(AppIcon("files"),"Files", self)
        show_files_action.setCheckable(True)
        show_files_action.setChecked(True)
        view_menu.addAction(show_files_action)
        view_action_group.addAction(show_files_action)  # view_action_group access actions externally, no overloading needed
        show_screenshots_action = QtGui.QAction(AppIcon("image"),"Screenshots", self)
        show_screenshots_action.setCheckable(True)
        show_screenshots_action.setChecked(True)
        view_menu.addAction(show_screenshots_action)
        view_action_group.addAction(show_screenshots_action)
        show_text_action = QtGui.QAction(AppIcon("text"),"Text/Html", self)
        show_text_action.setCheckable(True)
        show_text_action.setChecked(True)
        view_menu.addAction(show_text_action)
        view_action_group.addAction(show_text_action)

        view_menu.addSeparator()

        view_action_group.triggered.connect(self.panel_tab_widget.on_change_view_menu)

        ### window ###
        # http://stackoverflow.com/questions/23429663/qt-mutually-exclusive-checkable-menu-items
        window_menu = menubar.addMenu("&Window")
        transparency_action = QtGui.QAction(AppIcon("sun"), "&Transparency", self)
        transparency_sub_menu = QtGui.QMenu()
        transparency_action.setMenu(transparency_sub_menu)
        transparency_action_group = QtGui.QActionGroup(self)
        transparency_action_group.setExclusive(True)
        transparency_00pct = QtGui.QAction("Disabled", self)
        transparency_00pct.setCheckable(True)
        transparency_00pct.setChecked(True)
        transparency_sub_menu.addAction(transparency_00pct)
        transparency_action_group.addAction(transparency_00pct)
        transparency_10pct = QtGui.QAction("10 %", self)
        transparency_10pct.setCheckable(True)
        transparency_sub_menu.addAction(transparency_10pct)
        transparency_action_group.addAction(transparency_10pct)
        transparency_20pct = QtGui.QAction("20 %", self)
        transparency_20pct.setCheckable(True)
        transparency_sub_menu.addAction(transparency_20pct)
        transparency_action_group.addAction(transparency_20pct)
        transparency_30pct = QtGui.QAction("30 %", self)
        transparency_30pct.setCheckable(True)
        transparency_sub_menu.addAction(transparency_30pct)
        transparency_action_group.addAction(transparency_30pct)
        transparency_40pct = QtGui.QAction("40 %", self)
        transparency_40pct.setCheckable(True)
        transparency_sub_menu.addAction(transparency_40pct)
        transparency_action_group.addAction(transparency_40pct)
        transparency_50pct = QtGui.QAction("50 %", self)
        transparency_50pct.setCheckable(True)
        transparency_sub_menu.addAction(transparency_50pct)
        transparency_action_group.addAction(transparency_50pct)
        transparency_action_group.triggered.connect(self.on_transparency_action_group)

        always_on_top_action = QtGui.QAction(AppIcon("paperclip"),"&Always on top", self)
        always_on_top_action.setCheckable(True)
        always_on_top_action.triggered.connect(self.on_always_on_top_action)

        window_menu.addAction(always_on_top_action)
        window_menu.addSeparator()
        window_menu.addAction(transparency_action)

        #### help ###
        help_menu = menubar.addMenu("&Help")
        help_action = QtGui.QAction(AppIcon("help"), '&Help...', self)
        help_action.triggered.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(u"http://pastebeam.com/help/desktop")))
        help_menu.addAction(help_action)
        help_menu.addSeparator()
        about_action = QtGui.QAction(AppIcon("about"), '&About', self)
        about_action.triggered.connect(lambda: AboutDialog.show_(self))
        help_menu.addAction(about_action)

        self.menu_lockables = [lockout_action, edit_menu, view_menu]

    def on_view_menu_about_to_show(self):
        view_menu_actions = filter(lambda a: a.text(), self.view_menu.actions())  # get rid of separators
        old_filter_by_name_actions = view_menu_actions[3:]
        old_filter_by_name_texts = set(map(lambda each: each.text(), old_filter_by_name_actions))
        new_filter_by_name_texts = set(self.panel_tab_widget.get_all_sender_or_device_names())
        old_action_texts_to_remove = old_filter_by_name_texts.difference(new_filter_by_name_texts)  # old_filter_by_name_texts difference with new_filter_by_name_texts
        new_action_texts_to_add = sorted(new_filter_by_name_texts.difference(old_filter_by_name_texts))
        for action in old_filter_by_name_actions:
            if action.text() in old_action_texts_to_remove:
                self.view_menu.removeAction(action)
                self.view_action_group.removeAction(action)

        for each_new_text in new_action_texts_to_add:
            make_new_action = True
            for each_action in old_filter_by_name_actions:
                if each_action.text() == each_new_text:
                    make_new_action = False
                    break
            if make_new_action:
                new_filter_action = QtGui.QAction(each_new_text, self)
                new_filter_action.setCheckable(True)
                new_filter_action.setChecked(True)
            else:
                new_filter_action = each_action

            self.view_menu.addAction(new_filter_action)
            self.view_action_group.addAction(new_filter_action)

    def on_always_on_top_action(self, checked):
        if checked:  # http://stackoverflow.com/questions/1925015/pyqt-always-on-top
            flag = self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
        else:
            flag = self.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint  # http://www.qtcentre.org/threads/5730-Changing-AlwaysOnTop-window-flag
        self.setWindowFlags(flag)
        self.tray_icon.restore()  # hides for no fucking reason, so restore

    def on_transparency_action_group(self, transparency_action):
        transparency_action_text = unicode(transparency_action.text())
        opacity_percent_string = transparency_action_text.split(" ")[0]
        if opacity_percent_string == "Disabled":
            opacity_percent = 0
        else:
            opacity_percent = float(opacity_percent_string)/100.0
        transparency_percent = 1.0 - opacity_percent
        self.setWindowOpacity(transparency_percent)

    def init_status_bar(self):

        self.sbar = sb = self.statusBar()

        self.status_lbl = lbl = QtGui.QLabel("")

        sb.addPermanentWidget(lbl)

        self.status_icn = icn = QtGui.QLabel("")

        sb.addPermanentWidget(icn)

        self.on_set_status_slot(("Connecting", "connect"))

    def on_set_status_slot(self, msg_icn):
        msg,icn = msg_icn
        self.status_lbl.setText(views.status_label.format(msg=msg))

        pmap = QtGui.QPixmap("images/{icn}".format(icn=icn))
        pmap = pmap.scaledToWidth(self.px_to_dp(16), QtCore.Qt.SmoothTransformation) #antialiasing http://stackoverflow.com/questions/7623631/qt-antialiasing-png-resize
        self.status_icn.setPixmap(pmap)

        #events process once every x milliseconds, this forces them to process... or we can use repaint isntead
        QtGui.qApp.processEvents()  # YIELDS TO MAINLOOP # SIMILAR TO WX.YIELD # http://stackoverflow.com/questions/12410433/forcing-the-qt-gui-to-update-before-entering-a-separate-function  # http://stackoverflow.com/questions/4510712/qlabel-settext-not-displaying-text-immediately-before-running-other-method #the gui gets blocked, especially with file operations. DOCS: Processes all pending events for the calling thread according to the specified flags until there are no more events to process. You can call this function occasionally when your program is busy performing a long operation (e.g. copying a file).

    def init_tray_icon(self):
        self.tray_icon = TrayIcon(self)
        self.tray_icon.show()

    def px_to_dp(self, px):
        #LOG.info(dpi)
        dpi = self.desktop.logicalDpiX()
        dp = px*dpi/72.0
        #LOG.info(dp)
        return dp