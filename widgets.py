import bson.json_util as json
from functions import *
from PySide.QtGui import *
from PySide import QtCore
import views
"""
class AccountMixin(object):

    @staticmethod
    def getLogin():
        ring = keyring.get_password("pastebeam","account")
        login = json.loads(ring) if ring else {} #todo store email locally, and access only password!
        return login

    def showAccountDialogs(self):
        
        login = self.getLogin()
        
        email, e = QInputDialog.getText(self, 'Account',
            'Enter your <b>email</b>:',
            text = login.get("email"),
        )
        
        if not e:
            return
        
        password, p = QInputDialog.getText(self, 'Account',
            'Enter your <b>password</b>:',
            text = login.get("password"),
            echo=QLineEdit.Password
        )
        
        if not p:
            return
        
        keyring.set_password("pastebeam","account",json.dumps({
            "email":email,
            "password":password,
        }))
        
        if hasattr(self, "ws_worker") and hasattr(self.ws_worker, "WSOCK"): #maybe not initialized yet
            self.ws_worker.WSOCK.close()
            self.ws_worker.KEEP_RUNNING = 1
"""


class LockoutMixin(object):
    def initLockoutWidget(self):

        self.lockout_pin = lockout_pin = QLineEdit()
        lockout_pin.setAlignment(
            QtCore.Qt.AlignHCenter)  # http://www.codeprogress.com/cpp/libraries/qt/QLineEditCenterText.php#.VcnX9M7RtyN
        # self.lockout_pin.setValidator(QIntValidator(0, 9999)) #OLD# http://doc.qt.io/qt-4.8/qlineedit.html#inputMask-prop
        # self.lockout_pin.setMaxLength(4) #still need it despite setValidator or else you can keep typing
        lockout_pin.setEchoMode(
            QLineEdit.Password)  # hide with bullets #http://stackoverflow.com/questions/4663207/masking-qlineedit-text
        lockout_pin.setStatusTip("Type your account password to unlock.")
        lockout_pin.textEdited.connect(self.onLockoutPinTypedSlot)

        get_in_label = QLabel("<a href='#'>Can't get in?</a>")
        get_in_label.setAlignment(QtCore.Qt.AlignCenter)

        lines_vbox = QVBoxLayout()
        lines_vbox.addStretch(1)
        lines_vbox.addWidget(lockout_pin)
        lines_vbox.addWidget(get_in_label)
        lines_vbox.addStretch(1)

        lockout_hbox = QHBoxLayout()
        lockout_hbox.addStretch(1)
        lockout_hbox.addLayout(lines_vbox)
        lockout_hbox.addStretch(1)

        lockout_vbox = QVBoxLayout()
        lockout_vbox.addLayout(lockout_hbox)

        self.lockout_widget = QWidget()
        self.lockout_widget.setLayout(lockout_vbox)
        # self.lockout_widget.hide()
        self.stacked_widget.addWidget(self.lockout_widget)

    def onLockoutPinTypedSlot(self, written):
        login = getLogin().get("password")
        if not login:
            pass  # no password was set yet
        elif login != written:
            return
        self.stacked_widget.switchToMainWidget()
        self.lockout_pin.clear()
        for each in self.menu_lockables:
            each.setDisabled(False)

    def onShowLockoutSlot(self):
        for each in self.menu_lockables:
            each.setDisabled(True)
        self.stacked_widget.switchToLockoutWidget()


class OkCancelWidgetMixin(object):
    def doOkCancelWidget(self):
        ok_button = QPushButton("Ok")
        ok_button.clicked.connect(self.onOkButtonClickedSlot)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.onCancelButtonClickedSlot)
        okcancel_hbox = QHBoxLayout()
        okcancel_hbox.addStretch(1)
        okcancel_hbox.addWidget(ok_button)
        okcancel_hbox.addWidget(cancel_button)
        self.okcancel_widget = QWidget()
        self.okcancel_widget.setLayout(okcancel_hbox)

    def onOkButtonClickedSlot(self):
        self.done(1)

    def onCancelButtonClickedSlot(self):
        self.done(0)


class SettingsDialog(QDialog, OkCancelWidgetMixin):  # http://www.qtcentre.org/threads/37058-modal-QWidget

    @classmethod
    def show(cls,
             parent):  # THE CLASS ITSELF IS AN OBJECT WITH ITS OWN NAMESPACE, AND CALLING THE CLASS RETURNS (INSTANTIATES) A NEW INSTANCE OBJECT HELD IN THE CLASSES NAMESPACE
        cls(parent)

    def __init__(self, parent=None, f=0):
        super(self.__class__, self).__init__()
        self.main = parent
        self.current_login = getLogin()
        self.setWindowTitle("Edit Settings")
        self.doAccountWidget()
        self.doSystemWidget()
        self.doStartupWidget()
        self.doTabWidget()
        self.doOkCancelWidget()
        self.doSettingsLayout()
        self.setLayout(self.settings_layout)
        self.exec_()

    def doAccountWidget(self):
        email_hbox = QHBoxLayout()
        email_label = QLabel("Email:")
        self.email_line = QLineEdit(self.current_login.get("email"))
        email_hbox.addWidget(email_label)
        email_hbox.addWidget(self.email_line)
        email_widget = QWidget()
        email_widget.setLayout(email_hbox)

        password_hbox = QHBoxLayout()
        password_label = QLabel("Password:")
        self.password_line = QLineEdit(self.current_login.get("password"))
        self.password_line.setEchoMode(QLineEdit.Password)
        password_hbox.addWidget(password_label)
        password_hbox.addWidget(self.password_line)
        password_widget = QWidget()
        password_widget.setLayout(password_hbox)

        register_link = QLabel("<a href='#'>Register</a>")
        seperator = QLabel("|")
        forgot_link = QLabel("<a href='#'>Reset or change password</a>")
        links_hbox = QHBoxLayout()
        links_hbox.addWidget(register_link)
        links_hbox.addWidget(seperator)
        links_hbox.addWidget(forgot_link)
        links_hbox.setAlignment(QtCore.Qt.AlignRight)
        links_widget = QWidget()
        links_widget.setLayout(links_hbox)

        account_vbox = QVBoxLayout()
        account_vbox.addWidget(email_widget)
        account_vbox.addWidget(password_widget)
        account_vbox.addWidget(links_widget)

        self.account_widget = QWidget()
        self.account_widget.setLayout(account_vbox)

    def doSystemWidget(self):
        device_name_label = QLabel("Device Name:")
        self.device_name_line = QLineEdit()
        self.device_name_line.setText(getDeviceNameFromKeyring())
        device_name_hbox = QHBoxLayout()
        device_name_hbox.addWidget(device_name_label)
        device_name_hbox.addWidget(self.device_name_line)
        device_name_widget = QWidget()
        device_name_widget.setLayout(device_name_hbox)

        sync_label = QLabel("Sync device clipboard with the cloud ")
        sync_check = QCheckBox()
        sync_hbox = QHBoxLayout()
        sync_hbox.addWidget(sync_label)
        sync_hbox.addWidget(sync_check)
        sync_widget = QWidget()
        sync_widget.setLayout(sync_hbox)

        master_vbox = QVBoxLayout()
        master_vbox.addWidget(device_name_widget)
        master_vbox.addWidget(sync_widget)

        self.system_widget = QWidget()
        self.system_widget.setLayout(master_vbox)

    def setDeviceNameToKeyRing(self):
        keyring.set_password("pastebeam", "device_name",
                             self.device_name_line.text().strip() or HOST_NAME  # strip removes trailing spaces
                             )

    def doStartupWidget(self):

        run_label = QLabel("Run PasteBeam on startup")
        run_check = QCheckBox()
        run_hbox = QHBoxLayout()
        run_hbox.addWidget(run_label)
        run_hbox.addWidget(run_check)
        run_widget = QWidget()
        run_widget.setLayout(run_hbox)

        updates_label = QLabel("Periodically check for updates")
        updates_check = QCheckBox()
        updates_hbox = QHBoxLayout()
        updates_hbox.addWidget(updates_label)
        updates_hbox.addWidget(updates_check)
        updates_widget = QWidget()
        updates_widget.setLayout(updates_hbox)

        self.startup_layout = QVBoxLayout()
        self.startup_layout.addWidget(run_widget)
        self.startup_layout.addWidget(updates_widget)

        self.startup_widget = QWidget()
        self.startup_widget.setLayout(self.startup_layout)

    def doTabWidget(self):
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.account_widget, QIcon("images/account"), "Account")
        self.tab_widget.addTab(self.system_widget, QIcon("images/system"), "Device")
        self.tab_widget.addTab(self.startup_widget, QIcon("images/controls"), "Preferences")

    def doSettingsLayout(self):
        self.settings_layout = QVBoxLayout()
        self.settings_layout.addWidget(self.tab_widget)
        self.settings_layout.addWidget(self.okcancel_widget)

    def onOkButtonClickedSlot(self):
        self.setAccountInfoToKeyring()
        self.setDeviceNameToKeyRing()
        self.done(1)

    def onCancelButtonClickedSlot(self):

        self.done(0)

    def setAccountInfoToKeyring(self):

        login = getLogin()

        typed_email = self.email_line.text()
        typed_password = self.password_line.text()

        if not typed_email and typed_password:  # TODO STRONGER VALIDATION HERE
            return

        keyring.set_password("pastebeam", "account", json.dumps({
            "email": typed_email,
            "password": typed_password,
        }))

        if hasattr(self.main, "ws_worker") and hasattr(self.main.ws_worker, "WSOCK"):  # maybe not initialized yet
            if self.main.ws_worker.WSOCK:
                self.main.ws_worker.WSOCK.close()
            self.main.ws_worker.KEEP_RUNNING = 1


class WaitForSignalDialogMixin(object):
    def showWaitForSignalDialog(self, question, data_dict, error_msg, success_msg=False):
        "shows an unclosable dialog until closeWaitDialogSignalForMain"
        self.main.outgoingSignalForWorker.emit(
            dict(
                question=question,
                data=data_dict
            )
        )
        WaitForSignalDialog(self,
                            "please wait")  # EXECUTION FREEZfES HERE so WaitForSignalDialog().done(1) will not work, use signals instead
        if not self.success["success"]:
            QMessageBox.warning(
                # QMessageBox.critical #http://stackoverflow.com/questions/20841081/how-to-pop-up-a-message-window-in-qt
                self,
                "Error",
                "%s!<br><b>Reason:</b> <i>%s</i>" % (error_msg.capitalize(), self.success["reason"])
            )
        elif success_msg:
            QMessageBox.information(  # http://stackoverflow.com/questions/20841081/how-to-pop-up-a-message-window-in-qt
                self,
                "Success",
                "%s!" % success_msg.capitalize()
            )


class ContactsDialog(QDialog, OkCancelWidgetMixin, WaitForSignalDialogMixin):
    @classmethod
    def show(cls, parent):
        cls(parent)

    def __init__(self, parent):
        super(self.__class__, self).__init__(parent)

        self.main = parent
        self.contacts_list = []

        self.setWindowTitle('Edit Contacts')
        self.doAddContactWidget()
        self.doListWidget()
        self.doOkCancelWidget()
        self.doContactsWidget()

        # self.bindEvents()

        self.setLayout(self.contacts_layout)
        self.resizeMinWindowSizeForListWidget()

        self.doPreExecGetContactsList()
        if self.success:
            self.exec_()

    def doPreExecGetContactsList(self):
        self.showWaitForSignalDialog("Contacts?", {"contacts_list": None}, "could not get contacts list",
                                     success_msg=False)

        if self.success["success"]:
            self.contacts_list = self.success["contacts"]
            for each_email in self.contacts_list:
                self.list_widget.addItem(each_email)

            self.list_widget.sortItems()

    def onFriendRequestButtonClickSlot(self):
        email = self.email_line.text()
        if not validators.email(email):
            QMessageBox.warning(  # http://stackoverflow.com/questions/20841081/how-to-pop-up-a-message-window-in-qt
                self,
                "Warning",
                "Invalid email address!"
            )
            return

        self.showWaitForSignalDialog("Invite?", {"email": email}, "failed to send friend invite",
                                     success_msg="friend request sent")

    def onFriendRequestReceivedByServerSlot(self):
        self.friend_request_wait_dialog.done(1)
        QMessageBox.information(self, "Success", "Friend request sent!")

    def currentItems(self):
        """http://stackoverflow.com/questions/4629584/pyqt4-how-do-you-iterate-all-items-in-a-qlistwidget"""
        items = []
        for index in xrange(self.list_widget.count()):
            items.append(self.list_widget.item(index).text())
        return items

    def onOkButtonClickedSlot(self):
        # guaranteed thread safe as this window wouldn't even appear without self.contacts_list
        current_items = self.currentItems()

        if set(current_items) == set(self.contacts_list):  # no need to contact server
            super(self.__class__, self).onOkButtonClickedSlot()
            return

        self.showWaitForSignalDialog("Contacts?", {"contacts_list": current_items}, "failed to save contacts to server",
                                     success_msg="contacts saved to server")

        if self.success["success"]:
            super(self.__class__, self).onOkButtonClickedSlot()

    def resizeMinWindowSizeForListWidget(self):
        default_height = self.sizeHint().height()
        new_height = default_height * 1.15
        self.setMinimumHeight(new_height)

    def doAddContactWidget(self):
        email_label = QLabel("Friend's Email:")
        self.email_line = email_line = QLineEdit()

        friend_request_button = QPushButton("Send friend invite")
        friend_request_button.clicked.connect(self.onFriendRequestButtonClickSlot)

        lines_vbox = QVBoxLayout()
        lines_vbox.addWidget(email_label)
        lines_vbox.addWidget(email_line)
        lines_vbox.addWidget(friend_request_button)

        self.add_user_widget = QWidget()
        self.add_user_widget.setLayout(lines_vbox)

    def doListWidget(self):
        contacts_list_label = QLabel("Friends list:")
        self.list_widget = QListWidget()
        # for letter in range(65,91):
        #    self.contacts_list.addItem("%s@yahoo.com"%chr(letter))
        contacts_list_delete = QPushButton("Delete friend")
        contacts_list_delete.clicked.connect(self.onDeleteClickedSlot)
        contacts_list_layout = QVBoxLayout()
        contacts_list_layout.addWidget(contacts_list_label)
        contacts_list_layout.addWidget(self.list_widget)
        contacts_list_layout.addWidget(contacts_list_delete)
        self.contacts_list_widget = QListWidget()
        self.contacts_list_widget.setLayout(contacts_list_layout)

    def doContactsWidget(self):
        # how_label = QLabel("For your security, clips from other PasteBeam users are automatically blocked without notice. To unblock a friend, add his email to your contacts list here. Likewise, for him to receive your clips, he must add your login email to his own contacts list.")
        # how_label.setWordWrap(True)

        self.contacts_layout = QVBoxLayout()
        # self.contacts_layout.addWidget(how_label)
        self.contacts_layout.addWidget(self.add_user_widget)
        self.contacts_layout.addWidget(self.contacts_list_widget)
        self.contacts_layout.addWidget(self.okcancel_widget)

    def onDeleteClickedSlot(self):
        current_row = self.list_widget.currentRow()
        self.list_widget.takeItem(current_row)


class FaderWidget(QWidget):
    def __init__(self, old_widget, new_widget, duration=333):
        QWidget.__init__(self, new_widget)

        self.old_pixmap = QPixmap(new_widget.size())
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
        painter = QPainter()
        painter.begin(self)
        painter.setOpacity(self.pixmap_opacity)
        painter.drawPixmap(0, 0, self.old_pixmap)
        painter.end()

    def animate(self, value):
        self.pixmap_opacity = 1.0 - value
        self.repaint()


class StackedWidgetFader(QStackedWidget):
    def __init__(self, parent):
        super(StackedWidgetFader, self).__init__(parent)
        self.duration = 444

    def setCurrentIndex(self, index):
        self.fader_widget = FaderWidget(self.currentWidget(), self.widget(index),
                                        self.duration)  # does not work as a mixin, as self.currentWidget needs to be a subclass of QStackedWidget
        QStackedWidget.setCurrentIndex(self, index)

    def setFadeDuration(self, duration):
        self.duration = duration


class CommonListWidget(QListWidget, WaitForSignalDialogMixin):
    def __init__(self, parent=None):
        super(CommonListWidget, self).__init__(parent)
        self.parent = parent
        self.main = parent.main
        self.setVerticalScrollMode(
            QAbstractItemView.ScrollPerPixel)  # http://stackoverflow.com/questions/2016323/qt4-is-it-possible-to-make-a-qlistview-scroll-smoothly

        self.itemPressed.connect(self.onItemPressedSlot)  # ITEM CLICK DOES NOT WORK USE PRESSED FUCK!!

    def getItems(self):
        # http://stackoverflow.com/questions/12087715/pyqt4-get-list-of-all-labels-in-qlistwidget
        for index in xrange(self.count()):
            yield self.item(index)

    def resizeEvent(self, event):
        super(CommonListWidget, self).resizeEvent(event)
        # do something on resize!

    def onItemPressedSlot(self, i):
        "So that any click of an item will enable all context items"
        self.parent.onTabChangedSlot(self.index)  # hide notification icon in tab when clicking on an item

    def doCommon(self):

        self.doStyling()

        self.doUncommon()  # do uncommon here

        self.itemDoubleClicked.connect(
            self.onItemDoubleClickSlot)  # textChanged() is emited whenever the contents of the widget changes (even if its from the app itself) whereas textEdited() is emited only when the user changes the text using mouse and keyboard (so it is not emitted when you call QLineEdit::setText()).

    def doStyling(self):
        self.setIconSize(
            self.parent.icon_size)  # http://www.qtcentre.org/threads/8733-Size-of-an-Icon #http://nullege.com/codes/search/PySide.QtGui.QListWidget.setIconSize
        self.setAlternatingRowColors(
            True)  # http://stackoverflow.com/questions/23213929/qt-qlistwidget-item-with-alternating-colors

    def getClipDataByCurrentRow(self):
        current_row = self.currentRow()
        current_item = self.currentItem()
        current_item = json.loads(current_item.data(
            QtCore.Qt.UserRole))  # http://stackoverflow.com/questions/25452125/is-it-possible-to-add-a-hidden-value-to-every-item-of-qlistwidget
        return current_row, current_item

    def onItemDoubleClickSlot(self, double_clicked_item):

        # current_item = self.item(0)
        # current_clip = json.loads(current_item.data(QtCore.Qt.UserRole))

        double_clicked_data = json.loads(double_clicked_item.data(QtCore.Qt.UserRole))

        hash_, prev = double_clicked_data["hash"], self.main.previous_hash

        if hash_ == prev:
            self.main.onSetStatusSlot(("already copied", "warn"))
            return

        # container name is already in double_clicked_clip

        # double_clicked_clip = self.convertToDeviceClip(double_clicked_clip)

        self.main.onSetNewClipSlot(dict(new_clip = double_clicked_data, block_clip_change_detection = False))

        # self.previous_hash = hash #or else onClipChangeSlot will react and a duplicate new list item will occur.


class NotificationListWidget(CommonListWidget):
    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.index = 3
        self.doCommon()

    def doUncommon(self):
        pass


class StarListWidget(CommonListWidget):
    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.index = 1
        self.doCommon()

    def doUncommon(self):
        pass


class MainListWidget(CommonListWidget):
    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.index = 0
        self.doCommon()

    def doUncommon(self):
        pass


class FriendListWidget(CommonListWidget):
    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.index = 2
        self.doCommon()

    def doUncommon(self):
        pass


class PanelTabWidget(QTabWidget):
    def __init__(self, icon_size, parent):
        super(self.__class__, self).__init__(parent)
        self.main = parent
        self.icon_size = icon_size
        self.doSearchWidget()
        self.doPanels()
        self.addPanels()

        self.currentChanged.connect(self.onTabChangedSlot)

    def getListWidgetFromClip(self, clip):
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

    def onTabChangedSlot(self, index):
        if index == 0:
            self.setTabIcon(0, QIcon("images/devices.png"))
        if index == 1:
            self.setTabIcon(1, QIcon("images/star.png"))
        if index == 2:
            self.setTabIcon(2, QIcon("images/friends.png"))
        if index == 3:
            self.setTabIcon(3, QIcon("images/bulb.png"))

    def onChangeTabIconSlot(self, tabs_affected):
        if "starred" in tabs_affected:
            new_icon_tab = 1
        elif "notification" in tabs_affected:
            new_icon_tab = 3
        elif "main" in tabs_affected:
            new_icon_tab = 0
        elif "share" in tabs_affected:
            new_icon_tab = 2

        self.setTabIcon(new_icon_tab, QIcon("images/new.png"))

    def doSearchWidget(self):
        self.search = QLineEdit()
        self.search.textEdited.connect(self.onSearchEditedSlot)
        search_tip = "Search through your items (preview text only)."
        self.search.setStatusTip(search_tip)
        self.search.setPlaceholderText("Filter...")

    def onChangeViewMenu(self, action):
        actions = self.main.viewMenu.actions()
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
            for item in list_widget.getItems():
                activate = False
                for clip_type in activate_clip_types:
                    item_data = json.loads(item.data(QtCore.Qt.UserRole))
                    if item_data["clip_type"] in clip_type:
                        activate = True
                if activate:
                    item.setHidden(False)
                else:
                    item.setHidden(True)

    def onSearchEditedSlot(self, written):
        for list_widget in self.panels:
            # items = [] #http://stackoverflow.com/questions/12087715/pyqt4-get-list-of-all-labels-in-qlistwidget
            # for index in xrange(list_widget.count()):
            #    items.append(list_widget.item(index))

            is_blank = not bool(written)  # unhide when written is blank

            for item in list_widget.getItems():
                if is_blank:
                    item.setHidden(False)  # unhide all
                else:
                    item_data = json.loads(item.data(QtCore.Qt.UserRole))

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

    def doPanels(self):

        self.main_list_widget = MainListWidget(self)

        self.star_list_widget = StarListWidget(self)

        self.friend_list_widget = FriendListWidget(self)

        self.notification_list_widget = NotificationListWidget(self)

        self.panels = [self.main_list_widget, self.star_list_widget, self.friend_list_widget, self.notification_list_widget]
        # devices star friends

    def addPanels(self):
        self.addTab(self.main_list_widget, QIcon("images/devices"), "Devices")
        self.addTab(self.star_list_widget, QIcon("images/star"), "Bookmarks")
        self.addTab(self.friend_list_widget, QIcon("images/friends"), "Friends")
        # self.addTab(QWidget(), QIcon("images/bulb"), "Notifications")
        self.addTab(self.notification_list_widget, QIcon("images/bulb"), "Notifications")
        self.setCornerWidget(self.search)

    def onIncomingDelete(self, location):
        list_widget_name, remove_row = location

        if list_widget_name == "MainListWidget":
            self.main_list_widget.takeItem(remove_row)  # POSSIBLE RACE CONDITION
        elif list_widget_name == "StarListWidget":
            self.star_list_widget.takeItem(remove_row)
        elif list_widget_name == "FriendListWidget":
            self.friend_list_widget.takeItem(remove_row)
        elif list_widget_name == "NotificationListWidget":
            self.notification_list_widget.takeItem(remove_row)

    def clearAllLists(self):
        for each in self.panels:
            each.clear()

    def getMatchingContainerForHash(self, hash):
        hash_to_container = {}
        for list_widget in self.panels:  # the reason why it's in panel tab widget
            row = 0
            while row < list_widget.count():  # http://www.qtcentre.org/threads/32716-How-to-iterate-through-QListWidget-items
                each_item = list_widget.item(row)
                item_data = each_item.data(QtCore.Qt.UserRole)
                json_data = json.loads(item_data)
                if not json_data["system"] in ["share",
                                               "notification"]:  # DO NOT reuse shared clips, as they were encrypted with a random key, not user's password. Not reusing wil force the system to re-encrypt the container with user's password
                    hash_container_pair = {json_data["hash"]: json_data.get("container_name")}
                    hash_to_container.update(hash_container_pair)
                row += 1

        container = hash_to_container.get(hash)  # or None
        del hash_to_container
        return container


class LockoutStackedWidget(StackedWidgetFader):
    # https://wiki.python.org/moin/PyQt/Fading%20Between%20Widgets
    # http://www.qtcentre.org/threads/30830-setCentralWidget()-without-deleting-prev-widget
    def __init__(self, parent=None):
        # QStackedWidget.__init__(self, parent)
        super(LockoutStackedWidget, self).__init__(
            parent)  # it's better to use super method instead of explicitly calling the parent class, because the former allows to add another parent and "push up" the previous parent up the ladder without making any changes to the code here

    def switchToMainWidget(self):
        self.setCurrentIndex(0)

    def switchToLockoutWidget(self):
        self.setCurrentIndex(1)


class WaitForSignalDialog(QDialog):
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
        self.doLayout()
        self.setLayout(self.layout)
        self.bindEvents()
        self.exec_()

    def doLayout(self):
        wait_label = QLabel("<h1>%s...</h1>" % self.label.capitalize())
        self.layout = QVBoxLayout()
        self.layout.addWidget(wait_label)

    def bindEvents(self):
        self.main.ws_worker.closeWaitDialogSignalForMain.connect(self.onCloseWaitDialogSlot)

    def onCloseWaitDialogSlot(self, result):
        self.parent.success = result
        try:
            self.main.updateContactsListSignal.emit(sorted(result["contacts"]))
        except KeyError:
            pass
        self.done(1)


class QTextBrowserForFancyListWidgetItem(QTextBrowser):
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


class FancyListWidgetItem(QWidget, WaitForSignalDialogMixin):
    host_colors = sorted(
        ["#FF4848", "#800080", "#5757FF", "#1FCB4A", "#59955C", "#9D9D00", "#62A9FF", "#06DCFB", "#9669FE", "#23819C",
         "#2966B8", "#3923D6", "#23819C", "#FF62B0", ])  # http://www.hitmill.com/html/pastels.html
    file_icons = map(lambda file_icon: file_icon.split()[-1].upper(), os.listdir(os.path.normpath("images/files")))

    def __init__(self, clip, item):
        super(self.__class__, self).__init__()

        self.item = item
        self.clip = clip

        self.sender = self.timestamp = self.datestamp = self.content = None

        self.list_widget = self.item.listWidget()
        self.main = self.list_widget.main

        self.copy_action = self.accept_invite_action = self.delete_action = self.share_action = self.star_action = None

        self.setHeaderFromClip()
        self.setContentFromClip()
        self.doLayout()

        self.item_menu = QMenu()
        self.setContextMenuPolicy(
            QtCore.Qt.CustomContextMenu)  # need to access menu explicitly ActionContextMenu doesn't allow this
        self.customContextMenuRequested.connect(
            self.showContextMenu)  # http://www.setnode.com/blog/right-click-context-menus-with-qt/

    def showContextMenu(self, point_where_clicked):
        self.resetActions()
        point_where_clicked = self.mapToGlobal(point_where_clicked)
        self.item_menu.exec_(point_where_clicked)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.resetActions()
        # self.list_widget.setCurrentItem(self.item)
        super(self.__class__, self).mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if not self.clip["system"] == "notification":
            self.list_widget.onItemDoubleClickSlot(self.item)
            # super(self.__class__, self).mouseDoubleClickEvent(event)

    def resetActions(self):
        self.clearActions()
        self.setActions()

    def clearActions(self):
        self.item_menu.clear()

    def setActions(self):

        if not self.clip["system"] == "notification":
            self.setCopyAction()
            self.setStarAction()
            self.setShareAction()

        elif self.clip["clip_type"] == "invite":
            self.setAcceptInviteAction()

        self.setDeleteAction()  # Put delete last

    def setStarAction(self):
        # star action
        self.star_action = star_action = QAction(QIcon("images/star.png"), '&Star', self)
        # self.star_action.triggered.connect(self.onAddStarAction)
        sub_menu = self.getNoteSubMenu(history_list_widget =self.main.panel_tab_widget.star_list_widget,
                                       trigger = self.onAddStarAction,
                                       parent_action = None)
        star_action.setMenu(sub_menu)
        self.item_menu.addAction(star_action)

    def getNoteSubMenu(self, history_list_widget, trigger, parent_action,
                                 placeholder="Enter a note...", max_length = 40):
        def always_close_menu_decorator(func):
            def closure():
                func()
                self.item_menu.close()
            return closure

        sub_menu = QMenu()
        # share_sub_menu.triggered.connect(self.onShareSubMenuTriggeredSlot)
        message_subaction = QWidgetAction(self)
        message_widget = QLineEdit()
        message_widget.setMaxLength(max_length)

        @always_close_menu_decorator
        def onReturnPressed():
            # star_action.trigger()
            trigger(message_widget.text()[:max_length].strip(), parent_action)

        message_widget.returnPressed.connect(onReturnPressed)
        message_widget.setPlaceholderText(placeholder)
        message_subaction.setDefaultWidget(message_widget)
        sub_menu.addAction(message_subaction)

        if history_list_widget:
            sub_menu.addSeparator()
            action_names = []
            for each_item in history_list_widget.getItems(): #self.main.panel_tab_widget.star_list_widget.getItems():
                each_item_data = json.loads(each_item.data(QtCore.Qt.UserRole))
                each_item_note = each_item_data.get("note")
                if each_item_note and each_item_note not in action_names:

                    @always_close_menu_decorator
                    def on_note_history_action():
                        trigger(each_item_note, parent_action)

                    note_history_action = QAction(each_item_note, self)
                    note_history_action.triggered.connect(on_note_history_action)
                    sub_menu.addAction(note_history_action)
                    action_names.append(each_item_note)

        return sub_menu

    def onAddStarAction(self, note, *args):
        current_item = json.loads(self.item.data(QtCore.Qt.UserRole))
        current_item["note"] = note
        del current_item["_id"]
        async_process = dict(
            question="Star?",
            data=current_item
        )
        self.main.outgoingSignalForWorker.emit(async_process)

    def setAcceptInviteAction(self):
        self.accept_invite_action = QAction(QIcon("images/ok.png"), "&Accept invite", self)
        self.accept_invite_action.triggered.connect(self.onAcceptInviteAction)
        self.item_menu.addAction(self.accept_invite_action)

    def disableAcceptInviteAction(self):
        self.accept_invite_action.setDisabled(True)

    def onAcceptInviteAction(self):
        current_item = json.loads(self.item.data(QtCore.Qt.UserRole))
        if not current_item["clip_type"] == "invite":
            return
        email = current_item["host_name"]

        self.showWaitForSignalDialog("Accept?", {"email": email}, "could not accept invitation", success_msg=False)

    def setShareAction(self):
        self.share_action = QAction(QIcon("images/share.png"), "S&hare", self)
        self.enableShareAction()
        self.item_menu.addAction(self.share_action)

    def onShareSubMenuTriggeredSlot(self, note, action):
        email = action.text()
        share_item_data = json.loads(self.item.data(QtCore.Qt.UserRole))
        share_item_data["note"] = note

        # now get decryption keys
        clip_system = share_item_data["system"]
        if clip_system in ["main", "starred"]:
            decryption_key = getLogin().get("password")
        elif clip_system == "share":
            return  # DONE decrypt public key encrypted random AES key
        elif clip_system == "notification":  # cant share notifications yet
            return

        share_item_data["recipient"] = email
        share_item_data["decryption_key"] = decryption_key  # RAW
        self.main.outgoingSignalForWorker.emit(
            {
                "question": "Share?",
                "data": share_item_data
            }
        )

    def enableShareAction(self):
        if not self.main.contacts_list:
            self.share_action.setDisabled(True)
            # ADD bubble explaining why
        else:
            self.share_action.setDisabled(False)
            share_sub_menu = QMenu()
            #share_sub_menu.triggered.connect(self.onShareSubMenuTriggeredSlot)
            for email_addr in sorted(self.main.contacts_list):
                email_addr_action = QAction(email_addr, self)
                sub_menu = self.getNoteSubMenu(history_list_widget=None,
                                               trigger=self.onShareSubMenuTriggeredSlot,
                                               parent_action=email_addr_action,
                                               placeholder="Enter a message...")
                email_addr_action.setMenu(sub_menu)
                share_sub_menu.addAction(email_addr_action)
            self.share_action.setMenu(share_sub_menu)

    def setCopyAction(self):
        self.copy_action = copy_action = QAction(QIcon("images/copy.png"), "&Copy all", self)
        copy_action.triggered.connect(self.onCopyActionSlot)
        self.item_menu.addAction(copy_action)
        separator = QAction(self)
        separator.setSeparator(True)
        self.item_menu.addAction(separator)

    def onCopyActionSlot(self):
        self.list_widget.onItemDoubleClickSlot(self.item)  # listwidgetitems don't have signals, so must use parent

    def setDeleteAction(self):
        separator = QAction(self)
        separator.setSeparator(True)  # http://www.qtcentre.org/threads/21838-Separator-in-context-menu
        self.delete_action = QAction(QIcon("images/trash.png"), '&Delete', self)  # delete.setText("Delete")
        self.delete_action.triggered.connect(self.onDeleteAction)
        self.item_menu.addAction(separator)
        self.item_menu.addAction(self.delete_action)

    def onDeleteAction(self):
        current_row, current_item = self.list_widget.getClipDataByCurrentRow()
        remove_id = current_item["_id"]
        async_process = dict(
            question="Delete?",
            data={"remove_id": remove_id, "remove_row": current_row,
                  "list_widget_name": self.list_widget.__class__.__name__}
        )
        self.main.outgoingSignalForWorker.emit(async_process)

    def setHeaderFromClip(self):
        seed = hash32(self.clip["host_name"])
        reproducible_random_color = random.Random(seed).choice(self.host_colors)  # REPRODUCABLE RANDOM COLOR FROM SEED

        datetime_stamp = datetime.datetime.fromtimestamp(self.clip["timestamp_server"])
        self.timestamp = u"<h3 style='color:grey'>{dt:%I}:{dt:%M}:{dt:%S}{dt:%p}</h3>".format(dt=datetime_stamp)
        self.datestamp = u"<h3 style='color:grey'>{dt.month}-{dt.day}-{dt.year}</h3>".format(dt=datetime_stamp)
        self.sender = u"<h3 style='color:{color}'>{host_name}</h3>".format(color=reproducible_random_color,
                                                                           host_name=self.clip["host_name"])

    def setContentFromClip(self):
        if self.clip["clip_type"] == "screenshot":
            # crop and reduce pmap size to fit square icon
            # image = QImage()
            # LOG.info(image.loadFromData(self.clip["clip_display"]["thumb"]) )
            # self.item.setIcon(QIcon(QPixmap(image)))
            self.item.setIcon(AppIcon("image"))
            self.content = views.image_preview.format(
                b64 = self.clip["clip_display"]["thumb"].encode('base64'),
                **self.clip["clip_display"]["info"]
            )
            # print self.content

        elif self.clip["clip_type"] == "html":
            self.item.setIcon(QIcon("images/text.png"))
            self.content = self.clip["clip_display"]

        elif self.clip["clip_type"] == "text":
            self.item.setIcon(QIcon("images/text.png"))
            self.content = self.clip["clip_display"]

        elif self.clip["clip_type"] == "files":
            self.item.setIcon(QIcon("images/files.png"))
            files = []
            for each_filename in self.clip["clip_display"]:
                ext = each_filename.split(".")[-1]
                file_icon = "files/%s" % ext
                if not ext.upper() in self.file_icons:
                    pass  # file_icon = os.path.normpath("files/_blank")
                if ext == "_folder":  # get rid of the ._folder from folder._folder
                    each_filename = each_filename.split(".")[0]
                files.append(u"{icon} {file_name}".format(
                    # do NOT do "string {thing}".format(thing = u"unicode), or else unicode decode error will occur, the first string must be u"string {thing}"
                    file_name=each_filename,
                    icon=views.icon_html.format(name=file_icon, side=self.main.px_to_dp(12))
                ))

            self.content = u"<ol><li>{li}</ol>".format(li=u"<li> ".join(files))

        elif self.clip["clip_type"] == "invite":
            self.item.setIcon(AppIcon("me"))
            self.content = self.clip["clip_display"]

        elif self.clip["clip_type"] == "confirmation":  # change to "accepted" and get updated contacts here by appending "Contacts?" to outgoing queue
            self.item.setIcon(AppIcon("ok")) #todo change to check mark
            self.content = self.clip["clip_display"]

    def onDropDownClicked(self):
        def getLatestConextActionsForItem():
            self.resetActions()
            self.dropdown_widget.setMenu(self.item_menu)
            self.dropdown_widget.showMenu()
            # dropdown_widget.addItem(QIcon("images/copy.png"), "Copy all")

        getLatestConextActionsForItem()

    def doLayout(self):
        def do_header():
            item_header_hbox = QHBoxLayout()
            item_header_hbox.addWidget(QLabel(self.sender))
            item_header_hbox.addWidget(QLabel(self.timestamp))
            item_header_hbox.addWidget(QLabel(self.datestamp))
            item_layout.addLayout(item_header_hbox)

        def do_content():
            item_content_hbox = QHBoxLayout()

            if self.clip["system"] == "notification":
                content_widget = QLabel(self.content)
            else:
                content_widget = QTextBrowserForFancyListWidgetItem(self.list_widget, self.item,
                                                                    self.content)  # http://stackoverflow.com/questions/1575884/how-to-make-links-clickable-in-a-qtextedit

            # content_widget.setWordWrapMode(QTextOption.NoWrap)
            item_content_hbox.addWidget(content_widget)
            item_layout.addLayout(item_content_hbox)

        def do_dropdown():
            dropdown_hbox_layout = QHBoxLayout()
            self.dropdown_widget = QToolButton()
            self.dropdown_widget.setIcon(AppIcon("action"))
            self.dropdown_widget.clicked.connect(self.onDropDownClicked)
            self.dropdown_widget.setMenu(QMenu())  # needed to show arrow icon
            clip_type = self.clip["clip_type"]
            if clip_type == "invite":
                note_widget = QPushButton("Accept invite")
                note_widget.clicked.connect(self.onAcceptInviteAction)
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
                note_widget = QLabel(note_label)
            dropdown_hbox_layout.addWidget(note_widget)
            dropdown_hbox_layout.addStretch(1)
            dropdown_hbox_layout.addWidget(self.dropdown_widget)
            item_layout.addLayout(dropdown_hbox_layout)

        item_layout = QVBoxLayout()
        do_header()
        do_content()
        do_dropdown()
        self.setLayout(item_layout)
        self.item.setSizeHint(
            self.sizeHint())  # resize the listwidget item to fit the custom widget, using Qlabel's sizehint


class AppIcon(QIcon):
    def __init__(self, name):
        super(self.__class__, self).__init__("images/{name}.png".format(name=name))


class PixmapThumbnail():
    Px = 48

    def __init__(self, original_pmap, Px = None):
        if Px:
            self.Px = Px
        self.original_pmap = original_pmap
        self.original_w = self.original_h = self.thumbnail = self.is_landscape = None
        self.pixmapThumbnail()

    def pixmapThumbnail(self):
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
        self.thumbnail = crop.scaled(self.Px, self.Px, TransformationMode=QtCore.Qt.SmoothTransformation)


class PixmapPreview():
    Px = 360

    def __init__(self, original_pmap):
        self.original_pmap = original_pmap
        self.original_w = self.original_h = self.thumbnail = self.is_landscape = self.thumbnail = None
        self.pixmapPreview()

    def pixmapPreview(self):
        self.original_w = self.original_pmap.width()
        self.original_h = self.original_pmap.height()
        if self.original_w > self.original_h:
            self.thumbnail = self.original_pmap.scaledToWidth(self.Px, TransformationMode=QtCore.Qt.SmoothTransformation)
        else:
            self.thumbnail = self.original_pmap.scaledToHeight(self.Px, TransformationMode=QtCore.Qt.SmoothTransformation)

class TrayIcon(QSystemTrayIcon):
    def __init__(self, main):
        self.main = main
        super(self.__class__, self).__init__(main)
        self.setIcon(AppIcon("text"))
        self.activated.connect(self.onActivated)
    def onActivated(self, reason):
        if reason == self.__class__.DoubleClick:
            self.main.setVisible(True)
            self.main.setWindowState(QtCore.Qt.WindowActive)
