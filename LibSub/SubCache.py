#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manage the subtitle cache directory.
============== This the scheme for TV episodes:

 {showdir}/omdb-info.yaml   # OMDbAPI.org info (DIFFERENT dir than Movies)

 {vid-dir}={show-dir}[/{season-dir}]  # {show-dirs} has optional {season-dirs}

 {vid-dir}/{vid-corenm}.{vid-sfx}           # path of videofile w named parts
          /{vid-corenm}.{subt-sfx}
          /{vid-corenm}.cache        # directory for one videofile' paraphernalia
          /{vid-corenm}.cache/{vid-corenm}.en[.forced].TORRENT.{subx}
          /{vid-corenm}.cache/{vid-corenm}.REFERENCE.{subx}
          /{vid-corenm}.cache/{vid-corenm}.AUTOSUB.{subx}
          /{vid-corenm}.cache/{vid-corenm}.EMBEDDED.{subx}
          /{vid-corenm}.cache/{downloaded-subt}...
          /{vid-corenm}.cache/probe-info.yaml # info from ffprobe
          /{vid-corenm}.cache/quirk.{info}.nfo # quirk file


============== This the scheme for Movies:

 {vid-dir}/{vid-corenm}.{vid-sfx}     # path of videofile w named parts
          /{vid-corenm}.{subt-sfx}
          /{vid-corenm}.cache        # directory for one videofile' paraphernalia
          .... # SAME cache items for TV episode ... plus:
          /{vid-corenm}.cache/omdb-info.yaml # # OMDbAPI.org info (DIFFERENT dir than TV)


"""
# pylint: disable=import-outside-toplevel,broad-except
import os
import re
import time
import glob
import math
from pathlib import Path
from types import SimpleNamespace
from send2trash import send2trash
from LibGen.YamlDump import yaml_str
from LibGen.CustLogger import CustLogger as lg
from LibSub import ConfigSubshop
from LibSub.VideoProbe import VideoProbe
from LibSub.TmdbTool import TmdbTool
from LibSub.VideoParser import VideoParser, VideoFinder

class SubCache():
    """For handling the subtitle cache."""
    # pylint: disable=too-many-instance-attributes,too-many-public-methods
    o_cachedir = 'subcache.d' # deprecated
    subshop_params = ConfigSubshop.get_params()
    opts = None
    omdbtool = None

    # symbolic constants for quirk tags TODO get rid of deprecated
    FOREIGN = 'FOREIGN' # does not have english audio
    IGNORE = 'IGNORE'   # manual override
    SCORE = 'SCORE'     # score (note append XY to indicate score 01 to 19)
    AUTODEFER = 'AUTODEFER'  # no subtitle found automatically
    INTERNAL = 'INTERNAL' # has internal (english) subs

    quirk_tags = { # number is 'priority' (lower trumps larger)
            FOREIGN: 0,   # has no preferred language (english) audio track
            IGNORE: 1,    # manual override
            SCORE: 2,     # has external subs (w appended score, 01 to 19)
            INTERNAL: 3,  # has internal subs AND no external subs (i.e., relying on internal)
            AUTODEFER: 4,  # defer maintenance
            }

    def __init__(self, videofile, force_is_file=False):
        """Create a SubCache object for a given videofile; NOTE:
          - if given a directory, then binds to an arbitrary videofile in the directory.
        """
        videofile = os.path.abspath(videofile)
        self.video_dpath = None     # video directory
        self.video_basename = None  # video file basename including suffix
        self.video_corename = None  # video file basename w/o suffix
        self.is_tvdir = False       # whether video_dpath is below the tv-root-dirs
        self.cache_dpath = None     # directory of any cached subtitles
        self.omdb_dpath = None      # directory with omdb-info.yaml file (if exists)
        self.parsed = None          # if parsed video file, the result

        self.divider = None   # printing state (divider is shown once)
        self.probeinfo = None # cached probeinfo (call get_probeinfo())
        self.omdbinfo = None  # cached omdbinfo (call get_omdbinfo())
        self.quirk = ''       # cached last quirk; NOTE: empty str for easy compares
        self.q_value = None   # cached last quirk value; None OR 0 <= int < 100
        self.expired = False  # cached whether current quirk is expired (must check)
        self.defer_why = False  # cached why deferred, if deferred

        self.video_cats = None  # paths by category in the video folder
        self.cache_cats = None  # paths by category in the cache folder

        if videofile:
            self.bind(videofile, force_is_file)
        lg.tr3(f'SubCache(): dpath={self.video_dpath} basename={self.video_basename}')

    def get_videopath(self):
        """TBD"""
        return os.path.join(self.video_dpath, self.video_basename)

    def get_probeinfopath(self):
        """TBD"""
        return os.path.join(self.cache_dpath, 'probe-info.yaml')

    def get_probeinfo(self, refresh=False, persist=True):
        """TBD"""
        if not self.probeinfo or refresh:
            self.probeinfo = VideoProbe(self, refresh, persist=persist)
            if persist:
                quirk = self.get_quirk()

                if not self.probeinfo.get_audio_stream():
                    if self.quirk_trumps(self.FOREIGN):
                        self.force_set_quirk(self.FOREIGN)
                elif quirk == self.FOREIGN:
                    self.clear_quirks()

                if self.probeinfo.get_subt_stream():
                    if self.quirk_trumps(self.INTERNAL):
                        self.force_set_quirk(self.INTERNAL)
                elif quirk == self.INTERNAL:
                    self.clear_quirks()

        return self.probeinfo

    def get_omdbinfopath(self):
        """TBD"""
        return os.path.join(self.omdb_dpath, 'omdb-info.yaml')

    def get_omdbinfo(self, omdbtool=None):
        """TBD"""
        if not self.omdbinfo:
            tool = omdbtool if omdbtool else SubCache.omdbtool
            if not tool:
                tool = SubCache.omdbtool = TmdbTool()
            self.omdbinfo = tool.get_omdbinfo(self.get_videopath(), self)
        return self.omdbinfo


    def bind(self, videofile, force_is_file=False):
        """Bind object to the given video file OR directory.
          - if videofile, then bind to it;
          - if regular file, then bind to 1s videofile in its directory
          - if a directory, then bind to 1st videofile in that directory.
          - if no video files in directory, leave it bound to just directory
        """

        self.probeinfo = None
        videopath = os.path.abspath(videofile)
        lg.tr3(f'SubCache.bind({videopath})')

        if force_is_file or os.path.isfile(videopath):
            video_dpath, basename = os.path.split(videopath)
            self.video_dpath, self.video_basename = video_dpath, basename
            lg.tr4(f'dpath={self.video_dpath} basename={self.video_basename}')
        elif os.path.isdir(videopath):
            self.video_dpath = videofile
            cat = self._get_paths_by_category(self.video_dpath)
            self.video_basename = os.path.basename(cat.videopaths[0]) if cat.videopaths else None
            lg.tr4(f'dpath={self.video_dpath} basename={self.video_basename}')

        if not self.video_basename:
            self.cache_dpath = None
        else:
            self.video_corename, _ = os.path.splitext(self.video_basename)
            self.cache_dpath = os.path.join(self.video_dpath,
                    self.video_corename + '.cache')
        self.is_tvdir = self._is_tvdir()

        if self.is_tvdir:
            pathup2, dirup1 = os.path.split(self.video_dpath)
            self.omdb_dpath = self.video_dpath
            if VideoParser.seasondir_pat.match(dirup1):
                self.omdb_dpath = pathup2
            self.parsed = None
            if self.video_basename:
                self.parsed = VideoParser(self.video_basename, expect_episode=True)
        else:
            self.omdb_dpath = self.cache_dpath
            if self.video_basename:
                self.parsed = VideoParser(self.video_basename, expect_episode=False)


    def dump(self, verbose=False):
        """Print info on the target"""
        # lg.pr(f'   video_basename: {self.video_basename}')
        lg.pr(f'+ video_dpath: {self.video_dpath}')
        lg.pr(f'+ is_tvdir: {self.is_tvdir}')
        lg.pr(f'+ omdb_dpath: {self.omdb_dpath}')
        lg.pr(f'+ cache_dpath: {self.cache_dpath}')
        if self.parsed:
            lg.pr('+ parsed:\n' + yaml_str(self.parsed, indent=8).rstrip())
        else:
            lg.pr('+ parsed: None')
        if verbose:
            paths = self.get_subtpaths()
            lg.pr('+ subtitles:\n'
                    + yaml_str(paths, indent=8).rstrip())
            lg.pr('+ cached subtitles:\n'
                    + yaml_str(self.get_cached_subtpaths(), indent=8).rstrip())
            lg.pr('+ OMDb info:\n'
                    + yaml_str(self.get_omdbinfo(), indent=8).rstrip())
            lg.pr('+ Probe info:\n'
                    + yaml_str(self.get_probeinfo(), indent=8).rstrip())
            self.get_quirk()
            lg.pr(f'+ quirk: {self.quirk} {self.q_value}'
                    f'{"" if self.expired else f" defer [{self.defer_why}]"}')

    def _is_tvdir(self):
        if self.video_dpath:
            for root in self.subshop_params.tv_root_dirs:
                lg.tr7(f'_is_tvdir(): calling commonpath([{root}, {self.video_dpath}])')
                if root == os.path.commonpath([root, self.video_dpath]):
                    return True
        return False

    def _get_paths_by_category(self, folder, *folders, refresh=False):
        """Get all the videos and (uncached) subtitles in the video directory"""
        if folders:
            folder = os.path.join(folder, *folders)

        if folder == self.video_dpath and not refresh and self.video_cats:
            return self.video_cats
        if folder == self.cache_dpath and not refresh and self.cache_cats:
            return self.cache_cats

        rv = SimpleNamespace(videopaths=[], subtpaths=[], quirkpaths=[], otherpaths=[])
        paths = glob.glob(os.path.join(glob.escape(folder), '*'))
        # lg.info('get_paths_by_category() folder:', folder, type(paths),
                # len(paths), '\n', yaml_str(paths))
        for idx in range(len(paths)-1, -1, -1):
            path = paths[idx]
            # lg.info('get_paths_by_category() path:', idx, paths[idx])
            if VideoParser.has_video_ext(path):
                rv.videopaths.append(path)
            elif VideoParser.has_subt_ext(path):
                rv.subtpaths.append(path)
            elif os.path.basename(path).startswith('quirk.'):
                rv.quirkpaths.append(path)
            else:
                rv.otherpaths.append(path)
        # lg.info(tb.backtrace())
        # lg.info('get_paths_by_category() returning:\n', yaml_str(rv))
        # lg.info(type(rv), rv)
        if folder == self.video_dpath:
            self.video_cats = rv
        elif folder == self.cache_dpath:
            self.cache_cats = rv
        return rv

    def get_subtpaths(self):
        """Get all the (uncached) subtitles belonging to the current video
        and native language ordered by "most preferred":
            - .enNM.srt (where NM is a two digit score)
            - .en.srt
            - .srt
            - .enXYZ.srt (where XYZ is "anything")
        Same as get_all_subtpaths but does not return foreign subs.
        """
        native_paths, _ = self.get_all_subtpaths()
        return native_paths

    def get_all_subtpaths(self, refresh=False):
        """Get all the (uncached) subtitles belonging to the current video.
        Returns two lists .. native and non-native."""
        if not self.video_corename:
            return [], []

        lang = self.subshop_params.my_lang2
        # TODO: once there are no more .en04.srt, then clean this up!!!
        pat = re.compile(fr'^(?:|(\.{lang})(?:(\d\d)|(.*))|(\..*)).srt$')
        for loop in range(2):
            # pylint: disable=cell-var-from-loop
            least_score, native_paths, nat_scores, foreigns = -1, [], {}, []
            cat = self._get_paths_by_category(self.video_dpath,
                    refresh=bool(refresh or loop>0))
            for subtpath in cat.subtpaths:
                subt = os.path.basename(subtpath)
                if subt.startswith(self.video_corename + '.'):
                    subt_end = subt[len(self.video_corename):].lower()
                    mat = re.match(pat, subt_end)
                    if mat:
                        if mat.group(1) and mat.group(2): # .en35.srt
                            nat_scores[subtpath] = int(mat.group(2))
                        elif mat.group(1) and not mat.group(3): # .en.srt
                            nat_scores[subtpath] = 100
                        elif mat.group(1): # .en7x534.srt
                            nat_scores[subtpath] = 300
                        elif mat.group(4):  # something 'foreign'
                            foreigns.append(subtpath)
                        else: # .srt
                            nat_scores[subtpath] = 150
            native_paths = sorted(nat_scores.keys(), key=lambda x: (nat_scores[x], x))
            least_score = nat_scores[native_paths[0]] if native_paths else -1
            if 0 <= least_score < 100:
                # lg.info('loop:', loop, 'nat_scores:', nat_scores)
                assert loop == 0
                lang_srt_path = os.path.join(self.video_dpath,
                                self.video_corename + f'.{lang}.srt')
                for idx, path in enumerate(native_paths):
                    if 0 <= nat_scores[path] <= 100:
                        if idx == 0:
                            os.replace(path, lang_srt_path)
                        else:
                            os.unlink(path)
                self.soft_set_quirk(SubCache.SCORE, least_score, keep_modtime=True)
            else:
                break

        return native_paths, foreigns

    def get_cached_subtpaths(self, refresh=False):
        """Get all the cached subtitles belonging to the current video."""
        rv = []

        rv = SimpleNamespace(references=[], embeddeds=[], torrents=[], downloads=[])
        cat = self._get_paths_by_category(self.cache_dpath, refresh=refresh)
        for subtpath in cat.subtpaths:
            preext, _ = os.path.splitext(subtpath)
            if preext.endswith('.REFERENCE'):
                rv.references.insert(0, subtpath)
            elif preext.endswith('.AUTOSUB'):
                rv.references.append(subtpath)
            elif preext.endswith('.TORRENT'):
                rv.torrents.append(subtpath)
            elif preext.endswith('.EMBEDDED'):
                rv.embeddeds.append(subtpath)
            else:
                rv.downloads.append(subtpath)
        return rv

    def set_defer(self):
        """Effectively, set quirk.AUTODEFER.  Either set quirk.AUTODEFER quirk OR
        update the quirk.SCORE=XX modification time.
        """
        self.get_quirk()
        if self.quirk == SubCache.SCORE:
            quirkpath = self.quirk_makepath(self.quirk, self.q_value)
            Path(quirkpath).touch()
        else:
            self.soft_set_quirk(SubCache.AUTODEFER)

    def get_srt_score(self):
        """Return the SRT score; -1 if not set."""
        self.get_quirk()
        return -1 if self.quirk != SubCache.SCORE or self.q_value is None else self.q_value

    def get_quirk_str(self):
        """W/o refresh, return the current quirk + q_value as string."""
        rv = ''
        if self.quirk:
            rv += self.quirk
            if self.q_value is not None:
                rv += f'.{self.q_value:02d}'
        return rv



    def get_quirk(self):
        """Get the current exception if any."""
        cat = self._get_paths_by_category(self.cache_dpath)
        # lg.info(type(cat), cat)
        # lg.info(vars(cat))

        self.quirk = ''  # reset to no quirk
        winner = None
        for quirk in cat.quirkpaths:
            basename = os.path.basename(quirk)
            rhs = basename[len('quirk.'):]
            q_value = None
            if rhs[:-3] in self.quirk_tags: # we have a value too (e.g. quirk.SCORE=04)
                try:
                    rhs, strval = rhs[:-3], rhs[-2:]
                    q_value = int(strval)
                except Exception:
                    q_value = None
            if rhs in self.quirk_tags:
                if self.quirk_trumps(rhs):
                    self.quirk = rhs
                    self.q_value = q_value
                    winner = quirk
        if winner:
            while cat.quirkpaths:
                cat.quirkpaths.pop(0)
            cat.quirkpaths.insert(0, winner)

        return self.check_quirk_expiry()

    def check_quirk_expiry(self):
        """Check the expiration on the quirk.
        If an expired AUTODEFER, then just remove the quirk.
        Set the 'expired' flag to whether expired."""
        if not self.quirk:
            return ''
        if self.quirk in ('AUTODEFER', 'SCORE', ):
            def days_ago(secs):
                rv = round((time.time()- secs)/(24*3600), 3) if secs > 0 else 0
                # <-10: assume ago far in the future means very old
                # <0: avoid a sqrt exception and assume actually very new
                return 365*2 if rv < -10 else 0 if rv < 0 else rv

            video_age_d = days_ago(os.path.getmtime(self.get_videopath()))
            max_days = SubCache.subshop_params.cmd_opts_defaults.auto_retry_max_days
            expiry_d = round(min(max_days, math.sqrt(video_age_d)), 3)
            quirk_age_d = days_ago(os.path.getmtime(self.quirk_makepath(
                self.quirk, self.q_value)))
            # lg.info('quirk_age_d:', quirk_age_d, 'expiry_d:', expiry_d)
            self.expired = bool(quirk_age_d > expiry_d)
            self.defer_why = ('' if self.expired else
                    f'age({round(quirk_age_d)}d) <= expiry({round(expiry_d)}d)')
            if self.expired and self.quirk in ('AUTODEFER', ):
                self.clear_quirks()
                self.quirk, self.q_value = '', None

        return self.quirk

    def clear_quirks(self):
        """Remove the current exception if any.
        Returns the modtime of any AUTODEFER or None.
        """
        modtime = None
        cat = self._get_paths_by_category(self.cache_dpath)
        for quirk in cat.quirkpaths:
            if os.path.isfile(quirk):
                if not modtime and SubCache.AUTODEFER in quirk:
                    modtime = os.path.getmtime(quirk)
                os.unlink(quirk) # there is only supposed to be one
        cat.quirkpaths = []
        self.quirk = ''
        return modtime

    def quirk_makepath(self, quirk, value):
        """Make the full path of quirk files given its tag."""
        suffix = quirk
        suffix += f'.{value:02d}' if isinstance(value, int) and 0 <= value < 100 else ''
        return self.makepath('quirk.' + suffix)

    def soft_set_quirk(self, quirk, value=None, keep_modtime=False):
        """Set a quirk only if it trumps the current one."""
        if self.quirk_trumps(quirk):
            self.force_set_quirk(quirk, value, keep_modtime)

    def force_set_quirk(self, quirk, value=None, keep_modtime=False):
        """Set a quirk.
        Generally, first call quirk_trumps() to ensure the quirk SHOULD be set."""
        assert quirk in self.quirk_tags

        modtime = self.clear_quirks()
        # lg.info('autodefer_modtime:', modtime)
        quirkpath = self.quirk_makepath(quirk, value)
        Path(quirkpath).touch()
        self.cache_cats.quirkpaths.insert(0, quirkpath)
        if keep_modtime:
            if modtime is None:
                modtime = time.time() - (60*60*24)*365 # about a year ago so looks expired
            os.utime(quirkpath, times=(modtime, modtime))

        self.quirk, self.q_value = quirk, value

    def quirk_trumps(self, quirk):
        """Return true if given quirk trumps the existing one. There can only be
        one quirk and there is a strict hierarchy.  Ties allow trumping so the
        score and/or date can be updated. """
        nval = self.quirk_tags.get(quirk, 1000)
        oval = self.quirk_tags.get(self.quirk, 1000)
        return bool(nval <= oval)

    def glob(self, core, extpat, cache_only=False):
        """Glob the base name pattern in
          - the parent dir (unless suppressed with cache_only)
          - the cache dir
        Arguments:
          - core: is the fixed part of basename that must match (if any)
          - extpat: the pattern part (e.g., '*.srt')
        """
        folders = [self.cache_dpath] if cache_only else [
                self.cache_dpath, self.video_dpath]
        rv = []
        for folder in folders:
            fullcore = os.path.join(folder, core)
            ans = glob.glob(glob.escape(fullcore) + extpat)
            rv.extend(ans)
        return rv

    def makepath(self, basename, ensure_dir=True, tag=None):
        """Construct a cached file name path.  Ensure the
        directory exists, too, since there is a plan to
        create it (unless ensure_dir is False).
        - Tag is expected to be TORRENT/AUTOSUB/REFERENCE/EMBEDDED or which gets
          inserted before last '.'
        """
        cache_d = self.cache_dpath
        basename = os.path.basename(basename) # to be sure relative
        if tag:
            preext, ext = os.path.splitext(basename)
            basename = f'{preext}.{tag}{ext}'.replace('..', '.') # avoid too many dots
        newpath = os.path.join(cache_d, basename)
        if ensure_dir and not os.path.isdir(cache_d):
            lg.db(f'making {cache_d}')
            os.makedirs(cache_d)
        else:
            lg.db(f'making {cache_d} not needed / not opted')
        lg.db(f'makepath returns: {newpath}')
        return newpath

    def _pr_divider(self):
        if self.divider:
            lg.pr(self.divider)
            self.divider = None

    def _recycle(self, path, why):
        # pylint: disable=redefined-outer-name
        basename = os.path.basename(path)
        if self.opts.dry_run:
            self._pr_divider()
            lg.pr(f'   + WOULD recyle "{basename}" [{why}]')
            return

        self._pr_divider()
        lg.pr(f'   + recyle "{basename}" [{why}]')

        try:
            send2trash(path)
        except Exception as exc:
            lg.err(f'cannot trash "{basename}"\n  {exc}')

    def cleanup(self):
        """Clean up the directory."""

        return   # FIXME: must implement/reconsider cleanup
        cached_files = self.glob('', '*', cache_only=True)
        parent_files = glob.glob(glob.escape(self.video_dpath) + '/*')
        video_files = [x for x in parent_files if VideoParser.has_video_ext(x)]
        video_dict = {} # key:'core' video name;  val: full name
        for video in video_files:
            vbase, _ = os.path.splitext(video)
            video_dict[os.path.basename(vbase)] = video
        autosub_dict = {} # key: core video name; val: full name
        vosk_dict = {} # key: core video name; val: full name

        purge_days = SubCache.subshop_params.subcache_purge_days

        self.divider = f'== running cache cleanup on: {self.video_dpath}'

        for cached in cached_files:
            purge_day = 0
            cached_basename = os.path.basename(cached)
            cleft, _ = os.path.splitext(cached_basename)
            if not VideoParser.has_subt_ext(cached):
                self._recycle(cached, 'not subtitle')
                continue
            if os.path.isdir(cached):
                self._recycle(cached, 'child directory')
                continue
            stat = os.stat(cached)

            if cleft.endswith('.AUTOSUB'):
                # we expect a video with same core name
                corename = cleft[:-len('.AUTOSUB')]
                autosub_dict[corename] = cached
                if corename not in video_dict:
                    self._recycle(cached, 'no mate')
                    continue
                purge_day = purge_days.AUTOSUB

            elif cleft.endswith('.REFERENCE'):
                # we expect a video with same core name
                corename = cleft[:-len('.REFERENCE')]
                vosk_dict[corename] = cached
                if corename not in video_dict:
                    self._recycle(cached, 'no mate')
                    continue
                purge_day = purge_days.REFERENCE

            elif cleft.endswith('.EMBEDDED'):
                # we expect a video with same core name
                corename = cleft[:-len('.EMBEDDED')]
                if corename not in video_dict:
                    self._recycle(cached, 'no mate')
                    continue
                purge_day = purge_days.EMBEDDED

            elif cleft.endswith('.TORRENT'):
                corename = cleft[:-len('.TORRENT')]
                if corename.endswith('.en'):
                    corename = corename[:-len('.en')]
                if corename not in video_dict:
                    self._recycle(cached, 'no mate')
                    continue
                purge_day = purge_days.TORRENT

            else:
                nlink = stat.st_nlink
                purge_day = purge_days.linked if nlink > 1 else purge_days.unlinked

            age_d = (time.time() - stat.st_atime) / (24*3600)
            if purge_day:
                if age_d >= purge_day:
                    self._recycle(cached, f'{age_d}d >= {purge_day}d')
                    continue

            if self.opts.verbose:
                self._pr_divider()
                lg.pr(f'   # KEEP {cached_basename} # age={age_d:.1f}d lim={purge_day}d')

        for corename in vosk_dict:
            # if both REFERENCE and AUTOSUB reference srts, remove the AUTOSUB
            autosubpath = autosub_dict.get(corename, None)
            if autosubpath:
                self._recycle(autosubpath, 'both REFERENCE and AUTOSUB')

        if not any(os.scandir(self.video_dpath)):
            self._recycle(self.video_dpath, 'empty dir')

    @staticmethod
    def get_all_cache_parents():
        """Get all the subcache folders in the tv and movie directories."""

        roots = SubCache.subshop_params.tv_root_dirs + SubCache.subshop_params.movie_root_dirs
        lg.db('roots:', roots)

        parents = []
        for root in roots:
            dirs = glob.glob(glob.escape(root) + '/**/' + SubCache.o_cachedir + os.sep,
                    recursive=True)
            # add all the parents.  NOTE: must remove trailing '/'.
            parents.extend([os.path.dirname(d[:-1]) for d in dirs])

        return parents


def runner(argv):
    """
    SubCache.py [H,S]: encapsulates the Subtitle Cache. Its runner() shows
    the cache info of its targets.  This is roughly eqivalent to 'subshop stat'
    but its non-verbose mode is more verbose.
    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--dry-run', action='store_true',
            help='show potential actions w/o doing them')
    parser.add_argument('-v', '--verbose', action='store_true',
            help='elaborate actions')
    parser.add_argument('-V', '--log-level', choices=lg.choices,
        default='INFO', help='set logging/verbosity level [dflt=INFO]')
    parser.add_argument('targets', nargs='*', help="videofiles/dirs to check")
    args = SubCache.opts = parser.parse_args(argv)
    lg.setup(level=args.log_level)

    # if no targets, do audit/cleanup on them all
    if not args.targets:
        parents = SubCache.get_all_cache_parents()
        for parent in parents:
            SubCache(parent).cleanup()
        return

    # If specifying targets, ...
    for video in VideoFinder(args.targets):
        cache = SubCache(video)
        lg.pr(f'\n--- Cache info for {cache.video_basename}:')
        cache.dump(verbose=args.verbose)
