
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provides common functions and variables for general use.
Control variables
"""
# pylint: disable=invalid-name,consider-using-f-string,consider-using-with
import sys
import os
import fcntl
import signal
import atexit
import ctypes
import time

isPydoc = (sys.argv[0].find('pydoc') >= 0)
notPydoc = not isPydoc

COMMON_SIGS = [signal.SIGINT, signal.SIGQUIT, signal.SIGHUP,
                signal.SIGPIPE, signal.SIGTERM, signal.SIGXFSZ]


##############################################################################
##   getMonoTime()
##############################################################################
if notPydoc:
    CLOCK_MONOTONIC_RAW = 4 # see <linux/time.h>

    # pylint: disable=missing-docstring
    class timespec(ctypes.Structure):
        _fields_ = [
            ('tv_sec', ctypes.c_long),
            ('tv_nsec', ctypes.c_long)
        ]

    librt = ctypes.CDLL('librt.so.1', use_errno=True)
    clock_gettime = librt.clock_gettime
    clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]

def getMonoTime():
    """ Returns montotonic time as floating point seconds; throws
        an OS error on (an unlikely) failure. """
    if notPydoc:
        ts = timespec()
        if clock_gettime(CLOCK_MONOTONIC_RAW, ctypes.pointer(ts)) != 0:
            errno_ = ctypes.get_errno()
            raise OSError(errno_, os.strerror(errno_))
        return ts.tv_sec + ts.tv_nsec * 1e-9
    return 1e-9

if notPydoc:
    referenceMonoTime = getMonoTime()

def getRunTime():
    """Returns run time of program as seconds (float)."""
    return getMonoTime() - referenceMonoTime

# def dt():
#   """Returns the monotonic time difference between now
#   and when the program started (i.e., referenceMonoTime)
#   as a %8.3f string.
#   """
#   if dtWallClock:
#       return TimeMach.day_ms()
#       # now = datetime.datetime.now()
#       # return "%02d%02d:%02d%02d%02d.%03d "%(now.month, now.day, now.hour,
#           # now.minute, now.second, now.microsecond/1000)
#   return '%8.3f: ' % getRunTime()

##############################################################################
##   FileLocker
##############################################################################
class FileLocker():
    """FileLocker to support running exclusively."""

    logname = os.environ.get('LOGNAME', 'binssb')

    def __init__(self, keyname=None):
        self.pid_str = '' # last locker pid string (could be self)
        self.auto_progname = None
        self.pidfile_fh = None # pidfile filehandle
        if not keyname:
            keyname = os.path.basename(sys.argv[0])
            if not keyname:  # if running python interactively
                keyname = 'python'
            self.auto_progname = keyname
        self.keyname = keyname
        self.folder = '/tmp/.' + self.logname + '.locks'
        self.path = os.path.join(self.folder, keyname + '.pidlock')
        if not os.path.isdir(self.folder):
            os.makedirs(self.folder, mode=0o700)
        self.pidfile_fh = None

    def lock(self):
        """File lock ... always non-blocking"""
        # pylint: disable=broad-except
        if self.pidfile_fh:
            return
        fh = self.pidfile_fh = open(self.path, "a+", encoding='utf-8')

        self.pid_str = 'UNK'
        fh.seek(0, 0)
        try:
            atexit.register(self.unlock)
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            # DB('lock ok')
        except IOError as dummy_exc:
            atexit.unregister(self.unlock)
            fh.seek(0, 0)
            pid_str = fh.read().strip()
            self.pid_str = pid_str if pid_str else 'UNK'
            fh.close()
            self.pidfile_fh = None
            state = 'DEAD'
            try:
                test_pid(self.pid_str)
                state = 'ALIVE'
            except Exception as dummy_exc:
                pass
            # pylint: disable=raise-missing-from
            raise SystemExit("ERROR: already locked (pid={} {}) [{}]".format(
                self.pid_str, state, self.path))
        self.pid_str = str(os.getpid())
        fh.truncate(0)
        fh.write(self.pid_str + '\n')
        fh.flush()

    def unlock(self):
        """For ctl-c and other exits, to avoid leaving the file locked."""
        fh = self.pidfile_fh
        # print('unlock fh:', fh)
        if fh:
            fh.truncate(0)
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            fh.close()
            self.pidfile_fh = None
            atexit.unregister(self.unlock)

##############################################################################
##   Exclusively
##############################################################################
class Exclusively():
    """Instantiate this object to run exclusively.
     - this object does not need to be kept instantiated
     - only one instance per key may be run, but you may call
        unlock_all() to force release of all lock and you may
        re-construct to re-lock
    """
    lockers = {} # singleton per key
    pid_str = ''

    @staticmethod
    def unlock_all():
        """Unlock every Exclusively lock."""
        for locker in Exclusively.lockers.values():
            locker.unlock()
            del locker

    @staticmethod
    def _lock(locker):
        try:
            locker.lock()
            pid_str = locker.pid_str
            exc_info = None
        except SystemExit as dummy_exc:
            pid_str = locker.pid_str
            exc_info = sys.exc_info()
        return exc_info, pid_str

    def __init__(self, progname=None, locker_class=FileLocker):

        locker = locker_class(progname)
        assert Exclusively.lockers.get(locker.keyname, None
                ) is None, 'existing Exclusively locker w key={locker.keyname)'
        Exclusively.lockers[locker.keyname] = locker

        exc_info, Exclusively.pid_str = self._lock(locker)
        # print('exc_info:', exc_info)

        if exc_info:
            dummy_etype, einst, tb = exc_info
            raise einst.with_traceback(tb)

##############################################################################
##   Test whether pid is apparently alive
##############################################################################
def test_pidE(pid):  # returns errinfo, too
    """ Check For the existence of a unix pid ... possibly a string. """
    try:
        pid = int(pid)
        os.kill(pid, 0)
    except OSError as exc:
        return False, exc.errno, os.strerror(exc.errno)
    else:
        return True, '', ''

def test_pid(pid):  # no error info
    """ Check For the existence of a unix pid ... possibly a string. """
    return test_pidE(pid)[0]

def runner(argv):
    """
    ToolCheck.py [S,H] - test the common utilities used by most modules.
    """
    class Tester():
        """TBD"""
        args = None
        def __init__(self):
            """TBD"""

        def main(self, argv):
            """The main loop ... mainly for testing.
            """
            # pylint: disable=import-outside-toplevel
            import argparse

            parser = argparse.ArgumentParser('test ToolBase')
            # parser.add_argument('-o', '--filename', default='', type=str,
                    # help='dump to given file (vs all in-memory test')
            parser.add_argument('--terse', action='store_true',
                    help='minimize output (i.e, Exclusively print only pid if locked)')
            parser.add_argument('test', nargs=1, help='choose test',
                    choices=('exclusively', 'flock'))
            parser.add_argument('testargs', nargs='*', help='provide any args to test')
            Tester.args = parser.parse_args(argv)

            test = Tester.args.test[0]
            if test == 'exclusively':
                self.exclusively(Tester.args.testargs)
            elif test == 'flock':
                self.test_flock()


        @staticmethod
        def exclusively(progs):
            """Test Exclusively():
             * given more than one name, test for alive.
             * given 0 names, lock 'ToolChest' for 30s
             * given 1 {name}, lock {name} for 30s
            """
            exit_code = 0
            if not progs:
                progs = ['ToolChest']
            for prog in progs:
                try:
                    Exclusively(prog)
                    if len(progs) > 1:
                        print(prog, 'DOWN')
                    else:
                        print(prog, 'got lock')
                except SystemExit:
                    print(prog, 'CANNOT lock:', Exclusively.pid_str)
                    exit_code = 1
                if len(progs) > 1:
                    Exclusively.unlock_all() # required for multiple tests
                else:
                    if not exit_code:
                        print('sleeping 30s...')
                        time.sleep(30)
            sys.exit(exit_code)

        @staticmethod
        def test_flock():
            """Test file locking."""
            flockers = [None]*10
            for n, flocker in enumerate(flockers):
                flocker = flockers[n] = FileLocker(f'test{n}')
                flocker.lock()
                if n % 2 == 0:
                    flocker.unlock()
                print(f'[flockers[{n}] locked:', bool(flocker.pidfile_fh))

            flocker = FileLocker('test')
            while True:
                for n in range(1000):
                    try:
                        flocker.lock()
                        break
                    except SystemExit as dummy_exc:
                        # print('EXC:', str(dummy_exc))
                        if n == 0:
                            print('waiting on:', flocker.pid_str)
                        time.sleep(0.05)
                        continue
                print('got flock')
                time.sleep(1.0)
                print('unlocking ...')
                flocker.unlock()  # expecting to always work
                time.sleep(0.1)

    Tester().main(argv)
