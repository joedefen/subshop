#!/usr/bin/env python3
"""
`CustLogger` provide a customized interface to the standard python logging system.
Normally, it is usad as if named `lg`.  It is expected that:

    - main calls lg.setup() very early (before any logging)
    - non-main modules just call static methods (e.g., lg.db()) to
      log messages; the static methods invoke the singleton logger
      `lg.logger`;
    - if you log before logging has been established, then you
      are using a default logging to the console only with
      the level set to 'INFO' (meaning everything 'normal' is printed).

To set the log level using argparse, do something like:

    from CustLogger import CustLogger as lg
    parser.add_argument('-V', '--log-level', choices=lg.choices,
        default='INFO', help='set logging/verbosity level [dflt=INFO]')
    ...
    lgset(level=args.log_level)

These new methods to log text are added:
    - lg.pr() to print raw (w/o time and other adornment)
    - lg.warn() eqivalant to lg.warning()
    - lg.crit() eqivalant to lg.critical()
    - lg.err() eqivalant to lg.error()
    - lg.db() eqivalant to lg.debug()
    - lg.tr1() ... lg.tr9() to trace (at lower levels than debug)

NOTE:
    - the "message" has full print semantics rather than the oddball
      log message semantics.
    - you must use the `lg.` methods; e.g., logging.pr() is not defined
    - if you let up a log file (aka 'lgfile'), then logs go to both stdout
      and the lgfile unless to_stdout=False
        * if lg is relative and lgdir is given, then lgfile
          becomes "{lgdir}/{progname}.txt"
        * lgfile is none but lgdir is not, lgfile becomes "{lgdir}/{progname}.txt"
        * if lgfile is an absolute path, the directory is created if needed;
        * if the above rules do not create an absolute path, then lgfile/lgdir
          is ignored.
    - unless on python 3.8+, the file/lineno will be wrong when logged

"""
# pylint: disable=invalid-name,global-statement,protected-access,broad-except
# pylint: disable=too-many-arguments
import os
import sys
import re
from types import SimpleNamespace
from io import StringIO
import logging
from logging.handlers import RotatingFileHandler

def parse_mixed_args(parser, args=None):
    """This version of parse args allows intermixing if on Python 3.7 or greater."""
    can_intermix = bool(10*sys.version_info.major + sys.version_info.minor >= 37)
    opts = parser.parse_intermixed_args(args) if can_intermix else parser.parse_args(args)
    return opts

class CustLogger:
    """TBD"""
    logger = None       # the singleton logger
    log_to_stdout = False # are we logging to stdout?
    choices = ('TR9', 'TR8', 'TR7', 'TR6', 'TR5', 'TR4', 'TR3', 'TR2', 'TR1',
            'DB', 'DEBUG', 'INFO', 'WARN', 'WARNING', 'ERR', 'ERROR', 'CRIT', 'CRITICAL')
    lvls = {}   # dictionary of loglevels keyed by name
    data = SimpleNamespace() # persistent (mostly constant) data in namespace
    # check whether python3.8+ and supporting "stacklevel"
    has_stacklevel = bool(10*sys.version_info.major + sys.version_info.minor >= 38)

    @staticmethod
    def _log(methodname, *args, **kwargs):
        """TBD"""
        if CustLogger.log_to_stdout:
            # NOTE: this forces a BrokenPipeError that is NOT supressed by
            # the frigging logging system (w/o this, the program will not quit).
            sys.stdout.flush()

        method = getattr(CustLogger.logger, methodname)
        assert method and callable(method)
        sio = StringIO()
        kwargs2 = {'stacklevel': 3} if CustLogger.has_stacklevel else {}
        for key in ('exc_info', 'stack_info', 'stacklevel', 'extra'):
            val = kwargs.pop(key, None)
            if key == 'stacklevel' and not CustLogger.has_stacklevel:
                continue # stacklevel not supported yet; so omit it
            if val:
                kwargs2[key] = val + 3 if key == 'stacklevel' else val
        kwargs = {k: v for k, v in kwargs.items() if k not in ('file', 'end')}
        print(*args, **kwargs, file=sio, end='')
        method(sio.getvalue(), **kwargs2)

    def __getattr__(self, name):
        ''' will only get called for undefined attributes '''
        # warnings.warn('No member "%s" contained in settings config.' % name)
        return ''

#   @staticmethod
#   def db(message, *args, **kwargs):
#       """TBD"""
#       CustLogger.log(logging.DB, message, *args, **kwargs)

    @staticmethod
    def setup(level=logging.INFO, lgfile=None, lgdir=None, maxBytes=500*1024,
            backupCount=1, to_stdout=True):
        """TBD"""
        ## import traceback  # for double logging debugging
        ## print(f'+ lg.setup({level}, {lgfile}, {maxBytes}, {backupCount}, {to_stdout}) from:')
        ## traceback.print_stack()

        if to_stdout:
            CustLogger.log_to_stdout = True

        if not CustLogger.lvls:
            CustLogger._setup_once()

        if not isinstance(level, int):
            level_raw = level.upper()
            level = CustLogger.lvls.get(level_raw, None)
            if level is None:
                print(f'WARNING: CustLogger.lgsetup() given unknown level ({level_raw})')
                level = logging.INFO
        CustLogger.data.dflt_level = level

        # OVERRIDE FROM ENV
        env_loglevel = os.environ.get('LOGLEVEL', '').upper()
        if env_loglevel:
            level = CustLogger.lvls.get(env_loglevel, None)
            if level is not None:
                CustLogger.data.dflt_level = level

        CustLogger.data.handlers = []
        CustLogger.data.out_handler = CustLogger.data.file_handler = None

        if lgfile or lgdir:
            if not lgfile:
                lgfile = os.path.basename(sys.argv[0]) + '.txt'
            if lgfile and not os.path.isabs(lgfile) and lgdir:
                lgfile = os.path.join(lgdir, lgfile)
            if not lgfile or not os.path.isabs(lgfile):
                lgfile, lgdir = None, None
            else:
                lgdir = os.path.dirname(lgfile)
                try:
                    CustLogger.data.lgdir = lgdir
                    os.makedirs(lgdir, exist_ok=True)
                except Exception as exc:
                    lgfile, lgdir = None, None
                    print(f'ERROR: lgsetup() cannot mkdirs(({lgdir}) [{exc}]')

        if lgfile:
            try:
                CustLogger.data.file_handler = RotatingFileHandler(
                        os.path.join(lgdir, os.path.basename(lgfile)),
                        maxBytes=maxBytes, backupCount=backupCount)
                CustLogger.data.handlers.append(CustLogger.data.file_handler)
            except Exception as exc:
                lgfile, lgdir = None, None
                print(f'ERROR: lgsetup() cannot establish log file ({lgfile}) [{exc}]')

        if to_stdout or not lgfile:
            CustLogger.data.out_handler = logging.StreamHandler(sys.stdout)
            CustLogger.data.handlers.insert(0, CustLogger.data.out_handler)


        CustLogger.data.raw_formatter = logging.Formatter(None)
        CustLogger.data.cooked_formatter = logging.Formatter(
                CustLogger.data.stdfmt, CustLogger.data.datefmt)

        if not CustLogger.logger:
            CustLogger.logger = logging.getLogger('CustLogger')
            CustLogger.logger.propagate = False  # Fixes double logging (good grief)

        CustLogger.logger.handlers = []
        for handler in CustLogger.data.handlers:
            CustLogger.logger.addHandler(handler)
        CustLogger.logger.setLevel(CustLogger.data.dflt_level)
        CustLogger._set_cooked()
        # print('CustLogger.logger.handlers:', CustLogger.logger.handlers, '\n')
        return CustLogger.logger

    @staticmethod
    def set_stdout(enable=True):
        """This controls whether to use stdout at run-time."""
        if (hasattr(CustLogger.data, 'out_handler') and hasattr(CustLogger.data, 'file_handler')
                and CustLogger.data.out_handler and CustLogger.data.file_handler):
            CustLogger.data.handlers = [CustLogger.data.file_handler]
            if enable:
                CustLogger.data.handlers.insert(0, CustLogger.data.out_handler)

    @staticmethod
    def _set_cooked():
        for handler in CustLogger.data.handlers:
            handler.setFormatter(CustLogger.data.cooked_formatter)
            handler.setLevel(CustLogger.data.dflt_level)

    @staticmethod
    def _set_raw():
        for handler in CustLogger.data.handlers:
            handler.setFormatter(CustLogger.data.raw_formatter)
            handler.setLevel(CustLogger.data.dflt_level)

    @staticmethod
    def _setup_once():
        """TBD"""

        def add_logging_level(levelName, levelNum, methodName=None, raw=False):
            """
            Comprehensively adds new logging level to the `logging` module and the
            currently configured logging class.

            - `levelName` becomes an attribute of the `logging` module with the value
            `levelNum`.
            - `methodName` becomes a method for both `logging` and the class returned by
            `logging.getLoggerClass()` (usually just `logging.Logger`).
            If `methodName` is not specified, `levelName.lower()` is used.

            To avoid accidental clobberings of existing attributes, this method will
            raise an `AttributeError` if the level name is already an attribute of the
            `logging` module or if the method name is already present

            Example
            -------
            >>> add_logging_level('TRACE', logging.DEBUG - 5)
            >>> logging.getLogger(__name__).setLevel("TRACE")
            >>> logging.getLogger(__name__).trace('that worked')
            >>> logging.trace('so did this')
            >>> logging.TRACE
            5

            """
            if not methodName:
                methodName = levelName.lower()

            # if hasattr(logging, levelName):
                # raise AttributeError('{} already defined in logging module'.format(levelName))
            # if hasattr(logging, methodName):
                # raise AttributeError('{} already defined in logging module'.format(methodName))
            # if hasattr(logging.getLoggerClass(), methodName):
                # raise AttributeError('{} already defined in logger class'.format(methodName))

            # This method was inspired by the answers to Stack Overflow post
            # http://stackoverflow.com/q/2183233/2988730, especially
            # http://stackoverflow.com/a/13638084/2988730
            def log4level(self, message, *args, **kwargs):
                if self.isEnabledFor(levelNum):
                    CustLogger.data.handlers[0].acquire()
                    CustLogger._set_cooked()
                    self._log(levelNum, message, args, **kwargs)
                    CustLogger.data.handlers[0].release()

            def log4levelraw(self, message, *args, **kwargs):
                # self.critical(message, *args, **kwargs)
                if self.isEnabledFor(levelNum):
                    CustLogger.data.handlers[0].acquire()
                    CustLogger._set_raw()
                    self._log(levelNum, message, args, **kwargs)
                    CustLogger.data.handlers[0].release()

            def log2singleton(message, *args, **kwargs):
                CustLogger._log(methodName, message, *args, **kwargs)

            # def log2root(message, *args, **kwargs):
                # logging.log(levelNum, message, *args, **kwargs)

            logging.addLevelName(levelNum, levelName)
            setattr(logging, levelName, levelNum)
            setattr(logging.getLoggerClass(), methodName,
                    log4levelraw if raw else log4level)
            setattr(CustLogger, levelName, levelNum)
            setattr(CustLogger, methodName, log2singleton)
            # setattr(logging, methodName, log2root)


        ########################################
        assert not CustLogger.logger, "CustLogger.lgsetup() has already called"
        CustLogger.data.lgdir = None
        CustLogger.data.stdfmt = ('%(asctime)s.%(msecs)d %(levelname)-4s'
                + ' %(message)s [%(filename)s:%(lineno)d]')
        CustLogger.data.datefmt ='%Y-%m-%d:%H:%M:%S'

        add_logging_level('DEBUG', logging.DEBUG)
        add_logging_level('DB', logging.DEBUG)
        add_logging_level('PR', logging.CRITICAL + 2, raw=True)
        add_logging_level('TR0', logging.CRITICAL + 1)
        add_logging_level('CRITICAL', logging.CRITICAL)
        add_logging_level('CRIT', logging.CRITICAL)
        add_logging_level('ERROR', logging.ERROR)
        add_logging_level('ERR', logging.ERROR)
        add_logging_level('INFO', logging.INFO)
        add_logging_level('WARNING', logging.WARNING)
        add_logging_level('WARN', logging.WARNING)
        for trlev in range(1, 10):
            add_logging_level(f'TR{trlev}', logging.DEBUG - trlev)

        for attr, val in vars(logging).items():
            if re.match(r'^[A-Z][A-Z0-9]*$', attr) and isinstance(val, int):
                CustLogger.lvls[attr] = val
                # print('LEVEL:', attr, val)


if not CustLogger.logger:
    CustLogger.setup(level='INFO')

def runner(argv):
    """Simple tests CustLogger with various lg.xyz(...) calls."""
    # pylint: disable=import-outside-toplevel
    import argparse
    lg = CustLogger  # as if: from CustLogger import CustLogger as lg
    parser = argparse.ArgumentParser()
    parser.add_argument('-V', '--log-level', choices=lg.choices,
            default='TR9', help='set logging/verbosity level [dflt=TR9]')
    opts = parser.parse_args(argv)

    lg.tr8('tr8: pre-setup:', 'does not go to file')

    lg.setup(lgfile='my_log.log', level=opts.log_level)

    lg.db('db: This is a debug log', 'with args and STACK:', stack_info=True)
    lg.info("info: This is an info log")
    lg.crit("crit: This is critical")
    lg.error("error: An error occurred")
    lg.error("err: An error occurred")
    lg.tr1('tr1: level 1 trace')
    lg.tr9('tr9: level 9 trace')
    lg.pr("pr: This is raw")
    lg.pr("pr: An error occurred with raw")
    lg.debug("debug: This is a debug log")
    lg.db("db: This is a debug log")
    lg.info("info: This is an info log")
    lg.crit("crit: This is critical")
    lg.tr1('tr1: level 1 trace')
    lg.tr9('tr9: level 9 trace')
    lg.crit("crit: This is crit")
    lg.critical("critical: This is crit")
    lg.err("err: An err occurred")
    lg.logger.info('logger info: using logger w STACK', stack_info=True)
