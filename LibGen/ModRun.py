#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run the discover module tests, etc., via their runner() entry points
"""
# pylint: disable=broad-except
import argparse
import sys
import os
import re
import textwrap
import importlib
import inspect
from types import SimpleNamespace

import argparse

def main(caller_file, argv):
    """Run runner() functions in certain modules."""
    our_argv, runner_argv = splitargv(argv)
    # print('our_argv:', our_argv, 'runner_argv:', runner_argv)
    mods = get_modules(caller_file)  # key=filename (w/o .py), value={name:, doc:}
    # print('mods:', mods)
    commands = sorted(list(mods.keys()))

    descr = None
    if ('-h' in our_argv or '--help' in our_argv
            or not our_argv or our_argv[-1] not in commands):
        import_mods(mods) # note: some mods may be removed
        commands = sorted(list(mods.keys()))
        descr = f'\n{"-"*70}\nRuns module runner() function\n\n'
        for cmd in commands:
            ns = mods[cmd]
            descr += f'\n{"-"*70}\n{cmd}: [{ns.name}]\n'
            if ns.doc:
                descr += textwrap.indent(ns.doc, '   ') + '\n'


    parser = argparse.ArgumentParser(epilog=descr,
            formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('cmd', choices=commands)

    # parser.add_argument('targets', nargs='*', help='{test-args}')
    opts = parser.parse_args(our_argv)

    if not re.match(r'^Config[A-Z].*.py$', opts.cmd):
        # KLUDGE ALERT: Unless we are running on of the YamlConfig-based
        # modules, defeat the 1st YamlConfig constructor being special
        # which is required to test the YamlConfig-based modules.  YamlConfig
        # makes the 1s constructor special if the outermost program is named '*run'.
        from LibGen.YamlConfig import YamlConfig
        YamlConfig.is_first = False

    import_mods(mods, opts.cmd)
    if opts.cmd not in mods:
        print(f'\nSORRY: {opts.cmd} has no runner() function')
        sys.exit(15)

    ns = mods[opts.cmd]
    sys.argv[0] = f'{os.path.basename(sys.argv[0])} {opts.cmd}'
    ns.mod.runner(runner_argv)
    sys.exit(0)

def splitargv(argv):
    """Split argv into ours and theirs.  Ours ends with first non-option; e.g.,
        -h --help ConfigNanny -n
    splits:
        -h --help ConfigNanny <<--ours  theirs-->> -n
    """
    which, args = 0, [[], []]
    for arg in argv[1:]:
        args[which].append(arg)
        which = 1 if which or not arg.startswith('-') else 0
    return args[0], args[1]

def get_modules(caller_file, subdirs=None):
    """Get all the modules in the given LibFoo subdirs"""
    mods = {}
    caller_path = os.path.abspath(caller_file)
    # print('caller_path:', caller_path)
    if caller_path.endswith('subshop'):
        subdirs = ['LibSub', 'LibGen']
    mydir = os.path.dirname(caller_path)
    if not subdirs:
        subdirs = []
        with os.scandir(mydir) as entrys:
            for entry in entrys:
                if entry.is_dir() and re.match(r'^[A-Z][a-z]+[A-Z][a-z]+$', entry.name):
                    # print('added:', entry.name)
                    subdirs.append(entry.name)
    assert subdirs
    for subdir in subdirs:
        with os.scandir(os.path.join(mydir, subdir)) as entrys:
            for entry in entrys:
                name = entry.name
                if entry.is_file() and re.match(r'^[a-zA-Z]\w+.py$', name):
                    assert not name.startswith('_')
                    ns = SimpleNamespace(name=f'{subdir}.{name[:-3]}', mod=None, doc='')
                    mods[name[:-3]] = ns
    return mods

def import_mods(mods, key=None):
    """Import the given mods (in a dict of SimpleNamespaces)"""
    keys = [key] if key else sorted(list(mods.keys()), key=lambda x: mods[x].name)
    intentional_skips = set()

    for key in keys:
        ns = mods[key]
        msg = None
        try:
            ns.mod = importlib.import_module(ns.name)
            assert ns.mod
        except Exception as exc:
            msg = f'NOTE: cannot import {ns.name}) [{exc}]'

        try:
            if ns.mod:
                ns.doc = inspect.getdoc(ns.mod.runner)
        except Exception as exc:
            msg = f'NOTE: cannot getdoc({ns.name}.runner()) [{exc}]'

        try:
            if ns.mod and msg:
                inspect.getdoc(ns.mod.no_runner)
                intentional_skips.add(key)
                msg = None
        except Exception:
            pass

        if key not in intentional_skips and msg:
            print(msg)

        # print('key:', key, vars(ns))

    for key in intentional_skips:
        del mods[key]
    return mods
