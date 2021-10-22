#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generalized base classes for handling simple, yaml config files.
The supported config file must:
    - have a "root" dictionary
    - each key value must be:
        - a simple type (bool, int, float, string), or
        - a list of simple types, or
        - a dictionary with the same constraints as the root dictionary

A "template" defines the structure of the config file where:
    - whole template becomes the default config file if it does
      not exist, and
    - its values are the default values in case the keys do not exist
    - its default values define the acceptable types for config values

If a config file is loaded with key errors, then the config file will be
overwritten including the missing keys w default values and excluding
the extraneous keys.
    - each time a config file is overwritten, the old vesion will be
      moved to a file of the same name except adding a ".bak" suffix.

The loaded config file will have certain conversions:
    - its dictionaries are converted to SimpleNamespace's EXCEPT those
      dicts with variable keys
    - dash ('-') characters in keys are converted to underscores ('_')

"""

# pylint: disable=broad-except,too-many-arguments,too-many-instance-attributes
# pylint: disable=multiple-statements,using-constant-test,import-outside-toplevel

import os
import copy
import time
from io import IOBase
from types import SimpleNamespace
import traceback
from functools import reduce
import operator
import inspect
from ruamel.yaml import YAML, comments, scalarint, scalarfloat
from LibGen.YamlDump import yaml_dump
from LibGen.CustLogger import CustLogger as lg

yaml = YAML()
yaml.default_flow_style = False


class Internalize():
    """TBD"""
    def __init__(self, descr, templ_str, do_repairs=True):
        self.state = 'uninited'
        self.templ_str = templ_str
        self.templ_dict = None
        self.params = None
        self.key_errs = 0
        self.non_dflts = 0 # some values are non-default
        self.var_dicts = set()
        self.do_repairs = do_repairs
        self.descr = descr if descr else 'unk'
        self.flow_nodes = None # someday might support
        self._create_template()

    def _create_template(self):
        self.state = 'uninited'
        self.templ_dict = None
        try:
            self.templ_dict = yaml.load(self.templ_str)
            self.state = 'inited'
        except Exception as exc:
            lg.err(f'cannot load template for {self.descr} [{exc}]')
            for idx, line in enumerate(self.templ_str.splitlines()):
                lg.pr(f'{idx+1:4d}: {line}')
            raise  # this is fatal

    def _get_by_addr(self, addr):
        """Access a nested object in root by 'address' sequence."""
        return reduce(operator.getitem, addr, self.params)

    def _set_by_addr(self, addr, value, is_err=True):
        """Set a value in a nested object in 'params' by 'address' sequence."""
        if self.do_repairs and is_err:
            lg.warn(f'{self.descr}{addr} loaded with template default')
            if addr:
                self._get_by_addr(addr[:-1])[addr[-1]] = value
            else:
                self.params = value
        return self.do_repairs

    def _del_by_addr(self, addr):
        """Set a value in a nested object in 'params' by 'address' sequence."""
        if self.do_repairs:
            lg.warn(f'{self.descr}{addr} deleted [not in template]')
            del self._get_by_addr(addr[:-1])[addr[-1]]
        return self.do_repairs

    def cvt_to_namespaces(self):
        """TBD"""
        if isinstance(self.params, dict):
            self.params = self._dict_to_namespaces(addr=[], dict_val=self.params)
        elif isinstance(self.params, list):
            self.params = self._list_to_namespaces(addr=[], list_val=self.params)

    def _dict_to_namespaces(self, addr, dict_val):
        ndict_val = {}
        is_var_dict = bool(str(addr) in self.var_dicts)
        for key, val in dict_val.items():
            subaddr = addr + [key]
            nkey = key if is_var_dict else key.replace('-', '_')
            # lg.db(f'pre-dict_to_ns: key={key} T={type(val)} val={val}')
            if isinstance(val, dict):
                ndict_val[nkey] = self._dict_to_namespaces(subaddr, val)
                # lg.db(f'dict-dict_to_ns: nkey={nkey} val={ndict_val[nkey]}')
            elif isinstance(val, list):
                ndict_val[nkey] = self._list_to_namespaces(subaddr, val)
                # lg.db(f'list-dict_to_ns: nkey={nkey} val={ndict_val[nkey]}')
            else:
                # NOTE: SimpleNamespace does like some of the yaml complicated
                # type (e.g., ScalarFloat); so simplify...
                ndict_val[nkey] = self._pure_val(val)
                # lg.db(f'val-dict_to_ns: nkey={nkey} val={ndict_val[nkey]}')
        # lg.db(f'dict_to_ns: ndict_val={ndict_val}')
        return ndict_val if is_var_dict else SimpleNamespace(**ndict_val)

    def _list_to_namespaces(self, addr, list_val):
        for idx, val in enumerate(list_val):
            subaddr = addr + [idx]
            if isinstance(val, dict):
                list_val[idx] = self._dict_to_namespaces(subaddr, val)
            elif isinstance(val, list):
                list_val[idx] = self._list_to_namespaces(subaddr, val)
        return list_val

    @staticmethod
    def _pure_val(val, strip_comments=False):
        # pylint: disable=too-many-return-statements
        # lg.db('type(val):', type(val), 'val:', val)
        if isinstance(val, bool):
            return bool(val)
        if isinstance(val, float):
            # lg.db(f'_pure_val({val}) float type(val)={type(val)}')
            return float(val)
        if isinstance(val, int):
            # lg.db(f'_pure_val({val}) int type(val)={type(val)}')
            return int(val)
        if isinstance(val, str):
            # lg.db(f'_pure_val({val}) str type(val)={type(val)}')
            return str(val)
        if strip_comments:
            if isinstance(val, dict):
                for key, subval in val.items():
                    val[key] = Internalize._pure_val(subval)
                return dict(val)
            if isinstance(val, list):
                for idx, subval in enumerate(val):
                    val[idx] = Internalize._pure_val(subval)
                return list(val)
        return val

    def validate(self, params=None):
        """TBD"""
        self._create_template()
        self.params = params if params else self.params
        assert self.templ_dict and self.params, "cannot validate [invalid state]"
        self.key_errs, self.non_dflts, self.var_dicts = 0, 0, set()
        try:
            self._validate_dict(addr=[], templ_dict=self.templ_dict)
            if self.do_repairs:
                self.params, self.templ_dict = self.templ_dict, None
            return self.params
        except Exception as exc:
            lg.err(f'bad config: {exc}')
            traceback.print_exc()
            raise # this is fatal


    def _validate_dict(self, addr, templ_dict):
        # pylint: disable=too-many-branches
        params_dict = self._get_by_addr(addr)
        lg.tr8(f'_validate_dict addr={addr}\n   templ_keys={list(templ_dict.keys())}'
                '\n   type(params_dict)={type(params_dict)}')
        if not isinstance(params_dict, dict):
            raise TypeError(f'config{addr} should be dict')

        # variable_keys = bool(len(templ_dict) == 1 and list(templ_dict.keys())[0].startswith('*'))
        templ_keys = list(templ_dict.keys())
        is_var_keys = bool(str(templ_keys[0]).startswith('*'))

        if is_var_keys: # force them into the template
            while templ_dict:
                _, the_template_val = templ_dict.popitem()
            # pure_template_val = self._pure_val(the_template_val, strip_comments=False)
            for key in params_dict.keys():
                # templ_dict[key] = copy.deepcopy(pure_template_val)
                templ_dict[key] = copy.deepcopy(the_template_val)
            self.var_dicts.add(str(addr))

        else: # fixed keys ... check for superflous (incorrect or removed) keys in the params
            for key in params_dict.keys():
                if not isinstance(key, str):
                    if str(addr) not in self.var_dicts:
                        self.var_dicts.add(str(addr))
                        lg.info(f'added {addr} to var_dicts')
                if key not in templ_dict and ('?' + str(key)) not in templ_dict:
                    self.key_errs += 1
                    subaddr = addr + [key]
                    lg.warn(f'{self.descr}{subaddr} not in template')
                    if not self.do_repairs:
                        return None

        itemlist = list(templ_dict.items()) # plan for add/remove items in loop
        for key, templ_val in itemlist:
            lg.tr5(f'validating key={key} templ_val={templ_val} T={type(templ_val)}')
            key_optional = False
            if isinstance(key, str) and key.startswith('?'):
                templ_dict.pop(key)
                key, key_optional = key[1:], True
            subaddr = addr + [key]
            try:
                param_val = self._get_by_addr(subaddr)
            except KeyError:
                param_val = None
            lg.tr9(f'_validate_dict():{" optional" if key_optional else ""}'
                    f' subaddr={subaddr} key={key}'
                    f' T={templ_val} type(T)={type(templ_val)}'
                    f' D={param_val} type(D)={type(param_val)}')
            if param_val is None and key_optional:
                pass
            elif param_val is None:
                self.key_errs += 1
                if self.do_repairs:
                    templ_dict[key] = self._pure_val(templ_val)
                    lg.warn(f'{self.descr}{subaddr} missing [loaded with template default]')
                else:
                    lg.warn(f'{self.descr}{subaddr} missing')
                    return None
            elif isinstance(templ_val, dict):
                if not isinstance(param_val, dict):
                    raise TypeError(f'config{subaddr} should be dict')
                self._validate_dict(subaddr, templ_val)
            elif isinstance(templ_val, list):
                # lg.db(f'validate_list: templ_val={templ_val[0]} T={type(templ_val[0])}')
                ############### NOTE: not sure this restriction is required... but OK now
                if not isinstance(templ_val[0], (str, float, int)):
                    raise TypeError(f'template{subaddr + [0]} list not str/float/int')
                if not isinstance(param_val, list):
                    raise TypeError(f'config{subaddr} should be list')
                templ_type = type(templ_val[0])
                for idx, val in enumerate(param_val):
                    idxaddr = subaddr + [idx]
                    # idxparam_val = self._get_by_addr(idxaddr)
                    self._validate_type(idxaddr, val, templ_type)
                if templ_val != param_val or key_optional:
                    # lg.db(f'T={templ_val} != D={param_val}')
                    if self.do_repairs:
                        templ_dict[key] = param_val
                        self.non_dflts += 1
                        lg.tr3(f'{self.descr}{subaddr} has non-dflt value: {param_val}')
                    else:
                        return None
            else:
                if not isinstance(templ_val, (str, float, int)):
                    raise TypeError(f'template{addr} list not str/float/int')
                self._validate_type(subaddr, param_val, type(templ_val))
                if templ_val != param_val or key_optional:
                    if self.do_repairs:
                        templ_dict[key] = param_val
                        self.non_dflts += 1
                        lg.tr3(f'{self.descr}{subaddr} has non-dflt value:', param_val)
                    else:
                        return None
        return self.params

    @staticmethod
    def _validate_type(addr, param_val, templ_type):
        if templ_type == comments.CommentedOrderedMap:
            templ_type = dict
        elif templ_type == comments.CommentedSeq:
            templ_type = list
        elif templ_type == scalarint.ScalarInt:
            templ_type = int
        elif templ_type == scalarfloat.ScalarFloat:
            templ_type = float

        if templ_type == float:
            if not isinstance(param_val, (float, int)):
                raise TypeError(f'config{addr} should be float, not {type(param_val)}')
        elif not isinstance(param_val, templ_type):
            raise TypeError(f'config{addr} should be {templ_type}, not {type(param_val)}')


class YamlConfig(Internalize):
    """TBD"""
    is_first = True

    def __init__(self, filename, config_dir, templ_str=None, to_namespace=True,
            auto=True, dry_run=False):
        self.stat = 'uninited'
        abspath = os.path.abspath(config_dir)
        abspath = os.path.join(abspath, filename)
        self.abspath = os.path.expanduser(abspath)
        lg.tr3('YamlConfig(): abspath:', self.abspath)
        self.basename = os.path.basename(self.abspath)
        self.dry_run = dry_run
        self.to_namespace = to_namespace
        super().__init__(descr=self.basename, templ_str=templ_str)

        lg.tr3(f'YamlConfig.init({self.basename}) dry_run={self.dry_run}')
        self._stat = (0, 0)  # size and time of underlying file (at last read/write)
        self.state = 'inited'

        if YamlConfig.is_first:
            YamlConfig.is_first = False
            stack = inspect.stack()
            _, filename, _ = stack[len(stack)-1][0:3]
            auto = False if filename.endswith('run') else auto
            _, filename, _ = stack[1][0:3]

        if auto:
            self.load()
            self.validate_and_save()

    def load(self, from_str=None):
        """
        Read the YamlConfig into memory
        """
        try:
            if from_str:
                self.params = yaml.load(from_str)
            else:
                with open(self.abspath, "r", encoding='utf-8') as fh:
                    self._update_stat(fh)
                    self.params = yaml.load(fh)
            if not isinstance(self.params, dict):
                raise Exception(f'corrupt YamlConfig type={type(self.params)} (not dict)')

        except Exception as exc:
            op_str = 'read' if isinstance(exc, IOError) else 'parse'
            dbname = self.basename

            if isinstance(exc, FileNotFoundError):
                lg.info(f'creating defaulted "{self.abspath}"')
                try:
                    self.params, self.templ_dict = self.templ_dict, None
                    # lg.info('dumping self.params')
                    folder = os.path.dirname(self.abspath)
                    if not os.path.exists(folder):
                        os.makedirs(folder)
                    with open(self.abspath, "w+", encoding='utf-8') as fh:
                        yaml.dump(self.params, fh)
                except Exception:
                    lg.warn(f"cannot write {dbname} [{exc}], aborting\n")
                    lg.pr(traceback.format_exc())
                    raise
            else:
                lg.warn(f"cannot {op_str} {dbname} [{exc}], aborting\n")
                raise
        self.state = 'loaded'
        return self.params

    def validate_and_save(self, params=None, force=False):
        """Merge the params into the template, and then move the modified template
        to the params."""
        assert self.state in ('loaded', )
        params = params if params else self.params
        if super().validate(params) and (self.key_errs or force):
            lg.db(f'saving {self.descr}...')
            self.save()
        else:
            lg.tr3(f'not saving {self.descr} key_errs={self.key_errs} force={force}')
        if self.to_namespace:
            # lg.db('self.params BEFORE convert to namespace:\n')
            # yaml.dump(self.params, sys.stdout)
            self.cvt_to_namespaces()
        self.state = 'validated'

    def _update_stat(self, filehandle):
        if isinstance(filehandle, IOBase):
            stat = os.fstat(filehandle.fileno())
        else:
            stat = os.stat(filehandle)
        self._stat = (stat.st_size, stat.st_mtime)

    def refresh(self):
        """Read the database if the underlying file has a new
        timestamp and/or size.
        Return (self.params, True0 if updated and re-read, else (self.params, False).
        NOTE: the higher level app has to re-get objects, too,
        to complete any update.
        """
        params, state = self.params, self.state
        try:
            if self.is_changed():
                self.load()
                self.validate_and_save()
                return self.params, True
            return self.params, False
        except Exception as exc:
            self.params, self.state = params, state # leave in prior state
            lg.warn(f'cannot refresh {self.descr} [{exc}]')
            return self.params, False

    def is_changed(self):
        """Check if the datastore has change underneath us."""
        try:
            status = os.stat(self.abspath)
        except OSError:
            # sometimes the file is gone while being written
            # ... catch it next time
            return False

        stat = (status.st_size, status.st_mtime)
        return stat != self._stat

    def save(self):
        """Overwrite the config file with an updated version, saving the
        old file as a .bak copy"""
        tmpname = self.abspath + '.tmp'
        bakname = self.abspath + '.bak'
        with open(tmpname, "w", encoding='utf-8') as fh:
            yaml.dump(self.params, fh)
        saved_str = ''
        if os.path.isfile(self.abspath):
            if self.dry_run:
                saved_str = '; WOULD save .bak version'
            else:
                os.replace(self.abspath, bakname)
                saved_str = '; saved .bak version'
        if self.dry_run:
            lg.warn(f'WOULD update {os.path.basename(self.abspath)}{saved_str}')
        else:
            os.rename(tmpname, self.abspath)
            lg.warn(f'updated {os.path.basename(self.abspath)}{saved_str}')

    def generic_main(self, argv=None):
        """Generic main. This object constructed with auto=off.
         """
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('-V', '--log-level', choices=lg.choices,
            default='INFO', help='set logging/verbosity level [dflt=INFO]')
        parser.add_argument('-n', '--dry-run', action='store_true',
                dest='dry_run', help='enable "dry-run" mode so file not updated')
        parser.add_argument('--reset', action='store_true',
                help='reset config file to defaults')
        parser.add_argument('--loop', action='store_true',
                help='loop indefinitely and refresh when changed')
        args = parser.parse_args(argv)
        lg.setup(level=args.log_level)

        lg.info(f'args.dry_run={args.dry_run}')
        self.dry_run = False if args.reset else args.dry_run

        lg.info(f'configfile={self.abspath}')

        lg.pr(f'==== Loading {"template data" if args.reset else "config file"} ...')
        self.load(self.templ_str if args.reset else None)

        lg.pr(f'==== Validating and {"" if args.reset else "conditionally "}'
                'saving config file ...')
        self.validate_and_save(force=args.reset)

        lg.pr('==== Dumping loaded params ...')
        yaml_dump(self.params)
        lg.pr(f'NOTE: {self.key_errs} key repairs'
                f' and {self.non_dflts} non-dflt values')
        print_time = 0
        while args.loop:
            if time.time() - print_time > 15:
                lg.pr(f'Awaiting updated {self.descr}...')
                print_time = time.time()
            params, updated = self.refresh()
            if updated:
                lg.info(f'updated params from {self.descr} sucessfully')
                yaml_dump(params)
                print_time = 0
            time.sleep(0.5)

def no_runner():
    """NOTE: must test YamlConfig from derived ConfigXYZ classes."""
