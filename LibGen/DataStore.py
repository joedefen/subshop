#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A "DataStore" is tree of OrderedDict none-leaf nodes and leaf notes
of arbitrary type (although must be YAML compliant).
 - a DataStore is disk persistent as YAML file
"""
# pylint: disable=invalid-name,broad-except,too-many-instance-attributes
# pylint: disable=consider-using-f-string
import os
import sys
import time
from io import IOBase
import traceback
from collections import OrderedDict
from ruamel.yaml import YAML
from LibGen.YamlDump import yaml_to_file
from LibGen.CustLogger import CustLogger as lg

yaml = YAML(typ='safe')
yaml.default_flow_style = False

class DataStore():
    """
    See module description.  The DataStore object is usually the
    base class for a specific DataStore.
    """
    # pylint: disable=too-many-arguments

    def __init__(self, filename, storedir, autoflush=True, warn_if_corrupt=False,
            flow_nodes=None, backup=False):
        """Create a DataStore.
        Provide the filename uniquely identifying the store, and
        optionally the directory for the store.  The directory
        defaults (given above)

        'autoflush' persists all modification immediately;  if disabled,
        then call flush() as needed (mods that are not flushed are lost).

        'warn_if_corrupt' will recreate the datastore if corrupted if
        starting anew is OK.
        """
        self.datastore = None
        self.filename = os.path.expanduser(storedir + '/' + filename)
        self._stat = (0, 0)  # size and time of underlying file (at last read/write)
        self.autoflush = autoflush  # write datastore on every modify?
        self.warn_if_corrupt = warn_if_corrupt     # recreate corrupted DB?
        self.dirty = False          # has unflushed changes?
        self.do_backup = backup
        self.flow_nodes = flow_nodes

    def get_filename(self, backup=False):
        """TBD"""
        return self.get_backupname() if backup else self.filename

    def get_backupname(self):
        """TBD"""
        return self.filename + '.bak'

    def get_tmpname(self):
        """TBD"""
        return self.filename + '.tmp'

    def _get_datastore(self):
        """
        Gets the current DataStore (as a python object).  If
        it does not exist, it will bring it from the persistent
        file (in YAML) or create any empty one.
        """
        if not isinstance(self.datastore, dict):
            self._read_datastore()
        return self.datastore

    def _update_stat(self, filehandle):
        if isinstance(filehandle, IOBase):
            stat = os.fstat(filehandle.fileno())
        else:
            stat = os.stat(filehandle)
        self._stat = (stat.st_size, stat.st_mtime)

    def is_changed(self):
        """Check if the datastore has change underneath us."""
        try:
            status = os.stat(self.filename)
        except OSError:
            # sometimes the file is gone while being written
            # ... catch it next time
            return False

        stat = (status.st_size, status.st_mtime)
        return stat != self._stat

    def refresh(self):
        """Read the database if the underlying file has a new
        timestamp and/or size.
        Return True if updated and re-read, else false.
        NOTE: the higher level app has to re-get objects, too,
        to complete any update.
        """
        if self.is_changed():
            if self.dirty:
                lg.warn('re-read {} overwriting "dirty" status'.format(
                    self.filename))
            self._read_datastore()
            return True
        return False

    def _read_datastore(self, try_backup=False):
        """
        Read the DataStore into memory (or the backup if opted).
        """
        op_str = ''
        try:
            with open(self.get_filename(try_backup), "r", encoding='utf-8') as fh:
                self._update_stat(fh)
                self.datastore = yaml.load(fh)
                self.dirty = False
                fh.close() # to be sure
            if not isinstance(self.datastore, dict):
                raise Exception('corrupt DataStore (not dict)')
            lg.tr5("len=", len(self.datastore) if self.datastore else 0)
            if try_backup:
                self.flush(force=True, backup=False) # fix non-backup
            elif self.do_backup:
                self.flush(force=True, backup=True) # make backup after successful read
            return True

        except Exception as exc:
            op_str = 'read' if isinstance(exc, IOError) else 'parse'
            dbname = os.path.basename(self.filename)

            if not try_backup and os.path.isfile(self.get_backupname()):
                lg.warn(f"cannot {op_str} {dbname} [{exc}], trying backup\n")
                if self._read_datastore(try_backup=True):
                    time.sleep(5) # a little time to see the error messages
                    return True

            if op_str == 'read' or self.warn_if_corrupt:
                lg.warn(f"cannot {op_str} {dbname} [{exc}], starting empty\n")
                time.sleep(5) # a little time to see the error messages
                self.datastore = OrderedDict()
                self.flush(force=True)
                return True

            lg.warn(f"cannot {op_str} {dbname} [{exc}], aborting\n")
            raise


    @staticmethod
    def _kys(key):
        """
        Keys are identified as list of parts or a string with '^'
        separating the parts.  This is a convenice method to
        convert to list if necessary.
        """
        return key.split('^') if isinstance(key, str) else key


    def flush(self, force=False, backup=False):
        """
        Flush current changes to disk conditionally on having
        unwritten modifications unless forced.
        """
        if self.dirty or force:
            with open(self.get_tmpname(), "w", encoding='utf-8') as fh:
                yaml_to_file(self.datastore, fh, flow_nodes=self.flow_nodes)
                self._update_stat(fh)
                fh.close() # to be sure
            lg.tr5('dirty' if self.dirty else 'forced')
            self.dirty = False
            os.replace(self.get_tmpname(), self.get_filename(backup))
        else:
            lg.tr5('skipped')

    def get(self, key, default=None):
        """
        Gets the node (leaf or not) given the key.
        Retuns None if it does not exist.
        """
        kys = self._kys(key)
        node = self._get_datastore()
        # lg.db("-0-get() kys:", kys)
        for ky in kys[:-1]:
            # lg.db("get() ky:", ky, 'node:', str(node))
            # lg.db("-1-get() ky:", ky, 'node:', type(node))
            node = node.get(ky, None)
            # lg.db("-2-get() ky:", ky, 'node:', type(node))
            if not node or not isinstance(node, dict):
                node = None
                break
        rv = node.get(kys[-1], default) if node else default
        lg.tr5("get key:", key, 'rv:', rv, type(rv))
        return rv


    def subkeys(self, key):
        """
        Given a key to a non-leaf node, gets the subkeys at that level.
        This is handy when the subkeys are variable.
        """
        node = self.get(key)
        if node and isinstance(node, dict):
            return list(node.keys())
        return None

    def nthSubkey(self, idx, key):
        """
        Given a key to a non-leaf node, gets the
        nth (i.e., 0, 1, ...) subkey at that level.
        This is handy when the subkeys are variable.
        """
        subkeys = self.subkeys(key)
        if subkeys and idx in range(len(subkeys)):
            return subkeys[idx]
        return None

    def put(self, key, value):
        """
        Stores a value with a given key.
          - intermediate nodes are created as needed.
          - NOTE: you cannot store a value atop a non-leaf node
        Returns true if it worked.
          - if it worked and the value is changed/added and
            autoflush is on, the DataStore save to disk.
        """
        rv = True # until proven otherwise
        kys = self._kys(key)
        try:
            node = self._get_datastore()
        except Exception:
            lg.pr(traceback.format_exc())
            node = None
        if node is None:
            lg.err('OMG: Failed to read grits (will redo everything)')
            node = {}
            rv = False
        subkey = ''
        for ky in kys[:-1]:
            subkey += ('^' if subkey else '') + ky
            nxt_node = node.get(ky)
            if nxt_node is None:
                nxt_node = node[ky] = OrderedDict()
                node = nxt_node
            elif isinstance(nxt_node, dict):
                node = nxt_node
            else:
                lg.err('subkey ({}) is a leaf node with value ({})',
                        subkey, str(nxt_node))
                nxt_node = node[ky] = OrderedDict()
                rv = False
        lg.tr5("put key:", key, 'val:', value)
        if node.get(kys[-1]) != value:
            node[kys[-1]] = value
            self.dirty = True
            if self.autoflush:
                self.flush()
        return rv

    def purge(self, key):
        """Purge either internal or leaf node.
        Returns True if anything removed, else False.
        """
        kys = self._kys(key)
        node, parNode = self._get_datastore(), None
        for ky in kys:
            if isinstance(node, dict):
                node, parNode = node.get(ky), node
            else:
                lg.tr5("not found: key:", key)
                return False
        del parNode[kys[-1]]
        self.dirty = True
        lg.tr5("del key:", key, 'oVal:', str(node))
        if self.autoflush:
            self.flush()
        return True


def runner(argv):
    """Tests DataStore using a test (i.e., TestCfg) store.
    NOTE: this creates and leaves:  data.d/test_cfg.yaml
    """

    class TestCfg(DataStore):
        """
        Specialized DataStore for test purposes.
        """
        def __init__(self, storedir=None):
            """TBD"""
            DataStore.__init__(self, filename='test_cfg.yaml',
                    storedir=storedir, autoflush=True)

    def test_cfg():
        """TBD"""
        cfg = TestCfg()
        screens = cfg.get('screens')
        if screens is None:
            lg.db('No screens ...')
            screens = OrderedDict()
            screens['year_min'] = 2018
            screens['fuzzy_min'] = 35
            screens['bitrate_min'] = 192
            screens['format_min'] = 3
            screens['media_min'] = 2
            screens['reltype_min'] = 3
            screens['tag_min'] = 3
            formats = screens['formats'] = OrderedDict()
            formats['FLAC'] = 3
            formats['MP3'] = 2
            formats['AAC'] = 0
            formats['AC3'] = 0
            formats['DTS'] = 0
            media = screens['media'] = OrderedDict()
            media['CD'] = 3
            media['DVD'] = 3
            media['Blu-Ray'] = 3
            media['WEB'] = 2
            media['Vinyl'] = 1
            media['Soundboard'] = 0
            media['SACD'] = 0
            media['DAT'] = 0
            media['Cassette'] = 0
            types = screens['reltypes'] = OrderedDict()
            types['Album'] = 3
            types['Anthology'] = 3
            types['Compilation'] = 3
            types['Soundtrack'] = 2
            types['EP'] = 2
            types['Single'] = 1
            types['Live Album'] = 1
            types['Remix'] = 0
            types['Bootleg'] = 0
            types['Interview'] = 0
            types['Mixtape'] = 0
            types['Demo'] = 0
            types['Concert Recording'] = 0
            types['DJ Mix'] = 0
            types['Unknown'] = 0
            tags = screens['tags'] = OrderedDict()
            tags['3a'] = 'jazz,smooth.jazz,ambient,orchestral,piano'
            tags['2a'] = 'blues,classical,country,folk,pop,swing'
            tags['1a'] = 'electro,electronic,soul,world.music'
            tags['0a'] = 'alternative.rock,dance,dubstep,experimental,folk.rock,fusion,'
            tags['0b'] = 'gothic.rock,hardcore.dance,hardcore.punk,hip.hop,kpop,latin,metal'
            tags['0c'] = 'post.punk,progressive.rock,pyschedelic.rock,rock,score,techno,trance'
            lg.db('Writing screens ...')
            cfg.put('screens', screens)
        else:
            lg.db('Current screens ...')
            yaml.dump(screens, sys.stdout)

    # pylint: disable=import-outside-toplevel
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-V', '--log-level', choices=lg.choices,
            default='TR5', help='set logging/verbosity level [dflt=TR5]')
    opts = parser.parse_args(argv)
    lg.setup(level=opts.log_level)
    test_cfg()
