#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SubDownloader.py - get srt files from opensubtitles.org
- requires an account

        # 1/ Change the search language by using any supported 3-letter (ISO639-2) language code:
        #    > Supported language codes: https://www.opensubtitles.org/addons/export_languages.php
        #    > Full guide: https://github.com/emericg/OpenSubtitlesDownload/wiki/Adjust-settings
        #    > Ex: opt_languages = ['eng']
        # 2/ Search for subtitles in several languages (at once, select one)
        #    by using multiple codes separated by a comma:
        #    > Ex: opt_languages = ['eng,fre']
        # 3/ Search for subtitles in several languages (separately, select one of each)
        #    by using multiple codes separated by a comma:
        #    > Ex: opt_languages = ['eng','fre']
"""

# pylint: disable=invalid-name,broad-except,too-many-branches
# pylint: disable=too-many-instance-attributes,using-constant-test,too-many-nested-blocks
# pylint: disable=too-many-lines,too-many-public-methods
# pylint: disable=consider-using-f-string

import os
import re
import sys
import time
import gzip
import base64
import struct
import hashlib
import argparse
import traceback
import codecs
import shlex
import readline
from xmlrpc.client import ServerProxy, ProtocolError #, Error
from LibSub import ConfigSubshop
from LibSub.VideoParser import VideoParser, VideoFinder
from LibSub.SubCache import SubCache

DEBUG = False

class Throttle():
    """For limiting requests smartly."""
    def __init__(self):
        self.maxCnt, self.itvl = 10, 2.75  # no more than 40req/10s is published limit
        self.req_cnt, self.req_base = 0, 0  # current count since base time

    def delay_as_needed(self):
        """Sleep a bit if going too fast."""
        now = time.time()
        elapsed = now - self.req_base
        # print('do_throttle() cnt:', self.req_cnt, 'elapsed:', elapsed)
        if elapsed >= self.itvl:
            self.req_cnt, self.req_base = 0, time.time()
        elif self.req_cnt >= self.maxCnt:
            pause = min(self.itvl - elapsed, self.itvl)
            # print('OpenSubtitles.org API THROTTLE:', pause, 'secs')
            time.sleep(pause)
        self.req_cnt += 1

class SubDownloader():
    """TBD"""
    osd_server = ServerProxy('https://api.opensubtitles.org/xml-rpc')
    session_id = None  # aka; session token
    download_params = ConfigSubshop.get_params().download_params
    score_params = ConfigSubshop.get_params().download_score_params

    def __init__(self, args=None):
        self.osd_language = 'en' # Interface language (non-english is not an option)

        # ==== Language settings =======================================================
        # Write language code (ex: _en) at the end of the subtitles file. 'on', 'off' or 'auto'.
        # If you are regularly searching for several language at once, you sould use 'on'.

        # - auto: same language code size than set in opt_lanuages
        # - 2: 2-letter (ISO639-3) language code
        # - 3: 3-letter (ISO639-2) language code
        self.opt_language_suffix_size = 'auto'
        # Character used to separate file path from the language code (ex: file_en.srt).
        self.opt_language_suffix_separator = '_'


        # ==== Selection settings ============================================================

        # Various GUI columns to show/hide during subtitles selection.
        # You can set them to 'on', 'off' or 'auto'.
        self.opt_selection_hi       = 'auto'
        self.opt_selection_language = 'auto'
        self.opt_selection_match    = 'auto'
        self.opt_selection_rating   = 'off'
        self.opt_selection_count    = 'off'

        # "current" file attributes
        self.videoTitle = None
        self.videoFileName = None
        self.winnerSubFileName = None
        self.subcache = None
        self.cached_files = None
        self.probe_info = None
        self.duration_str = '00:00'
        self.videoHash = None
        self.videoSize = None
        self.search_override = None
        self.previous_search = None
        self.omdbinfo = None

        self.languageList = []
        self.languageCount_search = 0
        self.languageCount_results = 0
        self.limits = None
        self.exit_code = None
        self.whynot = None # failure summary of last attempt if not empty
        self.winner = None # last search winner
        self.downloaded_subtitle = None # set if download occurred
        self.throttle = Throttle()

        self.rem_retry_on_busy = 0   # remaining retries on busy
        self.rem_retry_on_407 = 0    # remaining retries on 407
        self.rem_retry_on_901 = 0    # remaining retries on 901
        self.first_rem_retry_on_407 = 0 # how many retries on 407 initially
        self.opts = self.parse_args(args)
        if self.opts.imdb:
            self.opts.imdb = self.opts.imdb.lower()
            if not self.opts.imdb.startswith('tt'):
                self.opts.imdb = 'tt' + self.opts.imdb

    @staticmethod
    def parse_args(args=None):
        """Parse and sanitize the arguments."""
        parser = argparse.ArgumentParser(prog='SubDownloader.py',
                formatter_class=argparse.RawTextHelpFormatter,
                description='find/download subtitles for the given videos')

        parser.add_argument('-l', '--lang', nargs='?', action='append',
                dest='languages', default=[],
                help="Specify desired subtitle language default: eng).\n"
                + "Syntax:\n-l eng,fre: search in both\n-l eng -l fre: download both")
        parser.add_argument('-t', '--select', default='default',
                help="Selection mode: manual, default, auto")
        parser.add_argument('-a', '--auto', action='store_true',
                help="Automatically pick and download best scored subtitles")
        parser.add_argument('-A', '--auto-redo', action='store_true',
                help="Automatically pick/download best scored, uncached subtitles")
        parser.add_argument('-C', '--no-cache', dest='use_cache', action='store_false',
                help="Do NOT use cache")
        parser.add_argument('-I', '--imdb', help="Specify IMDB ID as 'ttXXXXXXX'")
        parser.add_argument('-k', '--keep-trying', type=int,
                help="Keep trying on download on 407 for given number of tries")
        parser.add_argument('-o', '--output', dest='output_path',
                help="Override subtitles download path, instead of next their video file")
        parser.add_argument('-p', '--password',
                help="Set opensubtitles.org account password")
        parser.add_argument('-u', '--username',
                help="Set opensubtitles.org account username")
        parser.add_argument('-v', '--verbose', action='store_true', help="Print details")
        parser.add_argument('-x', '--suffix', action='store_true',
                help="Force language code file suffix")
        parser.add_argument('-X', '--forced-suffix',
                help="Force an explicit suffix (w/o leading dot")
        parser.add_argument('-8', '--utf8', action='store_true', dest='utf8',
                help="Force UTF-8 file download [which seems to be a no-op]")
        parser.add_argument('searchPathList',
                help="video file(s) or folder(s) for fetching subtitles", nargs='+')

        # Parse arguments
        opts = parser.parse_args(args)
        opts.languages = list(dict.fromkeys(opts.languages)) # remove dups
        opts.languages = opts.languages if opts.languages else ['eng']
        return opts

    # ==== Super Print =============================================================
    # priority: info, warning, error
    # title: only for zenity and kdialog messages
    # message: full text, with tags and breaks (tags will be cleaned up for CLI)

    @staticmethod
    def superPrint(_priority, _title, *message):
        """Print messages through terminal, zenity or kdialog"""
        message = ''.join(message)
        # Clean up format tags from the zenity string
        message = message.strip()
        message = message.replace("\n\n", "\n")
        message = message.replace('\\"', '"')
        message = message.replace("<i>", "")
        message = message.replace("</i>", "")
        message = message.replace("<b>", "")
        message = message.replace("</b>", "")
        message = message.replace("\n", "\n   ")
        # Print message
        print(">> " + message)

    # ==== Check file path & type ==================================================

    @staticmethod
    def checkFileValidity(path):
        """Check mimetype and/or file extension to detect valid video file"""
        if os.path.isfile(path) is False:
            return False

        fileExtension = path.rsplit('.', 1)
        if fileExtension[1] not in ['avi', 'mp4', 'mov', 'mkv', 'mk3d', 'webm', \
                                    'ts', 'mts', 'm2ts', 'ps', 'vob', 'evo', 'mpeg', 'mpg', \
                                    'm1v', 'm2p', 'm2v', 'm4v', 'movhd', 'movx', 'qt', \
                                    'mxf', 'ogg', 'ogm', 'ogv', 'rm', 'rmvb', 'flv', 'swf', \
                                    'asf', 'wm', 'wmv', 'wmx', 'divx', 'x264', 'xvid']:
            #superPrint("error", "File type error!",
            # "This file is not a video (unknown mimetype AND
            # invalid file extension):\n<i>" + path + "</i>")
            return False

        return True

    # ==== Check for existing subtitles file =======================================

    def checkSubtitlesExists(self, path):
        """Check if a subtitles already exists for the current file"""
        extList = ['srt', 'sub', 'sbv', 'smi', 'ssa', 'ass', 'usf']
        lngList = ['']

        if self.opts.suffix:
            for language in self.opts.languages:
                for l in list(language.split(',')):
                    lngList.append(self.opt_language_suffix_separator + l)
                    # Rough method to try 2 and 3 letters language codes
                    if len(l) == 3:
                        lngList.append(self.opt_language_suffix_separator + l[0:2])

        for ext in extList:
            for lng in lngList:
                subPath = path.rsplit('.', 1)[0] + lng + '.' + ext
                if os.path.isfile(subPath) is True:
                    self.superPrint("info", "Subtitles already downloaded!",
                            "A subtitles file already exists for this file:\n<i>"
                            + subPath + "</i>")
                    return True

        return False

    # ==== Hashing algorithm =======================================================
    # Info: https://trac.opensubtitles.org/projects/opensubtitles/wiki/HashSourceCodes
    # This particular implementation is coming from SubDownloader: https://subdownloader.net

    @staticmethod
    def hashFile(path):
        """Produce a hash for a video file: size + 64bit chksum of the first and
        last 64k (even if they overlap because the file is smaller than 128k)"""
        try:
            longlongformat = 'Q' # unsigned long long little endian
            bytesize = struct.calcsize(longlongformat)
            fmt = "<%d%s" % (65536//bytesize, longlongformat)

            f = open(path, "rb")

            filesize = os.fstat(f.fileno()).st_size
            filehash = filesize

            if filesize < 65536 * 2:
                SubDownloader.superPrint("error", "File size error!",
                        "File size error generating hash for :\n<i>" + path + "</i>")
                return "SizeError"

            buf = f.read(65536)
            longlongs = struct.unpack(fmt, buf)
            filehash += sum(longlongs)

            f.seek(-65536, os.SEEK_END) # size is always > 131072
            buf = f.read(65536)
            longlongs = struct.unpack(fmt, buf)
            filehash += sum(longlongs)
            filehash &= 0xFFFFFFFFFFFFFFFF

            f.close()
            returnedhash = "%016x" % filehash
            return returnedhash

        except IOError:
            SubDownloader.superPrint("error", "I/O error!",
                    "Input/Output error generating hash for:\n<i>" + path + "</i>")
            return "IOError"


    # ==== CLI selection mode ======================================================

    def selectionCLI(self, subtitles):
        """Command Line Interface, subtitles selection inside your current terminal"""
        def matchby_str(words):
            orders = (('Id', 'imdbid'), ('Tt', 'title'), ('Ep', 'episode'),
                    ('Yr', 'year'), ('Hs', 'moviehash'),
                    ('Du8', 'duration8'), ('Du7', 'duration7'), ('Du6', 'duration6'),
                    ('Du5', 'duration5'), ('Du4', 'duration4'), ('Du3', 'duration3'),
                    ('Du2', 'duration2'), ('Du1', 'duration1'),
                    ('Ln', 'language'), ('EMBEDDED', 'embedded'), ('IN-CACHE', 'in-cache'))
                    # ('Tx', 'fulltext'),
            rv = ''
            for order in orders:
                if order[0] in words or order[1] in words:
                    rv += ',' + order[0]
            return rv[1:]

        def present_choices(floor, window, cnt):
            nonlocal self, subtitles, max_choices, choice_floor
            # Print video infos
            print('\n')
            if self.omdbinfo:
                print(self.subcache.omdbtool.info_str(self.omdbinfo, w_overview=True,
                    indent='>> OMDb info: ', max_lines=3))
            else:
                print('>> **NO** OMDb info. Set if practical.\n')
            if self.videoTitle:
                print(">> Title: " + self.videoTitle)
            print(">> Filename: " + self.videoFileName)
            if self.probe_info.duration:
                print('>> Duration:', self.duration_str)

            # Print subtitles list on the terminal
            print(">> Available subtitles:")
            subtItem = ''
            ceiling = floor + window
            for idx, item in enumerate(subtitles):
                if idx < floor:
                    continue
                if idx >= ceiling:
                    break
                # print(item)

                subtItem = ''
                subtItem += str(item['_score_']) + ' '
                subtItem += '{}{} "{}"'.format(
                        '*' if item['SubFileName'] in self.cached_files else ' ',
                        re.sub(r'^[0:]*', r'', item['SubLastTS']),
                        item['SubFileName'])

                if self.opt_selection_hi == 'on' and item['SubHearingImpaired'] == '1':
                    subtItem += ' HI'
                if self.opt_selection_language == 'on':
                    subtItem += 'Lang:' + item['LanguageName']
                if self.opt_selection_match == 'on':
                    subtItem += ' By:' + matchby_str(item['_matchedbys_'])
                if self.opt_selection_rating == 'on':
                    subtItem += ' Rating:' + item['SubRating']
                if self.opt_selection_count == 'on':
                    subtItem += ' Cnt:' + item['SubDownloadsCnt']
                print('[{}] {}'.format(idx+1, subtItem))

            if floor > 0 or ceiling < cnt:
                print(f' ...Showing choices {floor+1}-{ceiling} of {cnt};'
                        ' enter u/d to page up/down')
            # Ask user to select a subtitles
            print("\033[91m[0]\033[0m Cancel search")

        max_choices = self.download_params.max_choices
        choice_floor =  0
        subtCnt = len(subtitles)
        present_choices(choice_floor, max_choices, subtCnt)

        choice = -1
        while (choice < 0 or choice > subtCnt):
            try:
                text = input(f'>> Pick (0-{subtCnt}) -OR- <Subt-Srch>/'
                        ' -OR- <IMDB-Srch>? -OR- ignore!: ')
                text = text.strip()
                if text.lower() in ('u', 'd'):
                    if text.lower() == 'u':
                        choice_floor = max(0, choice_floor - max_choices)
                    elif choice_floor + max_choices < subtCnt:
                        choice_floor += max_choices
                    present_choices(choice_floor, max_choices, subtCnt)
                    text = '-1'  # loop herein

                if text.startswith('/') or text.endswith('/'):
                    text = text[1:] if text.startswith('/') else text[:-1]
                    self.search_override = text.strip()
                    print(f'Searching for "{self.search_override}"')
                    return ""  # search for subs again from above

                if text.startswith('?') or text.endswith('?'):
                    text = text[1:] if text.startswith('?') else text[:-1]
                    tool = self.subcache.omdbtool
                    choice = tool.search_interactively(phrase=text, indent=3)
                    if 0 <= choice < len(tool.matches):
                        self.omdbinfo = tool.matches[choice]
                        tool.commit_to_cache(self.omdbinfo)
                        self.search_override = self.previous_search
                        return ""  # repeat last search with new imdbinfo
                    present_choices(choice_floor, max_choices, subtCnt)
                    text = '-1'  # loop herein

                if text.startswith('!') or text.endswith('!'):
                    # handle special commands
                    text = text[1:] if text.startswith('!') else text[:-1]
                    text = text.strip().lower()
                    if text == 'ignore':
                        print("Set video to ignore. Cancelling search...")
                        self.subcache.soft_set_quirk(SubCache.IGNORE)
                        return ""
                    print('unknown cmd ({text}) [expecting "ignore"]')
                    text = '-1'  # loop herein


                choice = int(text)
            except KeyboardInterrupt:
                print('Keyboard Interrupt ... exiting')
                sys.exit(15)
            except Exception as exc:
                print(f'ERROR: Exception {exc}')
                choice = -1

        # Return the result
        if choice == 0:
            print("Cancelling search...")
            return ""

        self.winnerSubFileName = subtitles[choice-1]['SubFileName']
        return self.winnerSubFileName

    # ==== Automatic selection mode ================================================


    def reorderSubtitlesByScore(self, subtitles):
        """Automatic subtitles selection using filename match"""
        def make_parts(string):
            wds = string.replace('-', '.').replace(
                ' ', '.').replace('_', '.').lower().split('.')
            return wds

        def set_duration(subtitle):
            """Set the (approximate) duration of the subtitles."""
            wds = subtitle['SubLastTS'].split(':') # expect '00:59:33' or hr:mm:ss
            duration = 0
            if len(wds) == 3:
                duration = 3600*int(wds[0]) + 60*int(wds[1]) + int(wds[2])
            subtitle['_duration_'] = duration
            # print(subtitle['SubFileName'], subtitle['SubLastTS'], wds, duration)
            return duration

        videoFileParts = make_parts(os.path.splitext(self.videoFileName)[0])
        info = VideoParser(self.videoFileName)
        languageListReversed = list(reversed(self.languageList))

        raw_name_scores = []
        scores = []
        durations = []
        for subtitle in subtitles:
            # print('scoreloop:', subtitle)
            # print('reversed language list:', languageListReversed)
            # print('lang:', subtitle['SubLanguageID'])
            score = 0
            # points to respect languages priority
            lang_idx = languageListReversed.index(subtitle['SubLanguageID'])
            if lang_idx > 0:
                score += lang_idx * self.score_params.pref_lang # 80
                subtitle['_matchedbys_'].append('Ln'*lang_idx)
            # extra point if the sub is found by hash
            if 'in-cache' in subtitle['_matchedbys_']:
                score += self.score_params.lang_pref # 80 - boost to get near front
            elif 'embedded' in subtitle['_matchedbys_']:
                score += self.score_params.lang_pref # 80 - boost to get near front
            if 'imdbid' in subtitle['_matchedbys_']:
                score += self.score_params.imdb_match # 20
            if info:
                # must manufacture a name with a video suffix for the parser
                subt_filename = subtitle['SubFileName']
                subt_info = VideoParser(subt_filename)
                if subt_info:
                    def norm(title): # normalized form of title
                        if isinstance(title, str):
                            return title.replace(' ', '.').replace('_', '.').lower()
                        return ''

                    # print('DB: info:', vars(info))
                    # print('DB: subt_info:', vars(subt_info))
                    if norm(info.title) == norm(subt_info.title):
                        score += self.score_params.title_match # 10
                        subtitle['_matchedbys_'].append('Tt')
                    if info.is_same_episode(subt_info):
                        score += self.score_params.season_episode_match # 30
                        subtitle['_matchedbys_'].append('Ep')
                    if info.is_same_movie_year(subt_info):
                        score += self.score_params.year_match # 20
                        subtitle['_matchedbys_'].append('Yr')
                    if DEBUG:
                        print('subt_info:', subt_filename, subt_info.title,
                                'sea:', info.season, subt_info.season,
                                'ep:', info.episode, subt_info.episode)

            if 'moviehash' in subtitle['_matchedbys_']:
                score += self.score_params.hash_match # 10

            # points for filename match
            subFileParts = make_parts(subtitle['SubFileName'])
            raw_name_score = 0
            for idx, subPart in enumerate(subFileParts):
                if idx < len(videoFileParts) and subPart == videoFileParts[idx]:
                    raw_name_score += 2
                else:
                    rem_sub_set = set(subFileParts[idx:])
                    rem_video_set = set(videoFileParts[idx:])
                    raw_name_score += len(rem_sub_set.intersection(rem_video_set))

            durations.append(set_duration(subtitle))
            # print("duration of", subtitle['SubFileName'], durations[-1])

            raw_name_scores.append(raw_name_score)

            if subtitle['SubHearingImpaired'] == '1': # a wee preference for hearing impaired
                score += self.score_params.hearing_impaired # 2
            elif 'hi' in  subFileParts:
                score += self.score_params.hearing_impaired # 2
            scores.append(score)

        # normalized name score so that 9 is top value
        top_nm_score = self.score_params.name_match_ceiling
        raw_name_score_vals = sorted(set(raw_name_scores), reverse=True)
        for idx, score in enumerate(scores):
            scores[idx] += max(0, top_nm_score
                    - raw_name_score_vals.index(raw_name_scores[idx]))

        # score the durations if we know the video duration
        if self.probe_info.duration >= 300:  # score <5m video too strange to risk
            def calc_dscore(sub_duration):
                nonlocal self
                ceiling = self.score_params.duration_ceiling # highest possible score
                vid_duration = self.probe_info.duration
                # Note 50s allowance for silence during credits; score impact starts
                # if subs are 10s longer or 110s shorter than video (so actually
                # allows for nearly 2m of silent credits).
                pct_sq_cap = 625 # (duration >=25% off gets worst score)
                delta = abs(vid_duration - 50 - sub_duration)
                delta_pct = round(100 * delta / vid_duration, 2)
                delta_pct_sq = int(round(min(pct_sq_cap, delta_pct * delta_pct)))
                score_pct = int(round(100 * (pct_sq_cap - delta_pct_sq) / pct_sq_cap))
                eighths = int(round((8 * score_pct / 100))) # 0-to-8 "indicator"
                scaled_score = int(round(score_pct * ceiling / 100)) # scaled 0-to-ceiling score
                # print('DB: ceiling:', ceiling, 'sdur:', sub_duration, 'vdur:', vid_duration,
                        # 'pct:', delta_pct, 'pct^2:', delta_pct_sq, 'sc_pct:', score_pct,
                        # 'scaled_sc:', scaled_score, 'eighths:', eighths)
                return (f'Du{eighths}' if eighths else '', scaled_score)

            dscores =  []
            for idx, duration in enumerate(durations):
                dscores.append(calc_dscore(duration))

            min_dscore = min([d[1] for d in dscores]) if scores else 0

            # print('DB: duration scores:', dscores)
            for idx, dscore in enumerate(dscores):
                relscore = dscore[1] - min_dscore
                if relscore:
                    scores[idx] += relscore
                    if dscore[0]:
                        subtitles[idx]['_matchedbys_'].append(dscore[0])

        # finally store it away for other use
        for idx, score in enumerate(scores):
            subtitles[idx]['_score_'] = score


        subtitles.sort(key=lambda x: '{:08d} {} {}'.format(x['_score_'],
                x['SubFileName'], x['SubHash']), reverse=True)
        if False:
            for subtitle in subtitles:
                print('DB scored:', subtitle['_score_'], subtitle['SubFileName'])

    def do_video_path(self, currentVideoPath, search_only=False):
        """Search and download subtitles"""
        self.whynot = None
        self.downloaded_subtitle = None # downloaded item whether decode/unzip works or not

        # ==== Exit code returned by the software. You can use them to improve scripting behaviours.
        # 0: Success, and subtitles downloaded
        # 1: Success, but no subtitles found or downloaded
        # 2: Failure
        if not SubDownloader.session_id:
            SubDownloader.session_id = self.login_primitive()
            if self.exit_code:
                return
            self.limits = self.limits_primitive()
            if self.exit_code:
                return
            if self.limits['client_24h_download_count'] > 20:
                # NOTE: I've not yet seen this non-zero ... print it if it finally
                # says something useful
                print('OpenSubtitles.org limit info:', self.limits)


        # ==== Count languages selected for this search
        for language in self.opts.languages:
            self.languageList += list(language.split(','))

        self.languageCount_search = len(self.languageList)
        self.languageCount_results = 0

        if self.opt_language_suffix_size == 'auto':
            languagePrefixSize = 0
            for language in self.languageList:
                languagePrefixSize += len(language)
            self.opt_language_suffix_size = (languagePrefixSize // self.languageCount_search)

        # ==== Get file hash, size and name
        self.videoTitle = ''
        self.videoFileName = os.path.basename(currentVideoPath)
        self.winnerSubFileName = None
        self.subcache = SubCache(currentVideoPath)
        # cached_paths = self.subcache.glob('', '*', cache_only=True)
        cat = self.subcache.get_cached_subtpaths(refresh=True)
        subtpaths = cat.embeddeds + cat.torrents + cat.downloads # ignore REFs
        self.cached_files = {}
        for path in subtpaths:
            self.cached_files[os.path.basename(path)] = path
        self.videoHash = SubDownloader.hashFile(currentVideoPath)
        self.videoSize = os.path.getsize(currentVideoPath)
        self.search_override = None

        # fetch: cached duration, internal_subs from videofile
        self.probe_info = self.subcache.get_probeinfo()
        self.duration_str = '00:00'
        if self.probe_info.duration: # create something like 01:47:44
            secs = int(round(self.probe_info.duration))
            hrs, mins, secs = secs//3600, (secs%3600)//60, secs%60
            self.duration_str = '{}{:02d}:{:02d}'.format(
                    f'{hrs:02d}:' if hrs else '', mins, secs)

        # get imdb info (and update if overridden from command line)
        omdbinfo = self.subcache.get_omdbinfo()
        if self.opts.imdb:
            if not omdbinfo or (omdbinfo and omdbinfo.imdbID != self.opts.imdb):
                tool = self.subcache.omdbtool
                matches = tool.lookup(self.opts.imdb)
                if matches:
                    print('NOTE: updated OMDb info:')
                    if omdbinfo:
                        print('   was:', tool.info_str(omdbinfo))
                    print('   now:', tool.info_str(matches[0]))
                    omdbinfo = matches[0]
                    tool.commit_to_cache(omdbinfo)
                else:
                    print('NOTE: ignoring unvalidated imdbID ({self.opts.imdb})')
        if omdbinfo:
            self.omdbinfo = omdbinfo


        self.search_pick_download(currentVideoPath, search_only)

        while self.search_override:
            self.search_pick_download(currentVideoPath, search_only)

        ## Print a message if no subtitles have been found, for any of the languages
        if self.languageCount_results == 0 and not search_only:
            SubDownloader.superPrint("info", "No subtitles available :-(",
                    '<b>No subtitles found</b> for this video:\n<i>'
                    + self.videoFileName + '</i>')


    def search_pick_download(self, currentVideoPath, search_only):
        """TBD"""
        # ==== Search for available subtitles
        for currentLanguage in self.opts.languages:
            if self.probe_info.get_subt_stream() and self.opts.auto:
                subtitles = [] # no search needed since the EMBEDDED one IS the winner
            else:
                subtitles = self.search_for_subtitles(currentLanguage)
                if self.exit_code:
                    return
            if subtitles: # remove non-SRT files, remove dups
                for idx in range(len(subtitles)-1, -1, -1):
                    if subtitles[idx]['SubFormat'] != 'srt':
                        subtitles.pop(idx)
                    elif self.std_codec_name(subtitles[idx]['SubEncoding']) is None:
                        subtitles.pop(idx)

                #  NOTE: another form of "dup" is identical names w/o identical SubHash;
                #  we are ignoring those although it may cause some confusion.
                #  E.g., in showing the subtitle list, we identify a match with a downloaded
                #  file w/o checking the hash (which probably should be done).
                keepers, dups = {}, []
                for idx, subtitle in enumerate(subtitles):
                    subhash = subtitle['SubHash']
                    if subhash in keepers:
                        # must insert in reverse order
                        dups.insert(0, (idx, subtitle, keepers[subhash]))
                    else:
                        keepers[subhash] = subtitle
                        subtitle['_matchedbys_'] = [subtitle['MatchedBy']]
                for dup in dups: # dups must be in reverse order
                    idx, duplicate, keeper = dup
                    keeper['_matchedbys_'].append(duplicate['MatchedBy'])
                    subtitles.pop(idx)


            ## Handle the list of matching subtitles
            if not self.opts.auto or subtitles or self.probe_info.get_subt_stream():
                # Mark search as successful
                if subtitles or self.probe_info.get_subt_stream():
                    self.languageCount_results += 1

                # Get video title
                winner = self.pick_winner(subtitles)

                ## Finally, download the winner
                self.winner = winner
                if search_only:
                    return
                if winner:
                    self.download_winner(winner, currentVideoPath, currentLanguage)
                elif self.search_override:
                    self.whynot = None
                else:
                    self.whynot = 'no selected subtitle'
            else:  # automatic, but not external/interal subtitles
                # NOTE: do not modify error text (relied on above)
                self.whynot = 'no available subtitles'

    def insert_fake_candidate(self, subtitles, filename):
        """In the case of internal subtitles being available, insert into
        the candidate subtitle list at the front;
        also used to put cached subtitles at the end.
        """
        fake = {}

        fake['_matchedbys_'] = ['in-cache' if filename else 'embedded']
        if filename:
            fake['_score_'] = 0
        else:
            fake['_score_'] = subtitles[0]['_score_'] if (
                    subtitles and '_score_' in subtitles[0]) else 99
        fake['_duration_'] = self.probe_info.duration

        fake['SubFormat'] = 'srt' # e.g., srt
        fake['MatchedBy'] = '' # e.g., imdbid
        fake['ISO639'] = 'en' # e.g., ro
        fake['IDSubtitleFile'] = 0 # e.g., 1954677189
        fake['SubDownloadLink'] = '' # e.g., http://dl.opensubtitles.org/en/...
        fake['LanguageName'] = 'English' # e.g., Romanian
        fake['SubHearingImpaired'] = 0 # e.g., 0
        fake['SubRating'] = 0.0 # e.g., 0.0
        fake['SubDownloadsCnt'] = 1 # e.g., 22322
        fake['SubEncoding'] = 'CP1250' # e.g., CP1250
        fake['SubLanguageID'] = 'eng'
        fake['SubHash'] = '8b87f1443ac9af51b0f7d9f052cff799'
        fake['SubLastTS'] = self.duration_str # e.g., [SubLastTS] => 01:47:44

            # e.g., [SubFileName] => Insurgent.2015.READNFO.CAM.AAC.x264-LEGi0N.srt
        if not filename:
            subFileName = os.path.basename(self.videoFileName)
            coreName, _ = os.path.splitext(subFileName)
            fake['SubFileName'] = f'{coreName}.EMBEDDED.srt'
            # e.g., [MovieName] => Insurgent
        else:
            subFileName = filename
            coreName, _ = os.path.splitext(subFileName)
            fake['SubFileName'] = subFileName

        fake['MovieName'] = coreName

        ####  FIELDS NOT USED / POPULATED (but could be)
        # [IDSubMovieFile] => 0
        # [MovieHash] => 0
        # [MovieByteSize] => 0
        # [MovieTimeMS] => 0
        # [SubActualCD] => 1
        # [SubSize] => 71575
        # [SubHash] => 8b87f1443ac9af51b0f7d9f052cff799
        # [IDSubtitle] => 6097361
        # [UserID] => 0
        # [SubSumCD] => 1
        # [SubAuthorComment] =>
        # [SubAddDate] => 2015-03-29 13:23:44
        # [SubBad] => 0
        # [MovieReleaseName] =>  Insurgent.2015.READNFO.CAM.AAC.x264-LEGi0N
        # [MovieFPS] => 30.000
        # [IDMovie] => 193345
        # [IDMovieImdb] => 2908446
        # [MovieNameEng] =>
        # [MovieYear] => 2015
        # [MovieImdbRating] => 6.6
        # [SubFeatured] => 0
        # [UserNickName] =>
        # [SubComments] => 0
        # [UserRank] =>
        # [SeriesSeason] => 0
        # [SeriesEpisode] => 0
        # [MovieKind] => movie
        # [SubHD] => 0
        # [SeriesIMDBParent] => 0
        # [SubEncoding] => CP1250
        # [ZipDownloadLink] => http://dl.opensubtitles.org/en/download/...
        # [SubtitlesLink] => http://www.opensubtitles.org/en/subtitles/...
        for subtitle in subtitles:
            if subtitle['SubFileName'] == fake['SubFileName']:
                return subtitles
        if not filename:
            subtitles.insert(0, fake)
        else:
            subtitles.append(fake)
        return subtitles

    @staticmethod
    def disconnect():
        """Disconnect from opensubtitles.org server"""
        if SubDownloader.session_id:
            try:
                SubDownloader.osd_server.LogOut(SubDownloader.session_id)
                SubDownloader.session_id = None
            except Exception:
                pass

    def login_primitive(self):
        """Establish Connection to OpenSubtitlesDownload"""
        self.plan_retries()
        while True:
            try:
                self.throttle.delay_as_needed()
                result = SubDownloader.osd_server.LogIn(self.opts.username,
                        self.opts.password[0:32], self.osd_language, 'opensubtitles-download 5.1')
                status = result['status']
            # except Exception:
            except ProtocolError as exc:
                status = '{} {}'.format(exc.errcode, exc.errmsg)
                # print('DB:', status)
            except Exception as exc:
                code = self.get_exception_code(exc)
                status = '{} LogIn(usr={}, pwd={}) exception [{}]'.format(
                        code, self.opts.username, self.opts.password, str(exc))

            if status.startswith('200'):
                return result['token'] # coding it as "session_id"
            if not self.retry_pause('Login', status):
                break

        SubDownloader.superPrint('error', 'LogIn error!',
                f'osd.Login(usr={self.opts.username}, pwd={self.opts.password}) failed [',
                status, ']\n')
        self.exit_code = status
        return None

    def limits_primitive(self):
        """Get Server Info including user quota"""
        self.plan_retries()
        while True:
            try:
                self.throttle.delay_as_needed()
                result = SubDownloader.osd_server.ServerInfo()
                # NOTE: oddyly, there is no status field
                return result['download_limits']
            except ProtocolError as err:
                status = '{} {}'.format(err.errcode, err.errmsg)
            except Exception as err:
                status = '999 ServerInfo() exception [{}]'.format(err)

            if not self.retry_pause('ServerInfo', status):
                break

        SubDownloader.superPrint('error', 'ConnectionLogIn error!',
                'osd.ServerInfo() failed [{}]\n'.format(status))
        self.exit_code = status
        return None

    def search_for_subtitles(self, language):
        """Search for subtiles for one language and one video file."""
        subtitles = []
        criteria = []
        text = self.search_override if self.search_override else self.videoFileName
        parsed = VideoParser(text)

        if self.omdbinfo:
            criteria.append({'sublanguageid': language,
                'imdbid': re.sub(r'^tt', r'', self.omdbinfo.imdbID, re.IGNORECASE)})
            if parsed.season is not None:
                criteria[-1]['season'] = str(parsed.season)
            if parsed.episode is not None:
                criteria[-1]['episode'] = str(parsed.episode)

        criteria.append({'sublanguageid': language,
            'moviehash': self.videoHash, 'moviebytesize': str(self.videoSize)})

        alt_text = parsed.title
        if alt_text:
            if parsed.episode is not None:
                if parsed.season is not None:
                    alt_text += f' {parsed.season}x{parsed.episode}'
            elif parsed.year is not None:
                alt_text += f' {parsed.year}'
            criteria.append({'sublanguageid': language, 'query': alt_text})
            if not self.search_override:
                readline.add_history(alt_text + '/')
        else:
            criteria.append({'sublanguageid': language, 'query': text})

        # print('criteria:', criteria)
        subtitles = self.search_primitive(criteria)
        self.previous_search = text
        self.search_override = None # use override once and done

        # print('result:', subtitles)
        if self.exit_code:
            return []

        return subtitles

    def search_primitive(self, subtitlesSearchList):
        """Do a search"""
        self.plan_retries()
        while True:
            try:
                self.throttle.delay_as_needed()
                result = SubDownloader.osd_server.SearchSubtitles(SubDownloader.session_id,
                        subtitlesSearchList)
                status = result['status']
            except ProtocolError as err:
                status = '{} {}'.format(err.errcode, err.errmsg)
            except Exception as err:
                # These:
                # - SearchSubtitles() exception [syntax error: line 1, column 0]
                # - SearchSubtitles() exception [no element found: line 1, column 0]
                # are likely (rare-ish) transient errors from experience ... so handling
                # it specially until it repeats for a while.
                code = self.get_exception_code(err)
                status = '{} SearchSubtitles() exception [{}]'.format(code, err)
            if status.startswith('200'):
                return result['data'] if 'data' in result else []

            if not self.retry_pause('SearchSubtites', status):
                break

        SubDownloader.superPrint('error', 'Search error!',
                'osd.SearchSubtiles() failed [', status, ']\n')
        self.exit_code = status
        return []

    def pick_winner(self, subtitles):
        """Select subtitle from list of candidates."""
        winnerSubFileName = ''

        subtitleFileNames = {x['SubFileName'] for x in subtitles}
        # print('DB subtitleFileNames:', subtitleFileNames)
        # print('DB vinfo:', vars(vinfo))
        for filename in self.cached_files:
            if filename not in subtitleFileNames:
                subtitles = self.insert_fake_candidate(subtitles, filename=filename)

        ## insert the internal subtitle as winner if appropropriate
        if self.probe_info.get_subt_stream():
            subtitles = self.insert_fake_candidate(subtitles, filename=None)
            if self.opts.auto:
                return subtitles[0]

        # If there is more than one subtitles and not self.opts.auto
        # then let the user decide which one will be downloaded
        self.reorderSubtitlesByScore(subtitles)

        if self.opts.auto: # Automatic subtitles selection
            winnerSubFileName = subtitles[0]['SubFileName']
        elif self.opts.auto_redo: # Automatic next best subtitles selection
            # looking for subtitle NOT in cache, preferring:
            # one with unique duration if any,
            # else wwith a duplicate duration, if any.
            durations = set()
            for subtitle in subtitles:
                if subtitle['SubFileName'] in self.cached_files:
                    durations.add(subtitle['_duration_'])
            best_uniq, best_dup = None, None # best with uniq/dup durations
            for subtitle in subtitles:
                if subtitle['SubFileName'] not in self.cached_files:
                    if subtitle['_duration_'] in durations:
                        best_dup = best_dup if best_dup else subtitle
                    else:
                        best_uniq = best_uniq if best_uniq else subtitle
            best = best_uniq if best_uniq else best_dup if best_dup else None
            winnerSubFileName = best['SubFileName'] if best else ''

        else:
            # Go through the list of subtitles and handle 'auto' settings activation
            for item in subtitles:
                if self.opt_selection_match == 'auto':
                    self.opt_selection_match = 'on'
                if self.opts.languages == 'auto' and self.languageCount_search > 1:
                    self.opt_selection_language = 'on'
                if self.opt_selection_hi == 'auto' and item['SubHearingImpaired'] == '1':
                    self.opt_selection_hi = 'on'
                if self.opt_selection_rating == 'auto' and item['SubRating'] != '0.0':
                    self.opt_selection_rating = 'on'
                if self.opt_selection_count == 'auto':
                    self.opt_selection_count = 'on'

            # Spaw selection window
            winnerSubFileName = self.selectionCLI(subtitles)


        # At this point a subtitles should be selected
        if winnerSubFileName:
            subIndex = 0
            subIndexTemp = 0

            # Find it on the list
            for item in subtitles:
                if item['SubFileName'] == winnerSubFileName:
                    subIndex = subIndexTemp
                    break
                subIndexTemp += 1
            return subtitles[subIndex]
        return None

    @staticmethod
    def std_codec_name(raw_name):
        """convert to lower case and remove anything that is not
        alphanumic or hypen;  then, look it up to be sure it is valid"""
        std_name = re.sub(r'[^a-z0-9_\-].*', '', raw_name.lower())
        try:
            codecs.lookup(std_name)
            return std_name
        except Exception:
            return None

    def download_winner(self, winner, currentVideoPath, currentLanguage):
        """Download a selected subtitle file."""
        # Prepare download
        subID = winner['IDSubtitleFile']
        subURL = winner['SubDownloadLink']
        subFileName = winner['SubFileName']
        subEncoding = self.std_codec_name(winner['SubEncoding'])
        self.videoTitle = winner['MovieName']

        # subLangName = winner['LanguageName']
        subPath = ''

        if not self.opts.use_cache and self.opts.output_path:
            if os.path.isdir(os.path.abspath(self.opts.output_path)):
                # Use the output path provided by the user
                subPath = (os.path.abspath(self.opts.output_path) + "/"
                        + subPath.rsplit('/', 1)[1])
            else:  # use the full path given
                subPath = self.opts.output_path
        elif self.opts.forced_suffix:
            # Use the path of the input video
            subPath = (currentVideoPath.rsplit('.', 1)[0] + '.'
                    + self.opts.forced_suffix)
        else:
            # Use the path of the input video
            subPath = (currentVideoPath.rsplit('.', 1)[0] + '.'
                    + winner['SubFormat'])

        # Write language code into the filename?
        if self.opts.suffix == 'on':
            if int(self.opt_language_suffix_size) == 2:
                subLangId = self.opt_language_suffix_separator + winner['ISO639']
            elif int(self.opt_language_suffix_size) == 3:
                subLangId = self.opt_language_suffix_separator + winner['SubLanguageID']
            else: subLangId = self.opt_language_suffix_separator + currentLanguage

            subPath = subPath.rsplit('.', 1)[0] + subLangId + '.' + winner['SubFormat']

        # Avoid the download if cached.
        if self.opts.use_cache and subFileName in self.cached_files:
            if os.path.isfile(subPath):
                os.unlink(subPath)
            os.link(self.cached_files[subFileName], subPath)
            print('>> Linked cached "{}" to "{}" [{}]'.format(
                subFileName, os.path.basename(subPath), winner['LanguageName']))
            return

        # extract the embedded sub if that is chosen
        if not winner['SubDownloadLink']:
            stream = self.subcache.get_probeinfo().get_subt_stream()
            cmd = 'ffmpeg -nostats -hide_banner -loglevel error -i {} -map {} {}'.format(
                    shlex.quote(currentVideoPath), stream, shlex.quote(subPath))
            print('\n+', cmd)
            rv = os.system(cmd)
            exit_code, signal = 0, 0
            if rv:
                exit_code, signal = rv >> 8, rv & 0x0FF
                print('ERR: os.system("ffmpeg -i ..")',
                        'killed by sig {}'.format(signal) if signal
                        else 'returned {}'.format(exit_code))
                if signal or exit_code == 15:
                    raise KeyboardInterrupt
            destpath = self.subcache.makepath(subFileName)
            if os.path.isfile(destpath):
                os.unlink(destpath)
            os.link(subPath, destpath)
            return


        # Make sure we are downloading an UTF8 encoded file
        if self.opts.utf8:
            downloadPos = subURL.find("download/")
            if downloadPos > 0:
                subURL = subURL[:downloadPos+9] + "subencoding-utf8/" + subURL[downloadPos+9:]
                # print('DB subURL', subURL)

        ## Download and unzip the selected subtitles
        print('>> Downloading "{}" [{}]'.format(subFileName, winner['LanguageName']))
        if False:
            print('===> WOULD download:', winner['SubFileName'])
        else:
            self.whynot = self.download_primitive(subID, subPath, subEncoding, winner)
            if self.whynot is None and self.opts.use_cache:
                if os.path.isfile(subFileName):
                    os.unlink(subFileName)
                madepath = self.subcache.makepath(subFileName)
                if os.path.isfile(madepath):
                    os.unlink(madepath)
                os.link(subPath, madepath)



    def download_primitive(self, subID, subPath, subEncoding, winner):
        """TBD"""
        self.plan_retries()
        while True:
            result, whynot, status = None, None, None
            try:
                whynot = None
                self.throttle.delay_as_needed()
                try:
                    result = SubDownloader.osd_server.DownloadSubtitles(SubDownloader.session_id,
                        [subID])
                    self.downloaded_subtitle = winner
                    status = result['status']
                except ProtocolError as err:
                    status = '{} {}'.format(err.errcode, err.errmsg)
                except Exception as err:
                    status = '999 DownloadSubtitles() exception [{}]'.format(err)
                if status.startswith('200'):
                    # print('DB result:', result)
                    items = result.get('data', None)
                    item = items[0] if items and isinstance(items, list) else None
                    data = item.get('data', None) if isinstance(item, dict) else None
                    if data:
                        # print('DB: len(data):', len(result['data'][0]['data']))
                        decodedBytes = base64.b64decode(data)
                        decompressed = gzip.decompress(decodedBytes)
                        if len(decompressed) > 0:
                            try:
                                decodedStr = str(decompressed, subEncoding, 'replace')
                            except LookupError as exc:
                                whynot = 'decode error [{}]'.format(exc)
                            if not whynot:
                                try:
                                    byteswritten = open(subPath, 'w', encoding='utf-8'
                                            ).write(decodedStr)
                                    if byteswritten <= 0:
                                        whynot = 'zero bytes written'
                                except Exception as exc:
                                    whynot = 'write error [{}]'.format(exc)

                                # print('DB: byteswritten:', byteswritten, len(decodedStr),
                                        # len(decompressed), subPath)
                        else:
                            whynot = 'decompressed to zero bytes'
                    else:
                        whynot = 'empty result data'
                    if whynot:
                        SubDownloader.superPrint('error', 'Subtitling error!',
                                'Failed writing <b>{}</b> [{}]'.format(subPath, whynot))
                    return whynot
            except Exception as exc:
                SubDownloader.superPrint('error', 'Subtitiling error!',
                        'Exception writing <b>{}</b>[{}]'.format(subPath, str(exc)))
                print(traceback.format_exc())
                whynot = self.exit_code = '999 exception'
                return whynot

            if not self.retry_pause('DownloadSubtitles', status):
                break

        whynot = self.exit_code = status
        SubDownloader.superPrint('error', 'Subtitiling error!',
                'Failed downloading <b>{}</b> [{}]'.format(subPath, whynot))
        print('cannot download [{}]'.format(whynot))
        return whynot

    @staticmethod
    def get_exception_code(err):
        """Returns '901' for exceptions that we think should be re-tried because
        they have been seen when the server is temporarily in the toilet (which
        is all too common).
        """
        err_str = str(err).lower()
        for phrase in ('syntax error', 'no element found', 'request-sent'):
            if phrase in err_str:
                return '901' # retry-able
        return '999' # not identified as retry-able

    def plan_retries(self):
        """Setup for request retries."""
        self.rem_retry_on_busy, self.rem_retry_on_407, self.rem_retry_on_901 = 4, 0, 8
        if isinstance(self.opts.keep_trying, int):
            self.first_rem_retry_on_407 = self.rem_retry_on_407 = self.opts.keep_trying

    def retry_pause(self, doing, status):
        """Pause appropriately depending on the status code and returns:
         - the amount of time slept OR
         - 0 when we should just stop retrying.
         NOTE:
         - 407 Download limit reached
         - 429 Too many requests
         - 503 Service Unavailable OR Backend fetch failed
         - 520 Origin Error
         - 901 {Function} exception - normally 999s unless thought retryable

        """
        if self.rem_retry_on_407 > 0 and status.startswith(('407', '429', '503', '520', '901')):
            if (self.first_rem_retry_on_407 - self.rem_retry_on_407) % 10 == 0:
                print('DELAY:', 'minute sleeps w', self.rem_retry_on_407,
                        'remaining...', doing, status)
            self.rem_retry_on_407 -= 1
            sys.stdout.flush()
            time.sleep(60)
            return 60
        if self.rem_retry_on_busy > 0 and status.startswith(('429', '503', '520')):
            self.rem_retry_on_busy -= 1
            print('DB: sleep(3)', doing, status)
            time.sleep(3)
            return 3
        if self.rem_retry_on_901 > 0 and status.startswith(('901',)):
            self.rem_retry_on_901 -= 1
            print('DB: sleep(3)', doing, status)
            time.sleep(3)
            return 3

        print('DB: no retry on', doing, status)
        return 0 # break if out of retries or status is not 407, 429, or 503



# ==============================================================================
# ==== Main program (execution starts here) ====================================
# ==============================================================================
def runner(argv):
    """
    SubDownloader.py [H] - 'primitive' tool for downloading subs. In most cases,
    use 'subshop dos/redos', but runner() provides access to the lower level
    tool and all its arguments.
    """

    fetch = SubDownloader(argv)

    # ==== Get video paths, validate them, and if needed check if subtitles already exists
    for video in VideoFinder(fetch.opts.searchPathList):
        fetch.do_video_path(video)
        if fetch.exit_code:
            print('Fatal error:', fetch.exit_code)
            sys.exit(15)

    fetch.disconnect()
    sys.exit(0)
