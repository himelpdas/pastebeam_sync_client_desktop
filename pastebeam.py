from gevent import monkey; monkey.patch_all(thread=False)  # thread MUST equal False or else unexpected behavior will occur with multiprocess

from application_process import Consumer
from clipboard_process import Producer

import PyQt4.QtGui as PyQt4_QtGui
import PySide.QtGui as PySide_QtGui

import sys, multiprocessing
import itertools, sys


def parallel_worker(qapp, role, clip_change_queue, set_clip_queue, status_queue, kill_event, previous_hash,
                    **unshared):
    #clip_change_queue, kill_event, role = args
    app = qapp(sys.argv)
    window = role(app, clip_change_queue, set_clip_queue, status_queue, kill_event, previous_hash,
                  **unshared)
    app.exec_()


if __name__ == "__main__":
    #manager = multiprocessing.Manager()  # Done via networking. GEVENT fucks this up. Can't use patch_all(socket=False) because we need requests and urllib patched
    clip_change_queue = multiprocessing.Queue()  # Gevent fucks this up!! USE patch_all(thread=False), Also use SimpleQueue as gevent patches multiprocessing.Queue()
    set_clip_queue = multiprocessing.Queue()  # This will cause set_clup_queue.get() to hang without a context switch
    status_queue = multiprocessing.Queue()  # put() may block when a process suddenly terminates, must use put_nowait
    kill_event = multiprocessing.Event()
    next_producer = multiprocessing.Event()
    previous_hash = multiprocessing.Value("L",long(0))

    #args = args_generator()
    args = (clip_change_queue, set_clip_queue, status_queue, kill_event, previous_hash)
    args = itertools.chain(itertools.repeat((PyQt4_QtGui.QApplication, Consumer,) + args, 1),  # 1 means repeat once
                           itertools.repeat((PySide_QtGui.QApplication, Producer,) + args)  # repeat infinite
                           )  # http://stackoverflow.com/questions/3211041/how-to-join-two-generators-in-python

    p = multiprocessing.Process(name="Consumer", target=parallel_worker, args=args.next(),
                                kwargs=dict(next_producer = next_producer))
    p.start()

    for i, each in enumerate(args):
        if kill_event.is_set():
            break
        next_producer.clear()
        q = multiprocessing.Process(name="Producer_%s" % i, target=parallel_worker, args=each,
                                    kwargs=dict(next_producer = next_producer))
        #q.daemon = True
        q.start()
        qpid = q.pid
        print "Starting " + unicode(qpid)
        next_producer.wait(timeout = Producer.timeout)
        print "Next was set terminating " + unicode(qpid)
        #q.terminate()
    p.terminate()
    q.terminate()
    sys.exit(1)