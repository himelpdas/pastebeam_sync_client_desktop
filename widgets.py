from functions import *
import views


class LockoutWidget(QtGui.QWidget):

    def __init__(self, main, *args, **kwargs):
        self.main = main
        self.stacked_widget = main.stacked_widget

        super(self.__class__, self).__init__(*args, **kwargs)

        self.lockout_pin = QtGui.QLineEdit()
        self.do_layout()

    def do_layout(self):

        self.lockout_pin.setAlignment(
            QtCore.Qt.AlignHCenter)  # http://www.codeprogress.com/cpp/libraries/qt/QLineEditCenterText.php#.VcnX9M7RtyN
        # self.lockout_pin.setValidator(QtGui.QIntValidator(0, 9999)) #OLD# http://doc.qt.io/qt-4.8/qlineedit.html#inputMask-prop
        # self.lockout_pin.setMaxLength(4) #still need it despite setValidator or else you can keep typing
        self.lockout_pin.setEchoMode(
            QtGui.QLineEdit.Password)  # hide with bullets #http://stackoverflow.com/questions/4663207/masking-qlineedit-text
        self.lockout_pin.setStatusTip("Type your account password to unlock.")
        self.lockout_pin.textEdited.connect(self.on_lockout_pin_typed_slot)

        get_in_label = QtGui.QLabel("<a href='#'>Can't get in?</a>")
        get_in_label.setAlignment(QtCore.Qt.AlignCenter)

        lines_vbox = QtGui.QVBoxLayout()
        lines_vbox.addStretch(1)
        lines_vbox.addWidget(self.lockout_pin)
        lines_vbox.addWidget(get_in_label)
        lines_vbox.addStretch(1)

        lockout_hbox = QtGui.QHBoxLayout()
        lockout_hbox.addStretch(1)
        lockout_hbox.addLayout(lines_vbox)
        lockout_hbox.addStretch(1)

        lockout_vbox = QtGui.QVBoxLayout()
        lockout_vbox.addLayout(lockout_hbox)

        self.setLayout(lockout_vbox)
        self.stacked_widget.addWidget(self)

    def on_lockout_pin_typed_slot(self, written):
        try:
            login = settings.account.get("password")
        except KeyError:
            pass  # no password was set yet
        else:
            if login != written:
                return

        self.stacked_widget.switch_to_main_widget()
        self.lockout_pin.clear()

        for each in self.main.menu_lockables:
            each.setDisabled(False)

        settings.is_locked = False


    def on_show_lockout_slot(self):
        for each in self.main.menu_lockables:
            each.setDisabled(True)

        settings.is_locked = True

        self.stacked_widget.switch_to_lockout_widget()


class OkCancelWidgetMixin(object):
    def do_ok_cancel_widget(self):
        ok_button = QtGui.QPushButton("Ok")
        ok_button.clicked.connect(self.on_ok_button_clicked_slot)
        cancel_button = QtGui.QPushButton("Cancel")
        cancel_button.clicked.connect(self.on_cancel_button_clicked_slot)
        ok_cancel_hbox = QtGui.QHBoxLayout()
        ok_cancel_hbox.addStretch(1)
        ok_cancel_hbox.addWidget(ok_button)
        ok_cancel_hbox.addWidget(cancel_button)
        self.ok_cancel_widget = QtGui.QWidget()
        self.ok_cancel_widget.setLayout(ok_cancel_hbox)

    def center_to_parent(self):
        # http://stackoverflow.com/questions/18302025/derrived-widget-not-centered-on-parent-when-shown-as-dialog
        move_location = self.main.frameGeometry().topLeft() + self.main.rect().center() - self.rect().center()
        self.move(move_location)

    def on_ok_button_clicked_slot(self):
        self.done(1)

    def on_cancel_button_clicked_slot(self):
        self.done(0)


class SettingsDialog(QtGui.QDialog, OkCancelWidgetMixin):  # http://www.qtcentre.org/threads/37058-modal-QWidget

    @classmethod
    def show(cls, parent):  # THE CLASS ITSELF IS AN OBJECT WITH ITS OWN NAMESPACE, AND CALLING THE CLASS RETURNS (INSTANTIATES) A NEW INSTANCE OBJECT HELD IN THE CLASSES NAMESPACE
        cls(parent)

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.main = args[0]
        self.setWindowTitle("Edit Settings")
        self.do_account_widget()
        self.do_preferences_widget()
        self.do_tab_widget()
        self.do_ok_cancel_widget()
        self.do_settings_layout()
        self.setLayout(self.settings_layout)

        QtCore.QTimer.singleShot(10, self.center_to_parent)  # not truly centered without the timer, let the dialog load up first
        self.exec_()

    def do_account_widget(self):
        try:
            account = settings.account
            email = account.get("email")
            password = account.get("password")
        except KeyError:
            email = ""
            password = ""

        email_hbox = QtGui.QHBoxLayout()
        email_label = QtGui.QLabel("Email:")
        self.email_line = QtGui.QLineEdit(email)
        email_hbox.addWidget(email_label)
        email_hbox.addWidget(self.email_line)
        email_widget = QtGui.QWidget()
        email_widget.setLayout(email_hbox)

        password_hbox = QtGui.QHBoxLayout()
        password_label = QtGui.QLabel("Password:")
        self.password_line = QtGui.QLineEdit(password)
        self.password_line.setEchoMode(QtGui.QLineEdit.Password)
        password_hbox.addWidget(password_label)
        password_hbox.addWidget(self.password_line)
        password_widget = QtGui.QWidget()
        password_widget.setLayout(password_hbox)

        register_link = QtGui.QLabel("<a href='#'>Register</a>")
        seperator = QtGui.QLabel("|")
        forgot_link = QtGui.QLabel("<a href='#'>Reset or change password</a>")
        links_hbox = QtGui.QHBoxLayout()
        links_hbox.addWidget(register_link)
        links_hbox.addWidget(seperator)
        links_hbox.addWidget(forgot_link)
        links_hbox.setAlignment(QtCore.Qt.AlignRight)
        links_widget = QtGui.QWidget()
        links_widget.setLayout(links_hbox)

        account_vbox = QtGui.QVBoxLayout()
        account_vbox.addWidget(email_widget)
        account_vbox.addWidget(password_widget)
        account_vbox.addWidget(links_widget)

        self.account_widget = QtGui.QWidget()
        self.account_widget.setLayout(account_vbox)

    def do_preferences_widget(self):
        device_name_label = QtGui.QLabel("Device Name:")
        self.device_name_line = QtGui.QLineEdit()
        try:
            device_name = settings.device_name
        except KeyError:
            device_name = host_name
        self.device_name_line.setText(device_name)
        device_name_hbox = QtGui.QHBoxLayout()
        device_name_hbox.addWidget(device_name_label)
        device_name_hbox.addWidget(self.device_name_line)
        device_name_widget = QtGui.QWidget()
        device_name_widget.setLayout(device_name_hbox)

        try:
            enable_universal_clipboard = settings.enable_universal_clipboard
        except KeyError:
            enable_universal_clipboard = True

        sync_label = QtGui.QLabel("Enable universal copy and paste")
        self.sync_check = sync_check = QtGui.QCheckBox()
        sync_check.setChecked(enable_universal_clipboard)
        sync_hbox = QtGui.QHBoxLayout()
        sync_hbox.addWidget(sync_label)
        sync_hbox.addWidget(sync_check)
        sync_widget = QtGui.QWidget()
        sync_widget.setLayout(sync_hbox)

        run_label = QtGui.QLabel("Run PasteBeam on system startup")
        run_check = QtGui.QCheckBox()
        run_hbox = QtGui.QHBoxLayout()
        run_hbox.addWidget(run_label)
        run_hbox.addWidget(run_check)
        run_widget = QtGui.QWidget()
        run_widget.setLayout(run_hbox)

        try:
            enable_item_double_click = settings.enable_item_double_click
        except KeyError:
            enable_item_double_click = True
        
        dclick_label = QtGui.QLabel("Double-click an item to copy")
        self.dclick_check = QtGui.QCheckBox()
        self.dclick_check.setChecked(enable_item_double_click)
        dclick_hbox = QtGui.QHBoxLayout()
        dclick_hbox.addWidget(dclick_label)
        dclick_hbox.addWidget(self.dclick_check)
        dclick_widget = QtGui.QWidget()
        dclick_widget.setLayout(dclick_hbox)

        master_vbox = QtGui.QVBoxLayout()
        master_vbox.addWidget(device_name_widget)
        master_vbox.addWidget(sync_widget)
        master_vbox.addWidget(run_widget)
        master_vbox.addWidget(dclick_widget)

        self.system_widget = QtGui.QWidget()
        self.system_widget.setLayout(master_vbox)

    def set_device_name_to_keyring(self):
        settings.device_name = unicode(self.device_name_line.text()).strip() or host_name  # strip removes trailing spaces

    def do_tab_widget(self):
        self.tab_widget = QtGui.QTabWidget()
        self.tab_widget.addTab(self.account_widget, AppIcon("account"), "Account")
        self.tab_widget.addTab(self.system_widget, AppIcon("controls"), "Preferences")

    def do_settings_layout(self):
        self.settings_layout = QtGui.QVBoxLayout()
        self.settings_layout.addWidget(self.tab_widget)
        self.settings_layout.addWidget(self.ok_cancel_widget)

    def on_ok_button_clicked_slot(self):
        self.set_account_to_keyring()
        self.set_device_name_to_keyring()
        self.set_checkables_to_keyring()
        super(self.__class__, self).on_ok_button_clicked_slot()

    def on_cancel_button_clicked_slot(self):
        if not self.main.ws_worker.KEEP_RUNNING:
            self.main.on_set_status_slot((views.not_connected_msg, "bad"))
        super(self.__class__, self).on_cancel_button_clicked_slot()

    def set_checkables_to_keyring(self):
        settings.enable_universal_clipboard = self.sync_check.isChecked()
        settings.enable_item_double_click = self.dclick_check.isChecked()

    def set_account_to_keyring(self):

        typed_email = unicode(self.email_line.text())
        typed_password = unicode(self.password_line.text())

        if (typed_email and typed_password):  # TODO STRONGER VALIDATION HERE

            settings.account = {
                "email": typed_email,
                "password": typed_password,
            }

        #if hasattr(self.main, "ws_worker") and hasattr(self.main.ws_worker, "WSOCK"):  # maybe not initialized yet
        if self.main.ws_worker.WSOCK: #can be None if closed
            self.main.ws_worker.WSOCK.close()
        self.main.ws_worker.KEEP_RUNNING = 1


class WaitForSignalDialogMixin(object):
    def show_wait_for_signal_dialog(self, question, data_dict, error_msg, success_msg=False):
        "shows an unclosable dialog until closeWaitDialogSignalForMain"
        self.main.outgoing_signal_for_worker.emit(
            dict(
                question=question,
                data=data_dict
            )
        )
        WaitForSignalDialog(self,
                            "please wait")  # EXECUTION FREEZfES HERE so WaitForSignalDialog().done(1) will not work, use signals instead
        if not self.success["success"]:
            QtGui.QMessageBox.warning(
                # QtGui.QMessageBox.critical #http://stackoverflow.com/questions/20841081/how-to-pop-up-a-message-window-in-qt
                self,
                "Error",
                "%s!<br><b>Reason:</b> <i>%s</i>" % (error_msg.capitalize(), self.success["reason"])
            )
        elif success_msg:
            QtGui.QMessageBox.information(  # http://stackoverflow.com/questions/20841081/how-to-pop-up-a-message-window-in-qt
                self,
                "Success",
                "%s!" % success_msg.capitalize()
            )


class ContactsDialog(QtGui.QDialog, OkCancelWidgetMixin, WaitForSignalDialogMixin):
    @classmethod
    def show(cls, parent):
        if parent.ws_worker.KEEP_RUNNING:
            cls(parent)
        else:
            QtGui.QMessageBox.warning(  # http://stackoverflow.com/questions/20841081/how-to-pop-up-a-message-window-in-qt
                parent, # so it doesn't get garbage collected
                "Warning",
                views.not_connected_msg
            )
            parent.on_set_status_slot((views.not_connected_msg, "bad"))


    def __init__(self, parent):
        super(self.__class__, self).__init__(parent)

        self.main = parent
        self.contacts_list = []

        self.setWindowTitle('Edit Contacts')
        self.do_add_contact_widget()
        self.do_list_widget()
        self.do_ok_cancel_widget()
        self.do_contacts_widget()

        # self.bindEvents()

        self.setLayout(self.contacts_layout)
        self.resize_min_window_size_for_list_widget()

        self.do_pre_exec_get_contacts_list()
        if self.success:
            QtCore.QTimer.singleShot(10, self.center_to_parent)
            self.exec_()

    def do_pre_exec_get_contacts_list(self):
        self.show_wait_for_signal_dialog("Contacts?", {"contacts_list": None}, "could not get contacts list",
                                     success_msg=False)

        if self.success["success"]:
            self.contacts_list = self.success["contacts"]
            for each_email in self.contacts_list:
                self.list_widget.addItem(each_email)

            self.list_widget.sortItems()

    def on_friend_request_button_clicked_slot(self):
        email = self.email_line.text()
        if not validators.email(email):
            QtGui.QMessageBox.warning(  # http://stackoverflow.com/questions/20841081/how-to-pop-up-a-message-window-in-qt
                self,
                "Warning",
                "Invalid email address!"
            )
            return

        self.show_wait_for_signal_dialog("Invite?", {"email": email}, "failed to send friend invite",
                                     success_msg="friend request sent")

    def on_friend_request_received_slot(self):
        self.friend_request_wait_dialog.done(1)
        QtGui.QMessageBox.information(self, "Success", "Friend request sent!")

    def currentItems(self):
        """http://stackoverflow.com/questions/4629584/pyqt4-how-do-you-iterate-all-items-in-a-qlistwidget"""
        items = []
        for index in xrange(self.list_widget.count()):
            items.append(self.list_widget.item(index).text())
        return items

    def on_ok_button_clicked_slot(self):
        # guaranteed thread safe as this window wouldn't even appear without self.contacts_list
        current_items = self.currentItems()

        if set(current_items) == set(self.contacts_list):  # no need to contact server
            super(self.__class__, self).on_ok_button_clicked_slot()
            return

        self.show_wait_for_signal_dialog("Contacts?", {"contacts_list": current_items}, "failed to save contacts to server",
                                     success_msg="contacts saved to server")

        if self.success["success"]:
            super(self.__class__, self).on_ok_button_clicked_slot()

    def resize_min_window_size_for_list_widget(self):
        default_height = self.sizeHint().height()
        new_height = default_height * 1.15
        self.setMinimumHeight(new_height)

    def do_add_contact_widget(self):
        email_label = QtGui.QLabel("Friend's Email:")
        self.email_line = email_line = QtGui.QLineEdit()

        friend_request_button = QtGui.QPushButton("Send friend invite")
        friend_request_button.clicked.connect(self.on_friend_request_button_clicked_slot)

        lines_vbox = QtGui.QVBoxLayout()
        lines_vbox.addWidget(email_label)
        lines_vbox.addWidget(email_line)
        lines_vbox.addWidget(friend_request_button)

        self.add_user_widget = QtGui.QWidget()
        self.add_user_widget.setLayout(lines_vbox)

    def do_list_widget(self):
        contacts_list_label = QtGui.QLabel("Friends list:")
        self.list_widget = QtGui.QListWidget()
        # for letter in range(65,91):
        #    self.contacts_list.addItem("%s@yahoo.com"%chr(letter))
        contacts_list_delete = QtGui.QPushButton("Delete friend")
        contacts_list_delete.clicked.connect(self.onDeleteClickedSlot)
        contacts_list_layout = QtGui.QVBoxLayout()
        contacts_list_layout.addWidget(contacts_list_label)
        contacts_list_layout.addWidget(self.list_widget)
        contacts_list_layout.addWidget(contacts_list_delete)
        self.contacts_list_widget = QtGui.QListWidget()
        self.contacts_list_widget.setLayout(contacts_list_layout)

    def do_contacts_widget(self):
        # how_label = QtGui.QLabel("For your security, clips from other PasteBeam users are automatically blocked without notice. To unblock a friend, add his email to your contacts list here. Likewise, for him to receive your clips, he must add your login email to his own contacts list.")
        # how_label.setWordWrap(True)

        self.contacts_layout = QtGui.QVBoxLayout()
        # self.contacts_layout.addWidget(how_label)
        self.contacts_layout.addWidget(self.add_user_widget)
        self.contacts_layout.addWidget(self.contacts_list_widget)
        self.contacts_layout.addWidget(self.ok_cancel_widget)

    def onDeleteClickedSlot(self):
        current_row = self.list_widget.currentRow()
        self.list_widget.takeItem(current_row)


class FaderWidget(QtGui.QWidget):
    def __init__(self, old_widget, new_widget, duration=333):
        QtGui.QWidget.__init__(self, new_widget)

        self.old_pixmap = QtGui.QPixmap(new_widget.size())
        old_widget.render(self.old_pixmap)
        self.pixmap_opacity = 1.0

        self.timeline = QtCore.QTimeLine()
        self.timeline.valueChanged.connect(self.animate)
        self.timeline.finished.connect(self.close)
        self.timeline.setDuration(duration)
        self.timeline.start()

        self.resize(new_widget.size())
        self.show()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setOpacity(self.pixmap_opacity)
        painter.drawPixmap(0, 0, self.old_pixmap)
        painter.end()

    def animate(self, value):
        self.pixmap_opacity = 1.0 - value
        self.repaint()


class StackedWidgetFader(QtGui.QStackedWidget):
    def __init__(self, parent):
        super(StackedWidgetFader, self).__init__(parent)
        self.duration = 444

    def setCurrentIndex(self, index):
        self.fader_widget = FaderWidget(self.currentWidget(), self.widget(index),
                                        self.duration)  # does not work as a mixin, as self.currentWidget needs to be a subclass of QtGui.QStackedWidget
        QtGui.QStackedWidget.setCurrentIndex(self, index)

    def setFadeDuration(self, duration):
        self.duration = duration


class CommonListWidget(QtGui.QListWidget, WaitForSignalDialogMixin):
    def __init__(self, parent=None):
        super(CommonListWidget, self).__init__(parent)
        self.parent = parent
        self.main = parent.main
        self.setVerticalScrollMode(
            QtGui.QAbstractItemView.ScrollPerPixel)  # http://stackoverflow.com/questions/2016323/qt4-is-it-possible-to-make-a-qlistview-scroll-smoothly

        self.itemPressed.connect(self.on_item_pressed_slot)  # ITEM CLICK DOES NOT WORK USE PRESSED FUCK!!

    def get_items(self):
        # http://stackoverflow.com/questions/12087715/pyqt4-get-list-of-all-labels-in-qlistwidget
        for index in xrange(self.count()):
            item = self.item(index) #RACE? COULD BE NONE!
            if item:
                 yield item

    def get_matching_item_for_data_id(self, find_data_id):
        for each_item in self.get_items():
            each_item_data_id = each_item.get_data_id()
            if each_item_data_id == find_data_id:
                return each_item

    def get_matching_items_for_hash(self, find_hash):
        for each_item in self.get_items():  # http://www.qtcentre.org/threads/32716-How-to-iterate-through-QListWidget-items
            each_item_hash = each_item.get_data_hash()
            if find_hash == each_item_hash:
                yield each_item

    def resizeEvent(self, event):
        super(CommonListWidget, self).resizeEvent(event)
        # do something on resize!

    def on_item_pressed_slot(self, i):
        "So that any click of an item will enable all context items"
        self.parent.on_tab_changed_slot(self.index)  # hide notification icon in tab when clicking on an item

    def scroll_to_top(self):
        #move the scrollbar to top
        list_widget_scrollbar = self.verticalScrollBar() #http://stackoverflow.com/questions/8698174/how-to-control-the-scroll-bar-with-qlistwidget
        list_widget_scrollbar.setValue(0)

    def do_common(self):

        self.do_styling()

        self.do_uncommon()  # do uncommon here

        self.itemDoubleClicked.connect(self.on_item_double_click_slot)  # textChanged() is emited whenever the contents of the widget changes (even if its from the app itself) whereas textEdited() is emited only when the user changes the text using mouse and keyboard (so it is not emitted when you call QtGui.QLineEdit::setText()).

    def do_styling(self):
        self.setIconSize(
            self.parent.icon_size)  # http://www.qtcentre.org/threads/8733-Size-of-an-Icon #http://nullege.com/codes/search/PySide.QtGui.QListWidget.setIconSize
        self.setAlternatingRowColors(
            True)  # http://stackoverflow.com/questions/23213929/qt-qlistwidget-item-with-alternating-colors

    def get_clip_data_by_current_row(self):
        current_row = self.currentRow()
        current_item = self.currentItem()
        current_item_data = current_item.get_data()  # http://stackoverflow.com/questions/25452125/is-it-possible-to-add-a-hidden-value-to-every-item-of-qlistwidget
        return current_row, current_item_data

    def on_item_double_click_slot(self, double_clicked_item):

        # current_item = self.item(0)
        # current_clip = json.loads(current_item.data(QtCore.Qt.UserRole))

        double_clicked_data = double_clicked_item.get_data()

        hash_, prev = double_clicked_data["hash"], self.main.previous_hash

        if hash_ == prev:
            self.main.on_set_status_slot(("Already copied", "warn"))
            return

        # container name is already in double_clicked_clip

        # double_clicked_clip = self.convertToDeviceClip(double_clicked_clip)

        # _id is in data, but not on_clip_change since that's created from scratch

        self.main.on_set_new_clip_slot(dict(new_clip = double_clicked_data, block_clip_change_detection = False))
        self.main.panel_tab_widget.toggle_is_in_clipboard_label("clear all labels")  # since the clipboard will change after a double-click, just remove all the "In your clipboard!" labels. Note, if decryption fails, then labels will stay erased.

        # self.previous_hash = hash #or else on_clip_change_slot will react and a duplicate new list item will occur.


class NotificationListWidget(CommonListWidget):
    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.index = 3
        self.do_common()

    def do_uncommon(self):
        pass


class StarListWidget(CommonListWidget):
    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.index = 1
        self.do_common()

    def do_uncommon(self):
        pass


class MainListWidget(CommonListWidget):
    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.index = 0
        self.do_common()

    def do_uncommon(self):
        pass


class FriendListWidget(CommonListWidget):
    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.index = 2
        self.do_common()

    def do_uncommon(self):
        pass


class PanelTabWidget(QtGui.QTabWidget):
    def __init__(self, icon_size, parent):
        super(self.__class__, self).__init__(parent)
        self.main = parent
        self.icon_size = icon_size
        self.do_search_widget()
        self.do_panels()
        self.add_panels()

        self.currentChanged.connect(self.on_tab_changed_slot)

    def get_list_widget_from_clip_data(self, clip):
        list_widget = None
        if clip["system"] == "starred":
            list_widget = self.star_list_widget
            # new_icon_tab = 1
        elif clip["system"] == "notification":
            list_widget = self.notification_list_widget
            # new_icon_tab = 3
        elif clip["system"] == "main":
            list_widget = self.main_list_widget
            # new_icon_tab = 0
        elif clip["system"] == "share":
            list_widget = self.friend_list_widget
            # new_icon_tab = 2
        return list_widget

    def on_tab_changed_slot(self, index):
        if index == 0:
            self.setTabIcon(0, QtGui.QIcon("images/devices.png"))
        if index == 1:
            self.setTabIcon(1, QtGui.QIcon("images/star.png"))
        if index == 2:
            self.setTabIcon(2, QtGui.QIcon("images/friends.png"))
        if index == 3:
            self.setTabIcon(3, QtGui.QIcon("images/bulb.png"))

    def onChangeTabIconSlot(self, tabs_affected):
        if "starred" in tabs_affected:
            new_icon_tab = 1
        elif "notification" in tabs_affected:
            new_icon_tab = 3
        elif "main" in tabs_affected:
            new_icon_tab = 0
        elif "share" in tabs_affected:
            new_icon_tab = 2

        self.setTabIcon(new_icon_tab, QtGui.QIcon("images/new.png"))

    def do_search_widget(self):
        self.search = QtGui.QLineEdit()
        self.search.textEdited.connect(self.on_search_edited_slot)
        search_tip = "Search through your items (preview text only)."
        self.search.setStatusTip(search_tip)
        self.search.setPlaceholderText("Filter...")

    def on_change_view_menu(self, action):
        actions = self.main.view_menu.actions()
        label_to_clip_type = {
            "Text/Html":["text", "html"],
            "Screenshots": "screenshot",
            "Files":"files",
        }
        activate_clip_types = []
        for each_action in actions:
            if each_action.isChecked():
                action_label = each_action.text()
                activate_clip_types.append(label_to_clip_type[action_label])
        for list_widget in self.panels[:-1]:
            for item in list_widget.get_items():
                activate = False
                for clip_type in activate_clip_types:
                    item_data = item.get_data()
                    if item_data["clip_type"] in clip_type:
                        activate = True
                if activate:
                    item.setHidden(False)
                else:
                    item.setHidden(True)

    def on_search_edited_slot(self, written):
        for list_widget in self.panels:
            # items = [] #http://stackoverflow.com/questions/12087715/pyqt4-get-list-of-all-labels-in-qlistwidget
            # for index in xrange(list_widget.count()):
            #    items.append(list_widget.item(index))

            if "PyQt4" in QtGui.__name__:
                written = unicode(written)

            is_blank = not bool(written)  # unhide when written is blank

            for item in list_widget.get_items():
                if is_blank:
                    item.setHidden(False)  # unhide all
                else:
                    item_data = item.get_data()

                    written = written.upper()
                    any_match = False
                    simple_search = ["text", "html", "confirmation", "invite"]
                    if item_data["clip_type"] == "files":
                        for each_display in item_data["clip_display"]:
                            # print each_display
                            if written in each_display.replace("._folder", "").upper():
                                any_match = True
                    elif item_data["clip_type"] in simple_search and written in item_data["clip_display"].upper():  # make compatible with files clip display #TODO only search in searchable html class
                        any_match = True
                    elif item_data.get("note") and written in item_data.get("note").upper():
                        any_match = True

                    if any_match:
                        item.setHidden(False)
                    else:
                        item.setHidden(True)

    def do_panels(self):

        self.main_list_widget = MainListWidget(self)

        self.star_list_widget = StarListWidget(self)

        self.friend_list_widget = FriendListWidget(self)

        self.notification_list_widget = NotificationListWidget(self)

        self.panels = [self.main_list_widget, self.star_list_widget, self.friend_list_widget, self.notification_list_widget]
        # devices star friends

    def add_panels(self):
        self.addTab(self.main_list_widget, QtGui.QIcon("images/devices"), "Devices")
        self.addTab(self.star_list_widget, QtGui.QIcon("images/star"), "Bookmarks")
        self.addTab(self.friend_list_widget, QtGui.QIcon("images/friends"), "Friends")
        # self.addTab(QtGui.QWidget(), QtGui.QIcon("images/bulb"), "Notifications")
        self.addTab(self.notification_list_widget, AppIcon("bulb"), "Notifications")
        self.setCornerWidget(self.search)

    def on_incoming_delete(self, location):
        item_to_delete = self.get_matching_item_for_data_id(location)
        if item_to_delete:
            list_widget = self.get_list_widget_from_clip_data(item_to_delete.get_data())
            row = list_widget.row(item_to_delete)  # even though there's no previous matching hash for new item, there may be more than max_free_limit clips, that need deleting
            list_widget.takeItem(row)
            list_widget.scroll_to_top()

    def clearAllLists(self):
        for each in self.panels:
            each.clear()

    def get_matching_containers_for_hash(self, find_hash):
        """SEARCHES ALL LIST_WIDGETS
        prevent the recreating of the container, if it already exists in server"""
        for list_widget in self.panels[:-2]:  #  # DO NOT reuse shared clips, as they were encrypted with a random key, not user's password. Not reusing wil force the system to re-encrypt the container with user's password
            for each_item in list_widget.get_matching_items_for_hash(find_hash):  # http://www.qtcentre.org/threads/32716-How-to-iterate-through-QListWidget-items
                each_item_data = each_item.get_data()
                yield each_item_data.get("container_name") # use yield instead of return if we just want to stop at the first match


    def get_matching_item_for_data_id(self, find_data_id):
        for list_widget in self.panels:
            matched_item = list_widget.get_matching_item_for_data_id(find_data_id)
            if matched_item:
                return matched_item


    def toggle_is_in_clipboard_label(self, compare_hash):
        for list_widget in self.panels[:-1]:
            for each_item in list_widget.get_items():
                each_widget = list_widget.itemWidget(each_item)
                each_widget.toggle_is_in_clipboard_label(compare_hash)

class LockoutStackedWidget(StackedWidgetFader):
    """lets you swap between 2 main widgets"""
    # https://wiki.python.org/moin/PyQt/Fading%20Between%20Widgets
    # http://www.qtcentre.org/threads/30830-setCentralWidget()-without-deleting-prev-widget
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)  # it's better to use super method instead of explicitly calling the parent class, because the former allows to add another parent and "push up" the previous parent up the ladder without making any changes to the code here

    def switch_to_main_widget(self):
        self.setCurrentIndex(0)

    def switch_to_lockout_widget(self):
        self.setCurrentIndex(1)


class WaitForSignalDialog(QtGui.QDialog):
    @classmethod
    def show(cls, parent, label):
        cls(parent, label)

    def __init__(self, parent, label="please wait"):
        self.main = parent.main
        super(self.__class__, self).__init__(self.main,
                                             QtCore.Qt.CustomizeWindowHint)  # remove the X button https://forum.qt.io/topic/4108/how-to-hide-the-dialog-window-close-button/6
        self.parent = parent
        self.parent.success = False  # always set false since self.success is shared
        self.label = label
        self.do_layout()
        self.setLayout(self.layout)
        self.bindEvents()
        self.exec_()

    def do_layout(self):
        wait_label = QtGui.QLabel("<h1>%s...</h1>" % self.label.capitalize())
        self.layout = QtGui.QVBoxLayout()
        self.layout.addWidget(wait_label)

    def bindEvents(self):
        self.main.ws_worker.closeWaitDialogSignalForMain.connect(self.on_close_wait_dialog_slot)

    def on_close_wait_dialog_slot(self, result):
        self.parent.success = result
        try:
            self.main.update_contacts_list_signal.emit(sorted(result["contacts"]))
        except KeyError:
            pass
        self.done(1)


class QTextBrowserForFancyListItemWidget(QtGui.QTextBrowser):
    def __init__(self, list_widget, item, content, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.list_widget = list_widget
        self.item = item
        self.content = content
        self.viewport().setAutoFillBackground(
            False)  # http://www.qtcentre.org/threads/12148-how-QTextEdit-transparent-to-his-parent-window
        self.setText(content)
        self.setReadOnly(True)
        self.setOpenExternalLinks(True)

    def mousePressEvent(self, event):
        super(self.__class__, self).mousePressEvent(event)
        self.list_widget.setCurrentItem(self.item)

    def wheelEvent(self, event):  # http://stackoverflow.com/questions/3241830/qt-how-to-disable-mouse-scrolling-of-qcombobox
        """ignore mouse scrolling here, and leave it to the parent listwidget"""
        event.ignore()

class FancyListItem(QtGui.QListWidgetItem):
    """cannot override data and setData directly, due to unknown behavior. Using horizontal methods instead."""
    def __init__(self):
        super(self.__class__, self).__init__()

    def set_data(self, clip_data, *args, **kwargs):
        id_and_clip_data = "{_id}|{hash}|{data}".format(_id=str(clip_data["_id"]), hash=clip_data["hash"], data=json.dumps(clip_data))  # use bson util's json.dumps or else clip data (especially BSON's Binary)will be truncated by setData

        # json.dumps or else clip data (especially BSON's Binary)will be truncated by setData
        self.setData(QtCore.Qt.UserRole, id_and_clip_data)

    def get_item_data(func):
        def closure(self):
            if "PyQt4" in QtGui.__name__:
                variant = self.data(QtCore.Qt.UserRole)
                self.id_and_clip_data = unicode(variant.toPyObject())
            else:
                self.id_and_clip_data = self.data(QtCore.Qt.UserRole)
            return func(self)
        return closure

    @get_item_data
    def get_data(self):
        raw_data = self.id_and_clip_data.split('|', 2)[-1]  # http://stackoverflow.com/questions/6903557/splitting-on-first-occurrence
        data = json.loads(raw_data)
        return data

    @get_item_data
    def get_data_id(self):
        _id = self.id_and_clip_data.split('|', 2)[0]  # http://stackoverflow.com/questions/6903557/splitting-on-first-occurrence
        return _id

    @get_item_data
    def get_data_hash(self):
        _id = self.id_and_clip_data.split('|', 2)[1]  # http://stackoverflow.com/questions/6903557/splitting-on-first-occurrence
        return _id



class FancyListItemWidget(QtGui.QWidget, WaitForSignalDialogMixin):
    host_colors = sorted(
        ["#FF4848", "#800080", "#5757FF", "#1FCB4A", "#59955C", "#9D9D00", "#62A9FF", "#06DCFB", "#9669FE", "#23819C",
         "#2966B8", "#3923D6", "#23819C", "#FF62B0", ])  # http://www.hitmill.com/html/pastels.html
    file_icons = map(lambda file_icon: file_icon.split(".")[0].upper(), os.listdir(os.path.normpath("images/files")))

    def __init__(self, clip, item):
        super(self.__class__, self).__init__()

        self.item = item
        self.clip = clip

        self.sender = self.timestamp = self.datestamp = self.content = None

        self.list_widget = self.item.listWidget()
        self.main = self.list_widget.main

        self.copy_action = self.accept_invite_action = self.delete_action = self.share_action = self.star_action = None

        self.set_header_from_clip()

        self.item_icon = AppIcon("action")
        self.set_content_from_clip()
        
        self.do_layout()

        self.item_menu = QtGui.QMenu()
        self.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu)  # need to access menu explicitly ActionContextMenu doesn't allow this
        self.customContextMenuRequested.connect(
            self.show_context_menu)  # http://www.setnode.com/blog/right-click-context-menus-with-qt/

    def show_context_menu(self, point_where_clicked):
        self.reset_actions()
        point_where_clicked = self.mapToGlobal(point_where_clicked)
        self.item_menu.exec_(point_where_clicked)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.reset_actions()
        # self.list_widget.setCurrentItem(self.item)
        super(self.__class__, self).mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        try:
           enable_item_double_click = settings.enable_item_double_click
           if not enable_item_double_click:
               self.main.on_set_status_slot(("Item double-click is disabled in settings", "warn"))
               return
        except KeyError:
            pass

        if not self.clip["system"] == "notification":
            self.list_widget.on_item_double_click_slot(self.item)
            # super(self.__class__, self).mouseDoubleClickEvent(event)

    def reset_actions(self):
        self.clear_actions()
        self.set_actions()

    def clear_actions(self):
        self.item_menu.clear()

    def set_actions(self):

        if not self.clip["system"] == "notification":
            self.set_copy_action()
            self.set_star_action()
            self.set_share_action()

        elif self.clip["clip_type"] == "invite":
            self.set_accept_invite_action()

        self.set_delete_action()  # Put delete last

    def set_star_action(self):
        # star action
        self.star_action = star_action = QtGui.QAction(QtGui.QIcon("images/star.png"), '&Star', self)
        # self.star_action.triggered.connect(self.on_add_star_action)
        sub_menu = self.get_note_sub_menu(history_list_widget =self.main.panel_tab_widget.star_list_widget,
                                       trigger = self.on_add_star_action,
                                       parent_action = None)
        star_action.setMenu(sub_menu)
        self.item_menu.addAction(star_action)

    def get_note_sub_menu(self, history_list_widget, trigger, parent_action,
                                 placeholder="Enter a note...", max_length = 100):
        def always_close_menu_decorator(func):
            def closure():
                func()
                self.item_menu.close()
            return closure

        sub_menu = QtGui.QMenu()
        # share_sub_menu.triggered.connect(self.on_share_sub_menu_triggered_slot)
        message_subaction = QtGui.QWidgetAction(self)
        message_widget = QtGui.QLineEdit()
        message_widget.setMaxLength(max_length)

        @always_close_menu_decorator
        def on_return_pressed():
            # star_action.trigger()
            message = unicode(message_widget.text())
            trigger(message[:max_length].strip(), parent_action)

        message_widget.returnPressed.connect(on_return_pressed)
        message_widget.setPlaceholderText(placeholder)
        message_subaction.setDefaultWidget(message_widget)
        sub_menu.addAction(message_subaction)

        if history_list_widget:
            sub_menu.addSeparator()
            action_names = []
            for each_item in history_list_widget.get_items(): #self.main.panel_tab_widget.star_list_widget.get_items():
                each_item_data = each_item.get_data()
                each_item_note = each_item_data.get("note")
                if each_item_note and each_item_note not in action_names:

                    @always_close_menu_decorator
                    def on_note_history_action():
                        trigger(each_item_note, parent_action)

                    note_history_action = QtGui.QAction(each_item_note, self)
                    note_history_action.triggered.connect(on_note_history_action)
                    sub_menu.addAction(note_history_action)
                    action_names.append(each_item_note)

        return sub_menu

    def on_add_star_action(self, note, *args):
        current_item_data = self.item.get_data()
        current_item_data["note"] = note
        async_process = dict(
            question="Star?",
            data=current_item_data
        )
        self.main.outgoing_signal_for_worker.emit(async_process)

    def set_accept_invite_action(self):
        self.accept_invite_action = QtGui.QAction(QtGui.QIcon("images/ok.png"), "&Accept invite", self)
        self.accept_invite_action.triggered.connect(self.on_accept_invite_action)
        self.item_menu.addAction(self.accept_invite_action)

    def disable_accept_invite_action(self):
        self.accept_invite_action.setDisabled(True)

    def on_accept_invite_action(self):
        current_item_data = self.item.get_data()
        if not current_item_data["clip_type"] == "invite":
            return
        email = current_item_data["host_name"]

        self.show_wait_for_signal_dialog("Accept?", {"email": email}, "could not accept invitation", success_msg=False)

    def set_share_action(self):
        self.share_action = QtGui.QAction(QtGui.QIcon("images/share.png"), "S&hare", self)
        self.enable_share_action()
        self.item_menu.addAction(self.share_action)

    def on_share_sub_menu_triggered_slot(self, note, action):

        email = unicode(action.text())
        share_item_data = self.item.get_data()
        share_item_data["note"] = note

        # now get decryption keys
        clip_system = share_item_data["system"]
        if clip_system in ["main", "starred"]:
            decryption_key = settings.account.get("password")
        elif clip_system == "share":
            ciphertext = share_item_data["decryption_key"]
            decryption_key = self.main.rsa_private_key.decrypt(ciphertext) #this is set on logon guaranteed!
        elif clip_system == "notification":  # cant share notifications yet
            return

        share_item_data["recipient"] = email
        share_item_data["decryption_key"] = decryption_key  # raw, will be replaced by new decryption key before actual share
        self.main.outgoing_signal_for_worker.emit(
            {
                "question": "Share?",
                "data": share_item_data
            }
        )

    def enable_share_action(self):
        if not self.main.contacts_list:
            self.share_action.setDisabled(True)
            # todo add bubble explaining why
        else:
            self.share_action.setDisabled(False)
            share_sub_menu = QtGui.QMenu()
            #share_sub_menu.triggered.connect(self.on_share_sub_menu_triggered_slot)
            for email_addr in sorted(self.main.contacts_list):
                email_addr_action = QtGui.QAction(email_addr, self)
                sub_menu = self.get_note_sub_menu(history_list_widget=None,
                                               trigger=self.on_share_sub_menu_triggered_slot,
                                               parent_action=email_addr_action,
                                               placeholder="Enter a message...")
                email_addr_action.setMenu(sub_menu)
                share_sub_menu.addAction(email_addr_action)
            self.share_action.setMenu(share_sub_menu)

    def set_copy_action(self):
        self.copy_action = copy_action = QtGui.QAction(QtGui.QIcon("images/copy.png"), "&Copy item", self)
        copy_action.triggered.connect(self.on_copy_action_slot)
        self.item_menu.addAction(copy_action)
        separator = QtGui.QAction(self)
        separator.setSeparator(True)
        self.item_menu.addAction(separator)

    def on_copy_action_slot(self):
        self.list_widget.on_item_double_click_slot(self.item)  # listwidget_items don't have signals, so must use parent

    def set_delete_action(self):
        separator = QtGui.QAction(self)
        separator.setSeparator(True)  # http://www.qtcentre.org/threads/21838-Separator-in-context-menu
        self.delete_action = QtGui.QAction(QtGui.QIcon("images/trash.png"), '&Delete', self)  # delete.setText("Delete")
        self.delete_action.triggered.connect(self.on_delete_action)
        self.item_menu.addAction(separator)
        self.item_menu.addAction(self.delete_action)

    def on_delete_action(self):
        current_row, current_item = self.list_widget.get_clip_data_by_current_row()
        remove_id = current_item["_id"]
        async_process = dict(
            question="Delete?",
            data={"remove_id": remove_id}  # user wanted to explicitly delete clip so delete associated files
        )
        self.main.outgoing_signal_for_worker.emit(async_process)

    def set_header_from_clip(self):
        seed = hash32(self.clip["host_name"])
        reproducible_random_color = random.Random(seed).choice(self.host_colors)  # REPRODUCIBLE RANDOM COLOR FROM SEED

        datetime_stamp = datetime.datetime.fromtimestamp(self.clip["timestamp_server"])
        self.timestamp = views.header_timestamp.format(dt=datetime_stamp)
        self.datestamp = views.header_datestamp.format(dt=datetime_stamp)
        self.sender = views.header_sender.format(color=reproducible_random_color, host_name=self.clip["host_name"])

    def set_content_from_clip(self):
        if self.clip["clip_type"] == "screenshot":
            # crop and reduce pmap size to fit square icon
            # image = QtGui.QImage()
            # LOG.info(image.loadFromData(self.clip["clip_display"]["thumb"]) )
            # self.item.setIcon(QtGui.QIcon(QtGui.QPixmap(image)))
            self.item_icon = AppIcon("image")
            self.content = views.image_preview.format(
                b64 = self.clip["clip_display"]["thumb"].encode('base64'),
                **self.clip["clip_display"]["info"]
            )
            # print self.content

        elif self.clip["clip_type"] == "html":
            self.item_icon = QtGui.QIcon("images/text.png")
            self.content = self.clip["clip_display"]

        elif self.clip["clip_type"] == "text":
            self.item_icon = QtGui.QIcon("images/text.png")
            self.content = self.clip["clip_display"]

        elif self.clip["clip_type"] == "files":
            self.item_icon = QtGui.QIcon("images/files.png")
            files = []
            for each_filename in self.clip["clip_display"]:
                ext = each_filename.split(".")[-1]
                file_icon = "files/%s" % ext
                if not ext.upper() in self.file_icons:
                    file_icon = "files/_blank"
                if ext.upper() == "JPEG":
                    file_icon = "files/jpg"
                if ext == "_folder":  # get rid of the ._folder from folder._folder
                    each_filename = each_filename.split(".")[0]
                files.append(u"{icon} {file_name}".format(
                    # do NOT do "string {thing}".format(thing = u"unicode), or else unicode decode error will occur, the first string must be u"string {thing}"
                    file_name=each_filename,
                    icon=views.icon_html.format(name=file_icon, side=self.main.px_to_dp(12))
                ))

            self.content = u"<ol><li>{li}</ol>".format(li=u"<li> ".join(files))

        elif self.clip["clip_type"] == "invite":
            self.item_icon = AppIcon("me")
            self.content = self.clip["clip_display"]

        elif self.clip["clip_type"] == "confirmation":  # change to "accepted" and get updated contacts here by appending "Contacts?" to outgoing queue
            self.item_icon = AppIcon("ok") #todo change to check mark
            self.content = self.clip["clip_display"]

    def on_dropdown_clicked(self):
        self.reset_actions()
        self.dropdown_widget.setMenu(self.item_menu)
        self.dropdown_widget.showMenu()
        # dropdown_widget.addItem(QtGui.QIcon("images/copy.png"), "Copy all")

    def toggle_is_in_clipboard_label(self, compare_hash):
        if self.item_is_in_clipboard(compare_hash):
            text = views.is_in_clipboard_label
        else:
            text = ""
        self.item_is_in_clipboard_label.setText(text)

    def item_is_in_clipboard(self, compare_hash):
        item_hash = self.item.get_data_hash()
        if compare_hash == item_hash:
            return True

    def do_layout(self):
        def do_header():
            item_header_hbox = QtGui.QHBoxLayout()
            item_header_hbox.addWidget(QtGui.QLabel(self.sender))
            item_header_hbox.addStretch()
            item_header_hbox.addStretch()
            item_header_hbox.addStretch()
            item_header_hbox.addStretch()
            item_header_hbox.addStretch()
            item_header_hbox.addWidget(QtGui.QLabel(self.timestamp))
            item_header_hbox.addStretch()
            item_header_hbox.addWidget(QtGui.QLabel(self.datestamp))
            item_layout.addLayout(item_header_hbox)

        def do_content():
            item_content_hbox = QtGui.QHBoxLayout()

            if self.clip["system"] == "notification":
                content_widget = QtGui.QLabel(self.content)
            else:
                content_widget = QTextBrowserForFancyListItemWidget(self.list_widget, self.item,
                                                                    self.content)  # http://stackoverflow.com/questions/1575884/how-to-make-links-clickable-in-a-qtextedit

            # content_widget.setWordWrapMode(QTextOption.NoWrap)
            item_content_hbox.addWidget(content_widget)
            item_layout.addLayout(item_content_hbox)

        def do_dropdown():
            dropdown_hbox_layout = QtGui.QHBoxLayout()
            self.dropdown_widget = QtGui.QToolButton()
            self.dropdown_widget.setIcon(self.item_icon)
            self.dropdown_widget.clicked.connect(self.on_dropdown_clicked)
            self.dropdown_widget.setMenu(QtGui.QMenu())  # needed to show arrow icon
            clip_type = self.clip["clip_type"]
            if clip_type == "invite":
                note_widget = QtGui.QPushButton("Accept invite")
                note_widget.clicked.connect(self.on_accept_invite_action)
            else:
                note = self.clip.get("note")
                if note:
                    note_label = views.corner_label_note % note
                else:
                    if clip_type == "html":
                        clip_type = "Text/Html"
                    else:
                        clip_type = clip_type.capitalize()
                    note_label = views.corner_label_type % clip_type
                note_widget = QtGui.QLabel(note_label)

            self.item_is_in_clipboard_label = QtGui.QLabel("")

            dropdown_hbox_layout.addWidget(note_widget)
            dropdown_hbox_layout.addStretch(1)
            dropdown_hbox_layout.addWidget(self.item_is_in_clipboard_label)
            dropdown_hbox_layout.addWidget(self.dropdown_widget)
            item_layout.addLayout(dropdown_hbox_layout)

        item_layout = QtGui.QVBoxLayout()
        do_header()
        do_content()
        do_dropdown()
        self.setLayout(item_layout)
        self.item.setSizeHint(  # size hint is the preferred size of the widget, layouts will try to keep it as close to this as possible.
            self.sizeHint())  # resize the listwidget item to fit the custom widget, using Qlabel's sizehint


class AppIcon(QtGui.QIcon):
    def __init__(self, name):
        super(self.__class__, self).__init__("images/{name}.png".format(name=name))


class PixmapThumbnail():
    Px = 48

    def __init__(self, original_pmap, Px = None):
        if Px:
            self.Px = Px
        self.original_pmap = original_pmap
        self.original_w = self.original_h = self.thumbnail = self.is_landscape = None
        self.pixmap_thumbanail()

    def pixmap_thumbanail(self):
        self.original_w = self.original_pmap.width()
        self.original_h = self.original_pmap.height()
        is_square = self.original_w == self.original_h
        if not is_square:
            smallest_side = min(self.original_w, self.original_h)
            longest_side = max(self.original_w, self.original_h)
            shift = longest_side / 4.0
            self.is_landscape = self.original_w > self.original_h
            if self.is_landscape:
                x = shift
                y = 0
            else:
                x = 0
                y = shift
            crop = self.original_pmap.copy(x, y, smallest_side,
                                           smallest_side)  # PySide.QtGui.QPixmap.copy(x, y, width, height) #https://srinikom.github.io/pyside-docs/PySide/QtGui/QPixmap.html#PySide.QtGui.PySide.QtGui.QPixmap.copy
        else:
            crop = self.original_pmap
        self.thumbnail = crop.scaled(self.Px, self.Px, transformMode=QtCore.Qt.SmoothTransformation)


class PixmapPreview():
    Px = 360

    def __init__(self, original_pmap):
        self.original_pmap = original_pmap
        self.original_w = self.original_h = self.thumbnail = self.is_landscape = self.thumbnail = None
        self.pixmap_preview()

    def pixmap_preview(self):
        self.original_w = self.original_pmap.width()
        self.original_h = self.original_pmap.height()
        if self.original_w > self.original_h:
            self.thumbnail = self.original_pmap.scaledToWidth(self.Px, TransformationMode=QtCore.Qt.SmoothTransformation)
        else:
            self.thumbnail = self.original_pmap.scaledToHeight(self.Px, TransformationMode=QtCore.Qt.SmoothTransformation)

class TrayIcon(QtGui.QSystemTrayIcon):

    def __init__(self, main):
        self.main = main
        super(self.__class__, self).__init__(main)
        self.setIcon(AppIcon("text"))
        self.activated.connect(self.on_activated)
        self.setContextMenu()

    def on_activated(self, reason):
        if reason == self.__class__.DoubleClick:
            self.restore()

    def restore(self):
        self.main.setVisible(True)  # needed to unhide http://goo.gl/RKHlMZ
        self.main.setWindowState(QtCore.Qt.WindowActive)  # needed to un-minimize
        self.main.activateWindow()  # needed to bring to top

    def setContextMenu(self, *args, **kwargs):
        context_menu = QtGui.QMenu()
        exit_action = QtGui.QAction(AppIcon("exit"), "Exit", self)
        exit_action.triggered.connect(self.main.closeReal)
        lock_action = QtGui.QAction(AppIcon("safe"), "Lock", self)
        lock_action.triggered.connect(self.show_lockout)
        context_menu.addAction(lock_action)
        context_menu.addSeparator()
        context_menu.addAction(exit_action)
        super(self.__class__, self).setContextMenu(context_menu)

    def show_lockout(self):
        self.restore()  # MUST RESTORE as without it app seems to crash without warning
        self.main.lockout_widget.on_show_lockout_slot()