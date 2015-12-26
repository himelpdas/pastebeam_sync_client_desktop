import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
QtCore.Signal = QtCore.pyqtSignal
QtCore.Slot = QtCore.pyqtSlot

import sys, multiprocessing, time
import itertools


class ConsumerClipboardEventListenerThread(QtCore.QThread):

    clipboard_changed_signal = QtCore.pyqtSignal()

    def __init__(self, evt, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.evt = evt

    def run(self):
        while 1:
            running = self.evt.get()
            if not running:  # poison pill technique
                break
            self.clipboard_changed_signal.emit()


class ProducerKillEventListenerThread(QtCore.QThread):

    kill_producer_signal = QtCore.pyqtSignal()

    def __init__(self, kill, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.kill = kill
        print "STARTING NEW KILL THREAD"

    def run(self):
        self.kill.wait()
        self.kill_producer_signal.emit()


class Consumer(QtGui.QMainWindow):

    def __init__(self, evt, kill, next_, app, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

        self.app = app
        self.evt = evt
        self.kill=  kill
        self.next_ = next_

        self.main_widget = QtGui.QTextEdit()
        self.setCentralWidget(self.main_widget)

        self.clipboard_event_thread = ConsumerClipboardEventListenerThread(self.evt)
        self.clipboard_event_thread.clipboard_changed_signal.connect(self.on_clipboard_changed)
        self.clipboard_event_thread.start()

        self.show()

        print multiprocessing.current_process().name


    def on_clipboard_changed(self):
        self.main_widget.append("faggot")

    def closeEvent(self, close_event):
        self.kill.set()
        self.evt.put(False)
        self.app.exit()


class Producer(QtGui.QMainWindow):
    def __init__(self, evt, kill, next_, app, *args, **kwargs):
        print "Starting new Producer"
        super(self.__class__, self).__init__(*args, **kwargs)
        self.app = app
        self.evt = evt
        self.kill = kill
        self.next_ = next_

        self.clipboard = app.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_data_changed)

        self.kill_event_thread = ProducerKillEventListenerThread(self.kill)
        self.kill_event_thread.kill_producer_signal.connect(self.terminate)
        self.kill_event_thread.start()

        self.kill_after(.25)
        print multiprocessing.current_process().name

    def terminate(self):
        print 'closing producer'
        self.next_.set()
        self.app.exit()  # http://stackoverflow.com/questions/8026101/correct-way-to-quit-a-qt-program

    def kill_after(self, second):
        second*=1000
        self.timer  = QtCore.QTimer(self)
        self.timer.setInterval(second)  # Throw event timeout with an interval of 1000 milliseconds
        self.timer.timeout.connect(self.terminate)  # this ensures clipboard stays alive
        self.timer.start()

    def on_clipboard_data_changed(self):
        self.evt.put(True)

def parallel_worker(evt, kill, next_, role):
    #evt, kill, role = args
    print "NEW SHIT my dessert eagle got a new grip"
    app = QtGui.QApplication(sys.argv)
    window = role(evt, kill, next_, app)
    app.exec_()

def start_process():
    print 'Starting', multiprocessing.current_process().name


if __name__ == "__main__":
    manager = multiprocessing.Manager()
    evt = manager.Queue()  # instead of multiprocessing.
    kill = manager.Event()
    next_ = manager.Event()
    args = itertools.chain(itertools.repeat((evt, kill, next_, Consumer), 1), itertools.repeat((evt, kill, next_, Producer)) )  # http://stackoverflow.com/questions/3211041/how-to-join-two-generators-in-python

    #args = args_generator()
    p = multiprocessing.Process(name="Consumer", target=parallel_worker, args=args.next())
    p.start()
    for i, each in enumerate(args):
        if kill.is_set():
            break
        next_.clear()
        q = multiprocessing.Process(name="Producer_%s" % i, target=parallel_worker, args=each)
        q.daemon = True
        q.start()
        qpid = q.pid
        print "Starting " + unicode(qpid)
        next_.wait()
        print "Next was set terminating " + unicode(qpid)
        q.terminate()
