#!/usr/bin/env python3
"""
Establish the folders for config/data/log files for all
the subshop commands/modules.
"""
# pylint: disable=invalid-name,global-statement

import os

_DEV_SUBSHOP_ENABLED = True  # enables subshop in ~/binsb

def _resolve_dir(env_name, dflt_dir):
    """Resolve a directory given the override env var and
    its default directory. And if '~' is used to indicate
    the home directory, then expand that."""
    folder = os.environ.get(env_name, dflt_dir)
    if folder is not None:
        return os.path.expanduser(folder)
    return None

def _resolve_root(env_name, dflt_dir):
    """IF the 'root_d' is set, then it establishes/overrides the
    other directories."""
    # special case for development / non-installed subshop
    folder = None
    if _DEV_SUBSHOP_ENABLED:
        dev_subshop = os.path.expanduser('~/binsb/subshop')
        if os.path.exists(dev_subshop):
            folder = os.path.dirname(dev_subshop)
    if not folder:
        folder = _resolve_dir(env_name, dflt_dir)
    if folder is None:
        return None
    global config_d, cache_d, log_d, model_d
    config_d = os.path.join(folder,'data.d')
    cache_d = os.path.join(folder,'tmp.d')
    log_d = os.path.join(folder,'log.d')
    model_d = folder
    return folder

# Resolve the folders for subshop's config/data/logs.
config_d = _resolve_dir('SUBSHOP_CONFIG_D', '~/.config/subshop')
cache_d = _resolve_dir('SUBSHOP_CACHE_D', '~/.cache/subshop')
log_d = _resolve_dir('SUBSHOP_LOG_D', '~/.cache/subshop')
model_d = _resolve_dir('SUBSHOP_MODEL_D', '~/.cache/subshop')
root_d = _resolve_root('SUBSHOP_ROOT_D', None)


def runner(argv):
    """TBD"""
    # pylint: disable=import-outside-toplevel
    import argparse
    if isinstance(argv, argparse.Namespace):
        opts = argv
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument('-v', '--verbose', action = "store_true",
            help = "choose whether show details")
        opts = parser.parse_args(argv)

    dirs = {}
    for name in ('config_d', 'cache_d', 'log_d', 'model_d'):
        folder = globals()[name]
        # print('dirs:', dirs)
        print(f'{name}="{folder}"')
        if opts.verbose:
            if folder in dirs:
                print(f'  ==${dirs[folder]}')
                continue
            dirs[folder] = name
        if opts.verbose and os.path.isdir(folder):
            dirlist = []
            for entry in os.scandir(folder):
                dirlist.append(f'{entry.name}{"/" if entry.is_dir() else ""}')
            print('  ' +  "\n  ".join(sorted(dirlist)))
