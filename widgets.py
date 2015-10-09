import bson.json_util as json

from functions import *

from PySide.QtGui import *
from PySide import QtCore
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
        lockout_pin.setAlignment(QtCore.Qt.AlignHCenter) #http://www.codeprogress.com/cpp/libraries/qt/QLineEditCenterText.php#.VcnX9M7RtyN
        #self.lockout_pin.setValidator(QIntValidator(0, 9999)) #OLD# http://doc.qt.io/qt-4.8/qlineedit.html#inputMask-prop
        #self.lockout_pin.setMaxLength(4) #still need it despite setValidator or else you can keep typing
        lockout_pin.setEchoMode(QLineEdit.Password) #hide with bullets #http://stackoverflow.com/questions/4663207/masking-qlineedit-text
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
        #self.lockout_widget.hide()
        self.stacked_widget.addWidget(self.lockout_widget)
        
    def onLockoutPinTypedSlot(self, written):
        login = getLogin().get("password")
        if not login:
            pass #no password was set yet
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

        
class SettingsDialog(QDialog, OkCancelWidgetMixin): #http://www.qtcentre.org/threads/37058-modal-QWidget

    @classmethod
    def show(cls, parent): #THE CLASS ITSELF IS AN OBJECT WITH ITS OWN NAMESPACE, AND CALLING THE CLASS RETURNS (INSTANTIATES) A NEW INSTANCE OBJECT HELD IN THE CLASSES NAMESPACE
        cls(parent)
    
    def __init__(self, parent = None, f = 0):
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
        sync_hbox  = QHBoxLayout()
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
       keyring.set_password("pastebeam","device_name",
            self.device_name_line.text().strip() or HOST_NAME #strip removes trailing spaces
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
        
        if not typed_email and typed_password: #TODO STRONGER VALIDATION HERE
            return
        
        keyring.set_password("pastebeam","account",json.dumps({
            "email":typed_email,
            "password":typed_password,
        }))
        
        if hasattr(self.main, "ws_worker") and hasattr(self.main.ws_worker, "WSOCK"): #maybe not initialized yet
            if self.main.ws_worker.WSOCK:
                self.main.ws_worker.WSOCK.close()
            self.main.ws_worker.KEEP_RUNNING = 1
            
class WaitForSignalDialogMixin(object):
    def showWaitForSignalDialog(self, question, data_dict, error_msg, success_msg = False):
        "shows an unclosable dialog until closeWaitDialogSignalForMain"
        self.main.outgoingSignalForWorker.emit(
            dict(
                question = question,
                data = data_dict
            )
        )
        WaitForSignalDialog(self, "please wait")#EXECUTION FREEZES HERE so WaitForSignalDialog().done(1) will not work, use signals instead
        if not self.success["success"]:
            QMessageBox.warning( #QMessageBox.critical #http://stackoverflow.com/questions/20841081/how-to-pop-up-a-message-window-in-qt
                self,
                "Error",
                "%s!<br><b>Reason:</b> <i>%s</i>"%(error_msg.capitalize(), self.success["reason"])
            )
        elif success_msg:
            QMessageBox.information( #http://stackoverflow.com/questions/20841081/how-to-pop-up-a-message-window-in-qt
                self,
                "Success",
                "%s!"%success_msg.capitalize()
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

        #self.bindEvents()

        self.setLayout(self.contacts_layout)
        self.resizeMinWindowSizeForListWidget()
        
        self.doPreExecGetContactsList()
        if self.success:
            self.exec_()
            
    def doPreExecGetContactsList(self):
        self.showWaitForSignalDialog("Contacts?", {"contacts_list":None}, "could not get contacts list", success_msg = False)

        if self.success["success"]:
            self.contacts_list = self.success["data"]
            for each_email in self.contacts_list:
                self.list_widget.addItem(each_email)

            self.list_widget.sortItems()

    def onFriendRequestButtonClickSlot(self):
        email = self.email_line.text()
        if not validators.email(email):
            QMessageBox.warning( #http://stackoverflow.com/questions/20841081/how-to-pop-up-a-message-window-in-qt
                self,
                "Warning",
                "Invalid email address!"
            )
            return
            
        self.showWaitForSignalDialog("Invite?", {"email":email}, "failed to send friend request", success_msg = "friend request sent")

    def onFriendRequestReceivedByServerSlot(self):
        self.friend_request_wait_dialog.done(1)
        QMessageBox.information(self,"Success", "Friend request sent!")
    
    def currentItems(self):
        """http://stackoverflow.com/questions/4629584/pyqt4-how-do-you-iterate-all-items-in-a-qlistwidget"""
        items = []
        for index in xrange(self.list_widget.count()):
            items.append(self.list_widget.item(index).text())
        return items

    def onOkButtonClickedSlot(self):
        #guaranteed thread safe as this window wouldn't even appear without self.contacts_list
        current_items = self.currentItems()

        if set(current_items) == set(self.contacts_list): #no need to contact server
            super(self.__class__,self).onOkButtonClickedSlot()
            return

        self.showWaitForSignalDialog("Contacts?", {"contacts_list":current_items}, "failed to save contacts to server", success_msg = "contacts saved to server")

        if self.success["success"]:
            #self.contacts_list = self.success["data"]
            #self.main.panel_tab_widget.onContactsListIncomming(self.contacts_list)
            super(self.__class__,self).onOkButtonClickedSlot()
    
    def resizeMinWindowSizeForListWidget(self):
        default_height = self.sizeHint().height()
        new_height = default_height *1.15
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
        #for letter in range(65,91):
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
        #how_label = QLabel("For your security, clips from other PasteBeam users are automatically blocked without notice. To unblock a friend, add his email to your contacts list here. Likewise, for him to receive your clips, he must add your login email to his own contacts list.")
        #how_label.setWordWrap(True)
        
        self.contacts_layout = QVBoxLayout()
        #self.contacts_layout.addWidget(how_label)
        self.contacts_layout.addWidget(self.add_user_widget)
        self.contacts_layout.addWidget(self.contacts_list_widget)
        self.contacts_layout.addWidget(self.okcancel_widget)
        
    def onDeleteClickedSlot(self):
        current_row = self.list_widget.currentRow()
        self.list_widget.takeItem(current_row)
                
class FaderWidget(QWidget):

    def __init__(self, old_widget, new_widget, duration = 333):
    
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
        self.fader_widget = FaderWidget(self.currentWidget(), self.widget(index), self.duration) #does not work as a mixin, as self.currentWidget needs to be a subclass of QStackedWidget
        QStackedWidget.setCurrentIndex(self, index)
    def setFadeDuration(self, duration):
        self.duration = duration
        
class CommonListWidget(QListWidget, WaitForSignalDialogMixin):
    def __init__(self, parent = None):
        super(CommonListWidget, self).__init__(parent)
        self.parent = parent
        self.main = parent.main
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel) #http://stackoverflow.com/questions/2016323/qt4-is-it-possible-to-make-a-qlistview-scroll-smoothly
        
        self.all_enable_disable_action_methods = []
        self.setMouseTracking(True)
        self.viewportEntered.connect(self.onMouseEnter)
        self.itemPressed.connect(self.onItemPressedSlot) #ITEM CLICK DOES NOT WORK USE PRESSED FUCK!!

    def onMouseEnter(self):
        "So that any click outside of an item will disable all context items"
        for each in self.all_enable_disable_action_methods:
            each[1]()

    def onItemPressedSlot(self, i):
        "So that any click of an item will enable all context items"
        self.parent.onTabChangedSlot(self.index) #hide alert icon in tab when clicking on an item
        for each in self.all_enable_disable_action_methods:
            each[0]()
        
    def doCommon(self):
        self.contacts_list = set([])
        
        self.doStyling()
        #delete action        
        self.doCopyAction()
        
        self.doShareAction()
        
        self.doUncommon() #do uncommon here
        
        self.doDeleteAction() #Put delete last
        
        self.itemDoubleClicked.connect(self.onItemDoubleClickSlot) #textChanged() is emited whenever the contents of the widget changes (even if its from the app itself) whereas textEdited() is emited only when the user changes the text using mouse and keyboard (so it is not emitted when you call QLineEdit::setText()).

    def doStyling(self, status="Double-click an item to copy it, or right-click it for more options."):
        self.setIconSize(self.parent.icon_size) #http://www.qtcentre.org/threads/8733-Size-of-an-Icon #http://nullege.com/codes/search/PySide.QtGui.QListWidget.setIconSize
        self.setAlternatingRowColors(True) #http://stackoverflow.com/questions/23213929/qt-qlistwidget-item-with-alternating-colors
        self.setStatusTip(status)
        
    def doShareAction(self):
        self.share_action = QAction(QIcon("images/share.png"), "S&hare", self)
        self.addAction(self.share_action)
        self.all_enable_disable_action_methods.append((self.enableShareAction, self.disableShareAction))
        self.disableShareAction()

    def onShareSubMenuTriggeredSlot(self, action):
        email = action.text()
        share_item = self.currentItem()
        share_item_data = json.loads(share_item.data(QtCore.Qt.UserRole))

        #now get decryption keys
        clip_system = share_item_data["system"]
        if clip_system == "main":
            decryption_key = getLogin().get("password")
        elif clip_system == "share":
            pass #TODO decrypt public key encrypted random AES key
        elif clip_system == "alert": #cant share alerts yet
            return

        share_item_data["recipient"] = email
        share_item_data["decryption_key"] = decryption_key #RAW
        self.main.outgoingSignalForWorker.emit(
            {
                "question": "Share?",
                "data" : share_item_data
            }
        )
    def enableShareAction(self):
        if not self.contacts_list:
            self.share_action.setDisabled(True)
            #ADD bubble explaining why
        else:
            self.share_action.setDisabled(False)
            share_sub_menu = QMenu()
            share_sub_menu.triggered.connect(self.onShareSubMenuTriggeredSlot)
            for name in sorted(self.contacts_list):
                share_sub_menu.addAction(name)
            self.share_action.setMenu(share_sub_menu)


    def disableShareAction(self):
        self.share_action.setDisabled(True)
    
    def doCopyAction(self):
        self.copy_action = copy_action = QAction(QIcon("images/copy.png"), "&Copy", self)
        copy_action.triggered.connect(self.onCopyActionSlot)
        self.addAction(copy_action)
        separator = QAction(self)
        separator.setSeparator(True)
        self.addAction(separator)
        self.all_enable_disable_action_methods.append((self.enableCopyAction, self.disableCopyAction))
        self.disableCopyAction() #start off disable bc nothing is selected yet
        
    def enableCopyAction(self):
        self.copy_action.setDisabled(False)
    
    def disableCopyAction(self):
        self.copy_action.setDisabled(True)
        
    def onCopyActionSlot(self):
        self.onItemDoubleClickSlot(self.currentItem())
    
    def doDeleteAction(self):
        separator = QAction(self)
        separator.setSeparator(True) #http://www.qtcentre.org/threads/21838-Separator-in-context-menu
        self.last_action = delete_action = QAction(QIcon("images/trash.png"), '&Delete', self) #delete.setText("Delete")
        delete_action.triggered.connect(self.onDeleteAction)
        self.addAction(separator)
        self.addAction(delete_action)
        self.all_enable_disable_action_methods.append((self.enableDeleteAction, self.disableDeleteAction))
        self.disableDeleteAction()
        
    def onDeleteAction(self):
        current_row, current_item = self.getClipDataByRow()
        remove_id = current_item["_id"]
        async_process = dict(
            question = "Delete?",
            data = {"remove_id":remove_id, "remove_row":current_row, "list_widget_name":self.__class__.__name__}
        )
        self.main.outgoingSignalForWorker.emit(async_process)
        
    def enableDeleteAction(self):
        self.last_action.setDisabled(False)
    
    def disableDeleteAction(self):
        self.last_action.setDisabled(True)
        
    def getClipDataByRow(self):
        current_row = self.currentRow()
        current_item = self.currentItem()
        current_item = json.loads(current_item.data(QtCore.Qt.UserRole)) #http://stackoverflow.com/questions/25452125/is-it-possible-to-add-a-hidden-value-to-every-item-of-qlistwidget
        return current_row, current_item
    """
    @staticmethod
    def convertToDeviceClip(clip): #todo do this on server! more secure!
        #convert back to device clip
        clip.pop("_id", None) #this is an id from an old clip from server. must remove or else key error will occur on server when trying to insert new clip
        clip["system"] = "main"
        return clip
    """
        
    def onItemDoubleClickSlot(self, double_clicked_item):
        
        #current_item = self.item(0)
        #current_clip = json.loads(current_item.data(QtCore.Qt.UserRole))
        
        double_clicked_data = json.loads(double_clicked_item.data(QtCore.Qt.UserRole))
        
        hash, prev = double_clicked_data["hash"], self.main.previous_hash
        
        if hash == prev:
            self.main.onSetStatusSlot(("already copied","warn"))
            return
            
        #container name is already in double_clicked_clip
        
        #double_clicked_clip = self.convertToDeviceClip(double_clicked_clip)
        
        self.main.onSetNewClipSlot(double_clicked_data)
        
        #self.previous_hash = hash #or else onClipChangeSlot will react and a duplicate new list item will occur.

class AlertListWidget(CommonListWidget):
    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.parent = parent
        self.main = parent.main
        self.index = 3
        self.doStyling(status="Right-click an item for more options.")

        self.doUncommon() #do uncommon here

        self.doDeleteAction() #Put delete last

    def doUncommon(self):
        self.doAcceptInviteAction()
        
    def doAcceptInviteAction(self):
        self.accept_invite_action = QAction(QIcon("images/ok.png"), "&Accept invite", self)
        self.accept_invite_action.triggered.connect(self.onAcceptInviteAction)
        
        self.all_enable_disable_action_methods.append((self.enableAcceptInviteAction, self.disableAcceptInviteAction))
        self.disableAcceptInviteAction()
        
    def onAcceptInviteAction(self):
        print "INVITE ACTION"
        current_row, current_item = self.getClipDataByRow()
        if not current_item["clip_type"] == "invite":
            return
        email = current_item["host_name"]
        
        self.showWaitForSignalDialog("Accept?", {"email":email}, "could not accept invitation", success_msg = False)
        
    def addAcceptInviteAction(self):
        self.insertAction(self.last_action, self.accept_invite_action)
        
    def removeAcceptInviteAction(self):
        self.removeAction(self.accept_invite_action)
        
    def enableAcceptInviteAction(self):
        self.accept_invite_action.setDisabled(False)
    
    def disableAcceptInviteAction(self):
        self.accept_invite_action.setDisabled(True)

    def onItemPressedSlot(self, clicked_item):
        super(self.__class__, self).onItemPressedSlot(clicked_item)
        self.removeAcceptInviteAction()
        clicked_alert = json.loads(clicked_item.data(QtCore.Qt.UserRole))
        if clicked_alert["clip_type"] == "invite":
            self.addAcceptInviteAction()
    
class StarListWidget(CommonListWidget):
    def __init__(self, parent = None):
        super(self.__class__, self).__init__(parent)
        self.index = 1
        self.doCommon()
    def doUncommon(self):
        pass
        
class MainListWidget(CommonListWidget):
    
    def __init__(self, parent = None):
        super(self.__class__, self).__init__(parent)
        self.index = 0
        self.doCommon()
    
    def doUncommon(self):
        self.doStarAction()

    def doStarAction(self):
        #star action
        self.star_action = star_action = QAction(QIcon("images/star.png"), '&Star', self)
        star_action.triggered.connect(self.onAddStarAction)
        self.addAction(star_action)

        self.all_enable_disable_action_methods.append((self.enableStarAction, self.disableStarAction))
        self.disableStarAction()
        
    def enableStarAction(self):
        self.star_action.setDisabled(False)
    
    def disableStarAction(self):
        self.star_action.setDisabled(True)
        
    def onAddStarAction(self):
        current_row, current_item = self.getClipDataByRow()
        del current_item["_id"]
        async_process = dict(
            question = "Star?",
            data = current_item
        )
        self.main.outgoingSignalForWorker.emit(async_process)
        
class FriendListWidget(CommonListWidget):
    def __init__(self, parent = None):
        super(self.__class__, self).__init__(parent)
        self.index = 2
        self.doCommon()
    def doUncommon(self):
        pass
        
class PanelTabWidget(QTabWidget):
    def __init__(self, icon_size, parent):
        super(self.__class__, self).__init__(parent)
        self.main=parent
        self.icon_size=icon_size
        self.doSearchWidget()
        self.doPanels()
        self.addPanels()

        self.currentChanged.connect(self.onTabChangedSlot)

    def onTabChangedSlot(self, index):
        if index == 0:
            self.setTabIcon(0,QIcon("images/devices.png"))
        if index == 1:
            self.setTabIcon(1,QIcon("images/star.png"))
        if index == 2:
            self.setTabIcon(2,QIcon("images/friends.png"))
        if index == 3:
            self.setTabIcon(3,QIcon("images/bulb.png"))

    def onChangeTabIconSlot(self, tabs_affected):
        if "starred" in tabs_affected:
            new_icon_tab = 1
        elif "alert" in tabs_affected:
            new_icon_tab = 3
        elif "main" in tabs_affected:
            new_icon_tab = 0
        elif "share" in tabs_affected:
            new_icon_tab = 2

        self.setTabIcon(new_icon_tab,QIcon("images/new.png"))

    def doSearchWidget(self):
        self.search = QLineEdit()
        self.search.textEdited.connect(self.onSearchEditedSlot)
        search_tip = "Search through your items (preview text only)."
        self.search.setStatusTip(search_tip)
        self.search.setPlaceholderText("Search text...")
        """
        search_icon = QLabel() #http://www.iconarchive.com/show/super-mono-3d-icons-by-double-j-design/search-icon.html
        pmap = QPixmap("images/find.png")
        pmap = pmap.scaledToWidth(32, QtCore.Qt.SmoothTransformation)
        search_icon.setPixmap(pmap)
        search_icon.setStatusTip(search_tip)
        """
        
    def onSearchEditedSlot(self, written):
        for list_widget in self.panels:
            items = [] #http://stackoverflow.com/questions/12087715/pyqt4-get-list-of-all-labels-in-qlistwidget
            for index in xrange(list_widget.count()):
                items.append(list_widget.item(index))

            is_blank = not bool(written) #unhide when written is blank

            for item in items:
                if is_blank:
                    item.setHidden(False) #unhide all
                else:
                    item_data = json.loads(item.data(QtCore.Qt.UserRole))

                    unsearchable_types = ["screenshot"]
                    if item_data["clip_type"] in unsearchable_types:
                        item.setHidden(True)
                        continue

                    any_match = False
                    if item_data["clip_type"] == "files":
                        for each_display in item_data["clip_display"]:
                            #print each_display
                            if written.upper() in each_display.replace("._folder", "").upper():
                                any_match = True
                    elif written.upper() in item_data["clip_display"].upper(): #make compatible with files clip display #TODO only search in searchable html class
                        any_match = True

                    if any_match:
                        item.setHidden(False)
                    else:
                        item.setHidden(True)
    
    def doPanels(self):
            
        self.main_list_widget = MainListWidget(self)
        
        self.star_list_widget = StarListWidget(self)
        
        self.friend_list_widget = FriendListWidget(self)
        
        self.alert_list_widget = AlertListWidget(self)
                
        self.panels = [self.main_list_widget, self.star_list_widget, self.friend_list_widget, self.alert_list_widget]
        #devices star friends
    def addPanels(self):
        self.addTab(self.main_list_widget, QIcon("images/devices"), "Devices")
        self.addTab(self.star_list_widget, QIcon("images/star"), "Bookmarks")
        self.addTab(self.friend_list_widget, QIcon("images/friends"), "Friends")
        #self.addTab(QWidget(), QIcon("images/bulb"), "Alerts")
        self.addTab(self.alert_list_widget, QIcon("images/bulb"), "Alerts")
        self.setCornerWidget(self.search)
        
    def onIncommingDelete(self,location):
        list_widget_name, remove_row = location
        
        if list_widget_name == "MainListWidget":
            self.main_list_widget.takeItem(remove_row) #POSSIBLE RACE CONDITION
        elif list_widget_name == "StarListWidget":
            self.star_list_widget.takeItem(remove_row)
        elif list_widget_name == "FriendListWidget":
            self.friend_list_widget.takeItem(remove_row)        
        elif list_widget_name == "AlertListWidget":
            self.alert_list_widget.takeItem(remove_row)

    def onContactsListIncomming(self, contacts_list):
        for each_list_widget in self.panels[:-1]: #everything but alerts
            each_list_widget.contacts_list = set(contacts_list)
            each_list_widget.enableShareAction()
            
    def clearAllLists(self):
        for each in self.panels:
            each.clear()
        
    def getMatchingContainerForHash(self, hash):
        hash_to_container = {}
        for list_widget in self.panels: #the reason why it's in panel tab widget
            row = 0
            while row < list_widget.count(): #http://www.qtcentre.org/threads/32716-How-to-iterate-through-QListWidget-items
                each_item = list_widget.item(row)
                item_data = each_item.data(QtCore.Qt.UserRole)
                json_data = json.loads(item_data)
                if not json_data["system"] in ["share", "alert"]: #DO NOT reuse shared clips, as they were encrypted with a random key, not user's password. Not reusing wil force the system to re-encrypt the container with user's password
                    hash_container_pair = {json_data["hash"] : json_data.get("container_name")}
                    hash_to_container.update(hash_container_pair)
                row+=1
            
        container = hash_to_container.get(hash) #or None
        del hash_to_container
        return container
        
class LockoutStackedWidget(StackedWidgetFader):
    #https://wiki.python.org/moin/PyQt/Fading%20Between%20Widgets
    #http://www.qtcentre.org/threads/30830-setCentralWidget()-without-deleting-prev-widget
    def __init__(self, parent = None):
        #QStackedWidget.__init__(self, parent)
        super(LockoutStackedWidget, self).__init__(parent) # it's better to use super method instead of explicitly calling the parent class, because the former allows to add another parent and "push up" the previous parent up the ladder without making any changes to the code here
    
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
        super(self.__class__, self).__init__(self.main, QtCore.Qt.CustomizeWindowHint) #remove the X button https://forum.qt.io/topic/4108/how-to-hide-the-dialog-window-close-button/6
        self.parent = parent
        self.parent.success =  False #always set false since self.success is shared
        self.label = label
        self.doLayout()
        self.setLayout(self.layout)
        self.bindEvents()
        self.exec_()
    def doLayout(self):
        wait_label = QLabel("<h1>%s...</h1>"%self.label.capitalize())
        self.layout = QVBoxLayout()
        self.layout.addWidget(wait_label)
    def bindEvents(self):
        self.main.ws_worker.closeWaitDialogSignalForMain.connect(self.onCloseWaitDialogSlot)
    def onCloseWaitDialogSlot(self, result):
        self.parent.success=result
        self.done(1)