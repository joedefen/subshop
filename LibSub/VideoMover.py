#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Moves "downloaded" files with wildly different conventions into
another place (i.e., staging directory) with standardized subtitle names.
"""
# pylint: disable=broad-except,import-outside-toplevel,too-many-instance-attributes
# pylint: disable=consider-using-f-string,invalid-name
import os
import sys
import shutil
import shlex
import re
import glob
from pathlib import Path
from LibGen.CustLogger import CustLogger as lg
from LibSub import ConfigSubshop
from LibSub.SubCache import SubCache
from LibSub.VideoParser import VideoParser, VideoFinder

class VideoMover:
    """TBD"""
    @staticmethod
    def create(videofile, find_subs=True, dry_run=False, verbose=False):
        """Create a VideoMover object IF the file exists and appears to be a video file."""
        # lg.tr9(f'has_video_ext={VideoParser.has_video_ext(videofile)}')
        # lg.tr9(f'isfile={os.path.isfile(videofile)}')
        if VideoParser.has_video_ext(videofile) and os.path.isfile(videofile):
            return VideoMover(videofile, find_subs=find_subs, dry_run=dry_run, verbose=verbose)
        return None

    def __init__(self, videofile, find_subs=True, dry_run=False, verbose=False):
        """TBD"""
        self.dry_run, self.verbose = dry_run, verbose
        self.would = 'WOULD ' if dry_run else ''
        fullpath = os.path.abspath(videofile)

        self.folder = os.path.dirname(fullpath)
        self.basename = os.path.basename(fullpath)
        self.corenm, self.ext = os.path.splitext(self.basename)
        self.subtpaths, self.ambiguous = [], []
        self.inhibit_download = False  # set to True to override automatic download
        if find_subs:
            self.subtpaths, self.ambiguous = self._gather_subtitles()

    def recycle_installed_video(self, videopath):
        """Recycle the installed video and its subtitles and cache."""
        dirname = os.path.dirname(videopath)
        basename = os.path.basename(videopath)
        commonpart, _ = os.path.splitext(basename)
        obstacles = glob.glob(glob.escape(os.path.join(dirname, commonpart)) + '.*')
        for obstacle in obstacles:
            self.recycle(obstacle)

    def move(self, dest_dir, new_basename=None):
        """Relocate the video to the destination folder.
        Returns True if the move worked.
        Optionally, rename the video.
        """
        # pylint: disable=redefined-outer-name
        ovideopath = os.path.join(self.folder, self.basename)
        nvideopath = os.path.join(dest_dir,
                new_basename if new_basename else self.basename)
        ncorenm, _ = os.path.splitext(new_basename) if new_basename else self.corenm, self.ext

        # firstly, clear the identically named destination if any.
        self.recycle_installed_video(nvideopath)

        ok = self.move_prim(ovideopath, dest=nvideopath)

        if ok and self.subtpaths:
            subcache = SubCache(nvideopath, force_is_file=self.dry_run)
            lg.db(f'nvideopath={nvideopath}, subcache={vars(subcache)}')

            for subtpath in self.subtpaths:
                _, ext = os.path.splitext(subtpath)
                identity = '.en'
                if re.search(r'\bforced\b', os.path.basename(subtpath)):
                    identity += '.forced'
                nsubbasename = ncorenm + identity + ext
                nsubtpath = os.path.join(dest_dir, nsubbasename)
                self.move_prim(subtpath, dest=nsubtpath)
                nsubcachepath = subcache.makepath(nsubbasename, tag='TORRENT')
                if self.dry_run or self.verbose:
                    lg.pr(f'+ {self.would} link {nsubtpath}\n   -> {nsubcachepath}')
                if not self.dry_run:
                    if os.path.isfile(nsubcachepath):
                        os.unlink(nsubcachepath)
                    os.link(nsubtpath, nsubcachepath)

        if ok and not self.subtpaths and ConfigSubshop.get_params().srt_auto_download:
            if self.dry_run or self.inhibit_download:
                lg.pr('+', f'{self.would} subshop dos "{nvideopath}" # if no internal subs')
            else:
                subcache = SubCache(nvideopath, force_is_file=self.dry_run)
                probeinfo = subcache.get_probeinfo()
                if probeinfo and not probeinfo.get_subt_stream():
                    cmd = "subshop dos {}".format(shlex.quote(nvideopath))
                    lg.pr('\n+', cmd)
                    os.system(cmd)
                    lg.pr('\n\n')
        return ok

    def move_prim(self, npath, dest):
        """Move 'npath' to 'dest'.
        If returns True if no failure; else False
        """
        if self.dry_run or self.verbose:
            lg.pr(f' {self.would}move:\n    {npath}\n    TO {dest}')
        if self.dry_run:
            return True
        try:
            dest_dir = os.path.dirname(dest)
            lg.tr1('dest_dir:', dest_dir, 'dest:', dest)
            if not os.path.isdir(dest_dir):
                lg.tr1('isdir:', dest_dir, 'to make dir')
                os.makedirs(dest_dir)
            shutil.move(npath, dest)
            lg.tr1('move:', npath, dest)
            return True # actually moved
        except Exception as why:
            lg.err('failed shutil.move({}, {})'.format(
                npath, dest), '\n   ', str(why))
            return False

    def _gather_subtitles(self):
        """TBD"""

        subdict = {}
        ambiguous = None
        for sub in VideoParser.oksubs:
            subdict[sub] = [[], []] # for (unforced, force)

        # collect all the subtitle file 'candidates' separated by whether 'forced'
        for (root, _, files) in os.walk(self.folder):
            for filename in files:
                pathname = os.path.join(root, filename)
                suffix = filename.lower()[-4:]
                if suffix in VideoParser.oksubs:
                    forced = 0
                    if re.search(r'\bforced\b', filename, re.IGNORECASE):
                        forced = 1
                    subdict[suffix][forced].append(pathname)
        # lg.db(subdict)

        sublist = [[], []] # preferred
        for forced in (0, 1):
            #### let us try to prune the list....
            ## find the most preferred type of subtitle...
            for sub in reversed(VideoParser.oksubs):
                if subdict[sub][forced]:
                    sublist[forced] = subdict[sub][forced]
            slist = sorted(sublist[forced], reverse=True)
            # lg.db('forced' if forced else 'unforced', slist)

            if len(slist) > 1:
                ## if the base name of the file is a subtitle name, then
                ## filter on that criteria
                lcorenm = self.corenm.lower()
                lg.db(f'testing {lcorenm} in {slist[0].lower()}...')
                matches = [sub for sub in slist if lcorenm in sub.lower()]
                # if False and len(matches) >= 1 and len(matches) < len(slist):
                #     lg.db('forced' if forced else 'unforced',
                #             lcorenm, matches, len(matches))
                if len(matches) >= 1:
                    sublist[forced] = slist = matches

            # still too many? now look for '3_en', etc looking for english indicator
            for pat in (r'\b[3-9]_en', r'\b2_en',
                    r'\b\d+_en', r'\ben\b', r'\beng\b', r'\benglish\b'):
                if len(slist) > 1:
                    matches = [sub for sub in slist if re.search(pat,
                        os.path.basename(sub), re.IGNORECASE) ]
                    # if False and len(matches) >= 1 and len(matches) < len(slist):
                    #     lg.db('forced' if forced else 'unforced',
                    #             pat, matches, len(matches))
                    if len(matches) >= 1:
                        sublist[forced] = slist = matches

            ## Give up if still too many
            if len(slist) > 1:
                ambiguous = slist
                for pathname in slist:
                    lg.db('excess sub:', pathname)
                slist = None
            elif len(slist) == 1:
                slist = slist[0]
            else:
                slist = None
            sublist[forced] = slist
            # lg.db('forced' if forced else 'unforced', slist)

        # finally, put the winners of each type in a list
        subtitlefiles = []
        for forced in (0, 1):
            if sublist[forced]:
                subtitlefiles.append(sublist[forced])

        return subtitlefiles, ambiguous

    def recycle(self, path):
        """Recyle the item with info."""
        from send2trash import send2trash
        ok = True
        if self.dry_run or self.verbose:
            lg.pr(f' {self.would}trash: {path}')
        if not self.dry_run and (os.path.isfile(path) or os.path.isdir(path)):
            try:
                send2trash(path)
            except Exception as why:
                lg.err('cannot trash:', path, '\n  ', str(why))
                ok = False
        return ok

def runner(argv):
    """
    VideoMover.py [H]: implements moving videos/subtitles from a download
    area to the final destination.  Determination of the final destination
    is a higher-level function.

    TEST MODE: using runner() and passing argument 'TEST'
      - creates files in /tmp/vmv_tests/srcXY (the XY is generated)
      - moves files to /tmp/vmv_tests/dest
    Use find or a file manager to manually check the move which
    should be sets of:
      - foobar.cache/foobar.en.TORRENT.srt # IF there is an external srt
      - foobar.en.srt # IF there is an external srt
      - foobar.mkv # always, but the extension may vary
    Look in VideoMover.py for the test cases which indicate the handled
    structures for downloaded TV shows and movies.

    SCRIPT MODE: using runner() and passing -d{folder} {downloads},
    it moves the video and subtitles to the destination folder.
    If the videos do not share one destination folder, then you must
    run separate the commands.
    """
    ### THESE are test cases taken straight from files listings
    ### sometimes abbreviated.
    test_cases = """
  Gilmore.Girls.S07.WEBRip.x264-FGT.nfo	3.63 KB
  Gilmore.Girls.S07E01.WEBRip.x264-FGT.mp4	373.48 MB
  Gilmore.Girls.S07E02.WEBRip.x264-FGT.mp4	370.80 MB
  Gilmore.Girls.S07E03.WEBRip.x264-FGT.mp4	369.85 MB
  RARBG.txt	0.03 KB
  Subs/Gilmore.Girls.S07E01.WEBRip.x264-FGT.srt	82.62 KB
  Subs/Gilmore.Girls.S07E02.WEBRip.x264-FGT.srt	79.22 KB
  Subs/Gilmore.Girls.S07E03.WEBRip.x264-FGT.srt	84.50 KB

   RARBG.txt	0.03 KB
   RARBG_DO_NOT_MIRROR.exe	0.10 KB
   Subs/2_English.srt	78.65 KB
   The.Looney.Looney.Looney.Bugs.Bunny.Movie.1981.1080p.WEBRip.x265-RARBG.mp4	1.24 GB

   RARBG.txt	0.03 KB
   RARBG_DO_NOT_MIRROR.exe	0.10 KB
   Subs/4_English.srt	129.95 KB
   Tim.Maia.2014.PORTUGUESE.720p.BluRay.H264.AAC-VXT.mp4	1.71 GB

   Mifune.The.Last.Samurai.2015.1080p.BluRay.H264.AAC-RARBG.mp4	1.52 GB
   RARBG.txt	0.03 KB
   RARBG_DO_NOT_MIRROR.exe	0.10 KB
   Subs/2_English.srt	37.40 KB
   Subs/3_French.srt	67.08 KB

   A.Writers.Odyssey.2021.CHINESE.720p.BluRay.H264.AAC-VXT.mp4	1.57 GB
   RARBG.txt	0.03 KB
   RARBG_DO_NOT_MIRROR.exe	0.10 KB
   Subs/2_Romanian.srt	82.63 KB
   Subs/6_English.srt	81.00 KB

   And.Tomorrow.the.Entire.World.2020.GERMAN.720p.BluRay.H264.AAC-VXT.mp4	1.34 GB
   RARBG.txt	0.03 KB
   RARBG_DO_NOT_MIRROR.exe	0.10 KB
   Subs/2_English.srt	70.46 KB
   Subs/3_English.srt	87.22 KB
   Subs/4_German.srt	82.21 KB
   Subs/5_German.srt	102.33 KB
   Subs/7_Spanish.srt	68.60 KB

	BSG.S03E00.Resistance.Webisodes.mkv			192.01 MiB
	BSG.S03E01.Occupation.720p.Brrip + C.mkv	640.25 MiB
	BSG.S03E01.Occupation.720p.Brrip + C.srt	41.08 KiB
	BSG.S03E02.Precipice.720p.Brrip + C.mkv		672.47 MiB
	BSG.S03E02.Precipice.720p.Brrip + C.srt     46.96 KiB

   RARBG.txt	0.03 KB
   Subs/the.wire.s04e01.ws.bdrip.x264-reward.idx	342.24 KB
   Subs/the.wire.s04e01.ws.bdrip.x264-reward.sub	21.74 MB
   Subs/the.wire.s04e02.ws.bdrip.x264-reward.idx	391.81 KB
   Subs/the.wire.s04e02.ws.bdrip.x264-reward.sub	24.69 MB
   Subs/the.wire.s04e03.ws.bdrip.x264-reward.idx	355.08 KB
   Subs/the.wire.s04e03.ws.bdrip.x264-reward.sub	20.60 MB
   the.wire.s04e01.ws.bdrip.x264-reward.mkv	558.01 MB
   the.wire.s04e02.ws.bdrip.x264-reward.mkv	546.38 MB
   the.wire.s04e03.ws.bdrip.x264-reward.mkv	557.42 MB

   MacGyver.S05E01.WEBRip.x264-ION10.mp4	419.95 MB
   MacGyver.S05E02.WEBRip.x264-ION10.mp4	386.44 MB
   MacGyver.S05E03.WEBRip.x264-ION10.mp4	417.28 MB
   RARBG.txt	0.03 KB
   Subs/MacGyver.S05E01.WEBRip.x264-ION10.srt	59.56 KB
   Subs/MacGyver.S05E02.WEBRip.x264-ION10.srt	49.08 KB
   Subs/MacGyver.S05E03.WEBRip.x264-ION10.srt	55.42 KB
"""
    def make_tests():
        """TBD"""
        root = os.path.join('/tmp', 'vmv_tests')
        nonlocal test_cases

        if os.path.isfile(root):
            os.unlink(root)
        elif os.path.isdir(root):
            shutil.rmtree(root)
        os.mkdir(root)

        subdir = 'src0'
        for lineno, test in enumerate(test_cases.splitlines()):
            testfile = test.strip()
            # look for size spec at end-of-line and strip it
            mat = re.search(r'\b([.\d]+\s*[mgk]i?b)$', testfile, re.IGNORECASE)
            if mat:
                testfile = testfile[:-(len(mat.group(1)))].strip()
            if testfile:
                testpath = os.path.join(root, subdir, testfile)
                lg.db('path:', testpath)
                os.makedirs(os.path.dirname(testpath), exist_ok=True)
                Path(testpath).touch()
            else:
                subdir = f'src{lineno}'
        return root

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--dry-run', action='store_true',
            help='show potential actions w/o doing them')
    parser.add_argument('-v', '--verbose', action='store_true',
            help='elaborate actions')
    parser.add_argument('-d', '--dest-dir', default=None,
            help='destination dir (required if not test')
    parser.add_argument('-V', '--log-level', choices=lg.choices,
        default='INFO', help='set logging/verbosity level [dflt=INFO]')
    parser.add_argument('downloads', nargs='+',
            help='files or folders w downloaded videos OR "TEST"')
    args = parser.parse_args(argv)
    lg.setup(level=args.log_level)

    if args.downloads[0] == 'TEST':
        testroot = make_tests()
        dest_dir = os.path.join(testroot, 'dest')
        os.mkdir(dest_dir)
        downloads = [testroot]
    else:
        downloads = args.downloads
        if not os.path.isdir(args.dest_dir):
            lg.err('FATAL: must specify -d/--dest-dir if not running TEST')
            sys.exit(1)
        dest_dir = args.dest_dir


    for video in VideoFinder(downloads, use_plex=False):
        mover = VideoMover.create(video, dry_run=args.dry_run, verbose=args.verbose)
        mover.inhibit_download = True  # override the auto-download subtitles configuration
        lg.pr(f'\n\n+ {os.path.basename(video)}')
        for subtpath in mover.ambiguous if mover.ambiguous else []:
            lg.pr(f'  - AMBIGUOUS: {subtpath}')
        for subtpath in mover.subtpaths:
            lg.pr(f'  - {subtpath}')
        mover.move(dest_dir)
