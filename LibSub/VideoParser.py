#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Specialized videoname looking specifically for:
    - tv episodes with season/episode identifiers
    - "repack" designation
    - movies with year designation
We only try to pull out the
    - title of the tv show or movie
    - if tv episode:
      - the season
      - the episode
      - whether a "repack"
    - if movie, the year
"""
# pylint: disable=import-outside-toplevel,too-many-instance-attributes,broad-except,too-many-branches
# pylint: disable=too-many-arguments,too-many-nested-blocks
import re
import os
from types import SimpleNamespace
from ruamel.yaml import YAML
from LibGen.YamlDump import yaml_dump
from LibGen.CustLogger import CustLogger as lg
from LibSub import ConfigSubshop
from LibSub.PlexQuery import PlexQuery

yaml = YAML()
yaml.default_flow_style = False

class VideoFinder:
    """This is a generally use class to turn command line arguments (i.e, 'terms')
    into a list of videofile pathnames.  The terms may be:
        - a list of files and directories, or
        - a crude videofile/videoset search specification
    """
    def __init__(self, terms, allow_title=True, only=None, every=True,
            just_locations=False, use_plex=None):
        lg.tr3('terms:', terms, 'allow_title:', allow_title, 'plex?', use_plex)
        self.terms = terms
        self.allow_title = allow_title
        self.only = only  # if not both, only "tv" or "movie"
        self.every = bool(every or just_locations) # return every match, not just shortest
        self.just_locations = just_locations # return just the TV show folders and movies
        self.spec = None # set if filtering on title/season/episode/year
        self.yield_cnt = 0
        self.is_tv_tree = False
        self.is_movie_tree = False
        self.is_unk_tree = True
        self.use_plex = use_plex
        self.plex = None  # if using Plex for searches
        self.candidates = {}  # only populated if not "every"
        self.done_shows = set() # only populated when returning "locations" to avoid dup shows
        if self.use_plex is None:
            self.use_plex = VideoParser.params.cmd_opts_defaults.search_using_plex

    def _set_tree_type(self, is_tv_tree=False, is_movie_tree=False):
        if is_tv_tree:
            self.is_tv_tree, self.is_movie_tree, self.is_unk_tree = True, False, False
        elif is_movie_tree:
            self.is_tv_tree, self.is_movie_tree, self.is_unk_tree = False, True, False
        else:
            self.is_tv_tree, self.is_movie_tree, self.is_unk_tree = False, False, True

    def __iter__(self):
#       if False and not self.terms:
#           lg.pr('iter:', 'nothing to do')
#           return # nothing to do
        if not self.terms or (os.path.isfile(self.terms[0]) or os.path.isdir(self.terms[0])):
            lg.tr3('iter:', 'calling _yield_files_and_folders()')
            yield from self._yield_files_and_folders()
        elif self.allow_title:
            lg.tr3('iter:', 'calling _yield_searched_videos()')
            yield from self._yield_searched_videos()
        else:
            # lg.pr('WARNING: no videofiles were given')
            return # nothing to do


    def _yield_files_and_folders(self):
        """Find video files in the given and folders
            - if the first term is neither a file or folder, then
            assume the terms make up a title specification and return None
            - else returns the list of video files whether empty or not
        """
        if not self.terms:
            if not self.only or self.only == 'tv':
                self.terms += VideoParser.params.tv_root_dirs
            if not self.only or self.only == 'movie':
                self.terms += VideoParser.params.movie_root_dirs

        for term in self.terms:
            # lg.db('term:', term, 'isfile:', os.path.isfile(term),
                    # 'isvideo:', TvHoard.has_video_ext(term))
            if os.path.isfile(term):
                if VideoParser.has_video_ext(term):
                    self.yield_cnt += 1
                    yield term
                else:
                    lg.pr(f'SKIP: not videofile: "{term}"')
            elif os.path.isdir(term):
                ocnt = self.yield_cnt
                yield from self._yield_videos_primitive(term)
                if ocnt == self.yield_cnt:
                    lg.pr(f'SKIP: no videofiles in: "{term}"')
            else:
                lg.pr(f'SKIP: neither videofile nor folder: "{term}"')

        if not self.yield_cnt:
            lg.pr('WARNING: no videofiles were found')

    def _yield_searched_videos(self):
        self._decode_spec()
        if not self.spec.title:
            lg.pr(f'WARNING: no valid title given: {self.terms}')
            return
        lg.tr3('iter:', 'would filter on spec:', vars(self.spec))
        if self.use_plex:
            self.plex = PlexQuery()
            if not self.plex.plex: # not configured if server unset
                self.plex = None

        if not self.only or self.only == 'tv' or self.spec.se_term:
            yield from self._yield_search_tv_episodes()

        if (self.every or not self.yield_cnt) and not self.spec.se_term and (
                not self.only or self.only == 'movie'):
            yield from self._yield_search_movies()

    def _yield_search_tv_episodes(self):
        self._set_tree_type(is_tv_tree=True)
        if self.plex:
            folders, _ = self.plex.get_locations(self.spec.title, tv=True)
            lg.db('searched plex tv:', self.spec.title, folders)
            for folder in folders:
                if self.just_locations:
                    self.yield_cnt += 1
                    yield folder
                else:
                    yield from self._yield_videos_primitive(folder)
        else:
            for folder in VideoParser.params.tv_root_dirs:
                lg.tr3(f'_yield_videos_primitive({folder})')
                yield from self._yield_videos_primitive(folder)

        if self.candidates: # only if not yielding every match
            sorted_shows = sorted(list(self.candidates.keys()), key=len)
            winner = sorted_shows[0] # shortest show name wins
            match_cnt = len(sorted_shows)
            if match_cnt > 1:
                reveal_cnt = 4 if match_cnt == 4 else min(3, match_cnt)
                lead = '|' * 6
                lg.pr(lead, f'NOTE: {match_cnt} shows matched for "{self.spec.title}";',
                        'picked shortest:')
                for idx in range(reveal_cnt):
                    lg.pr(lead, '-' if idx else '*', sorted_shows[idx])
                if match_cnt > reveal_cnt:
                    lg.pr(lead, f'... and {match_cnt-reveal_cnt} more')
            for video in self.candidates[winner]:
                yield video

    def _yield_search_movies(self):
        self._set_tree_type(is_movie_tree=True)
        if self.plex:
            _, movies = self.plex.get_locations(self.spec.title, movie=True)
            lg.tr5('searched plex movies:', self.spec.title, movies)
            for movie in movies:
                self.yield_cnt += 1
                if self.every or self.just_locations:
                    yield movie
                else:
                    self.candidates[movie] = VideoParser(movie)
        else:
            for folder in VideoParser.params.movie_root_dirs:
                yield from self._yield_videos_primitive(folder)

        if self.candidates: # only if not yielding every match
            sorted_parsed = sorted(list(self.candidates.keys()),
                    key=lambda x: len(self.candidates[x].title))
            lg.tr5('sorted_parsed:', sorted_parsed)
            winner = sorted_parsed[0] # shortest movie title wins
            match_cnt = len(sorted_parsed)
            if match_cnt > 1:
                show_cnt = 4 if match_cnt == 4 else min(3, match_cnt)
                lead = '|' * 6
                lg.pr(lead, f'NOTE: {match_cnt} movies matched for "{self.spec.title}";',
                        'picked shortest:')
                for idx in range(show_cnt):
                    parsed = self.candidates[sorted_parsed[idx]]
                    lg.pr(lead, '-' if idx else '*', parsed.title, f'({parsed.year})')
                if match_cnt > show_cnt:
                    lg.pr(lead, f'... and {match_cnt-show_cnt} more')
            yield winner


    @staticmethod
    def _normalize(title):
        """Normalizes titles for the purpose of comparisons.
            - make '&' become ' and '
            - make non-word characters and '_' become spaces
            - consolidate white space and strip from both ends
            - convert to lower case
        """
        if not isinstance(title, str):
            return ''
        rv = re.sub(r'[\&]+', ' and ', title)
        rv = re.sub(r'[^\w]+', ' ', title)
        rv = re.sub(r'[_\s]', ' ', rv)
        rv = rv.strip().lower()
        lg.tr9(f'_normalize({title})={rv}')
        return rv

    def _decode_spec(self):
        """Given terms, decode as following:
            - trailing NxM, sNeM, assumed to be episode specs
            - an eposide spec (even 'x') is a strong indicator of TV series
            - the title are the words before the episode specs if given
        """
        spec = SimpleNamespace(title=[], season=None, episode=None, se_term='')
        for idx in range(len(self.terms)-1, -1, -1):
            term = self.terms[idx]
            if not spec.se_term:
                mat = re.match(r'^s(\d+)(|e(\d+))$', term, re.IGNORECASE)
                if mat:
                    season, episode = mat.group(1, 3)
                else:
                    mat = re.match(r'^(\d*)x(\d*)$', term, re.IGNORECASE)
                    if mat:
                        season, episode = mat.group(1, 2)
                if mat:
                    season = int(season) if len(season) > 0 else None
                    episode = int(episode) if len(episode) > 0 else None
                    spec.season, spec.episode, spec.se_term = season, episode, term
                    self.terms.pop(idx)
                    continue
            break
        if len(self.terms) >= 0:
            spec.title = self._normalize(' '.join(self.terms).lower())
        self.spec = spec

    def _yield_videos_primitive(self, folder, show_name=None):
        """Recursively gather all the video file pathnames. NOTE:
          - if store is list, the videos are put into the single list by full pathname
          - if store is dict, then the basename of the videos are put into a list per folder
          - once a folder is found with videos, do NOT go deeper
        """
        def yield_new_show(folder):
            nonlocal self
            if folder in self.done_shows:
                return
            self.done_shows.add(folder)
            self.yield_cnt += 1
            yield folder

        if show_name is None:
            show_name = os.path.basename(folder)
        lg.tr5('_yield_videos_primitive:', folder, show_name)
        basenames = os.listdir(folder)
        prev_yield_cnt, folders = self.yield_cnt, []
        ok_dir = False # until it passes
        for basename in basenames:
            path = os.path.join(folder, basename)
            if os.path.isfile(path) and VideoParser.has_video_ext(basename):
                parsed = None
                if not ok_dir:
                    spec, spec_has_tv_sea_or_ep = self.spec, False
                    if spec and (spec.season is not None or spec.episode is not None):
                        spec_has_tv_sea_or_ep = True

                    if not self.plex and spec:
                        tv_match = False
                        if self.is_tv_tree:
                            if spec.title not in self._normalize(show_name):
                                return
                            tv_match = True
                        elif self.is_unk_tree and spec_has_tv_sea_or_ep:
                            if spec.title not in self._normalize(show_name):
                                return
                            tv_match = True
                        if tv_match and self.just_locations:
                            if VideoParser.seasondir_pat.match(os.path.basename(folder)):
                                yield from yield_new_show(os.path.dirname(folder))
                            else:
                                yield from yield_new_show(folder)
                            return # no more from this subtree
                    ok_dir = True

                if spec and spec_has_tv_sea_or_ep:
                    parsed = VideoParser(path)
                    if spec.season is not None and spec.season != parsed.season:
                        continue
                    if spec.episode is not None and spec.episode != parsed.episode:
                        continue
                elif spec:
                    parsed = VideoParser(path)
                    # lg.db('parsed:', vars(parsed))
                    if spec.title not in self._normalize(parsed.title):
                        continue

                self.yield_cnt += 1
                if self.just_locations or self.every or (not self.spec and not self.plex):
                    yield path
                else:
                    if self.is_tv_tree:
                        lst = self.candidates.get(show_name, [])
                        lst.append(path)
                        if len(lst) <= 1:
                            self.candidates[show_name] = lst
                    else:
                        self.candidates[path] = parsed if parsed else VideoParser(path)

            elif os.path.isdir(path) and not path.endswith('.cache'):
                folders.append(path)
        if prev_yield_cnt == self.yield_cnt:  # go deeper only if nothing found here
            for path in folders:
                basename = os.path.basename(path)
                if not VideoParser.seasondir_pat.match(basename):
                    show_name = basename
                yield from self._yield_videos_primitive(path, show_name)


class VideoParser():
    """TBD"""
    params = ConfigSubshop.get_params()
    accumulate_junk = False # for creating 'junk' words list
    junk = {}

    # sets of extensions (note that the leading '.' is not included)
    vid_exts = set(('avi mp4 mov mkv mk3d webm ts mts m2ts ps vob evo mpeg'
                    ' mpg m1v m2p m2v m4v movhd movx qt mxf ogg ogm ogv rm rmvb'
                    ' flv swf asf wm wmv wmx divx x264 xvid').split())
    # for movies w/o a year separator, these words are assumed to be the first
    # non-title work in the junk after the title.
    not_titles = ('1080p 480p 576p 720p'  # actually seen as 1st junk
        ' bd bdrip bluray brrip cd1 cd2'
        ' dvdrip dvdscr extended'
        ' hdrip hdts hdtv japanese korsub'
        ' proper remastered repack web webrip'
        ' bbc 10bit 2hd aaa aac aac2 ac3 afg aks74u amzn bmf'  # junk but NOT seen as 1st junk
        ' cm8 cmrg crazy4ad d3fil3r d3g dd5 drngr dsnp'
        ' evo fgt ftp fum galaxytv gaz'
        ' h264 h265 hevc ion10 it00nz lol m2g'
        ' megusta msd nhanc3 nodlabs notv npw nsd ozlem pdtv'
        ' rarbg rerip rgb sfm shitbox sticky83 stuttershit tbs'
        ' tepes tvv vtv vxt w4f x0r x264 x265 xvid xvidhd yify zmnt'
        .split())
    not_titles_re = rf'{"|".join(not_titles)}' # '1080p|480p|...|webrip'

    oksubs = ('.srt', '.smi', '.ssa', '.ass', '.vtt') # most to least prefered
    sub_exts = {x[1:] for x in oksubs}
    vid_sub_exts = vid_exts | sub_exts

    # compiled patterns to apply to filenames to categorize extension
    vid_ext_pat = re.compile(rf'\.({"|".join(vid_exts)})$', re.IGNORECASE)
    sub_ext_pat = re.compile(rf'\.({"|".join(sub_exts)})$', re.IGNORECASE)
    vid_sub_ext_pat = re.compile(rf'\.({"|".join(vid_sub_exts)})$', re.IGNORECASE)

    seasondir_pat = re.compile(r'^season\s*(\d+)$', re.IGNORECASE)  # season folder pattern
    specialsdir_pat = re.compile(r'^specials?\b', re.IGNORECASE)  # specials folder

    # -- TODO: NO match cases *might* want to handle ---
    # American Experience s22e06b Eleanor Roosevelt 2.mp4
    # (1991) American Experience Empire of the Air
    # Big.Little.Lies.Part.1.iNTERNAL.720p.HEVC.x265-MeGusta.mkv
    # Friends - [1x08] - The One where Nana dies Twice.mkv
    # The.X-Files.S09e19e20.480P.Web.Dl.Nsd.X264-Nhanc3-37.mkv
    # Star.Trek.Discovery.S02E00b.Short.Treks.Runaway.720p.HEVC.x265-MeGusta.mkv
    # Adam.Ruins.Everything.S01.Special-Election.Special.720p.HEVC.x265-MeGusta.mkv
    # [AnimeRG] One Piece Special (2018) Episode of Skypiea! [1080p].mkv
    # Samurai Jack - 0xSpecial 4 - Genndy's Scrapbook.avi

    sep = r'[.\-\[\]\s]+'
        # e.g., to trash [*] in '[HorribleSubs] One Piece - 808 [480p].mkv'
    trash_in_front_re = r'^(?:\[[^\]]*\]|)[.\-\s]*'
    hi_ep = r'(?:(?:-e|-|e)(\d{1,3})|)\b'

    # regexes to pull out title, season, episode, episode_hi, year...
    regexes = { 'tv': [
            # title and episode REs $1=title $2=season $3=episode $4=episode_hi
            # 1=strong TV indicator, 0=weak/not TV indicator
        (1, r'(.*?)' + sep + r's(\d{1,3})[.\s]*e(\d{1,3})' + hi_ep), # title S09E02[03]
        (1, r'(.*?)' + sep + r'(\d{1,3})x(\d{1,3})' + hi_ep),  # title 9x02
        (1, r'(.*?)' + sep + r'(\d{1,3})(\d\d)(\d\d)\b'),  # title 90203
        (0, r'(.*?)' + sep + r'(\d{1,3})(\d\d)\b' + hi_ep),  # title 902
        (1, r'()s(\d{1,3})e(\d{1,3})[\s\.]*' + hi_ep), # no-title S09E02
        (1, r'(.*?)' + sep + r's(\d{1,3})[.\s\-]+(\d{1,3})' + hi_ep), # title S09E02[03]
        (0, r'(.*?)' + sep + r'\s*-\s*()(\d{1-3})' + hi_ep),  # title - 02
        (0, r'(.*?)' + sep + 'part()' + sep + r'(\d{1,3})' + hi_ep), # title part 1
        ], 'movie': [
            # title and year REs $1=title $2=year
        (0, r'(.*?)' + sep + r'\(((?:19|20)\d\d)\)'), # title (2020)
        (0, r'(.*)' + sep + r'\b((?:19|20)\d\d)\b'), # title 2020 : look for last
        (0, r'(.*?)' + sep + rf'()(?=\b(?:{not_titles_re})\b)'), # title followed by junk
        ]}

    compiled_regexes = {}

    @staticmethod
    def has_video_ext(path):
        """Does the video file have a standard video file extension?"""
        return bool(VideoParser.vid_ext_pat.search(path))

    @staticmethod
    def has_subt_ext(path):
        """Does the subtitle file have a standard subtitle file extension?"""
        return bool(VideoParser.sub_ext_pat.search(path))

    def is_tv_episode(self):
        """Return true if has season and episode set."""
        return bool(self.episode is not None and self.season is not None)

    def has_tv_sea_or_ep(self):
        """Return true if has season OR episode set."""
        return bool(self.episode is not None or self.season is not None)

    def is_movie_year(self):
        """Return true if has year set (w/o season and episode set)."""
        return bool(self.year is not None and not self.is_tv_episode())

    def is_same_episode(self, rhs):
        """Return True if season and epsiode agree (and are non-None)."""
        return (self.is_tv_episode() and rhs.is_tv_episode
                and self.season == rhs.season and self.episode == rhs.episode)

    def is_same_movie_year(self, rhs):
        """Return True years agree (and are non-None AND not tv episodes)."""
        return bool(self.is_movie_year() and rhs.is_movie_year() and self.year == rhs.year)

    def is_error(self):
        """Cannot parse as tv episode or movie."""
        return not bool(self.re_key)

    @staticmethod
    def type_hint_by_path(videopath):
        """Get a hint of whether the video is a tv episode or movie
        per its location in the file system."""
        hint = SimpleNamespace(movie=False, tv=False)
        if os.path.isfile(videopath):
            for root in VideoParser.params.tv_root_dirs:
                if root == os.path.commonpath([root, videopath]):
                    hint.tv = True
                    return hint
            for root in VideoParser.params.movie_root_dirs:
                if root == os.path.commonpath([root, videopath]):
                    hint.movie = True
                    return hint
        return hint

    def check_special(self, expect_movie, videopath):
        """Check whether this video is likely to be a TV special
        setting .is_special accordingly."""
        self.is_special = False # until proven otherwise
        if self.is_movie_year() or expect_movie:
            pass
        elif self.season is not None and self.season == 0:  # s00 => special
            self.is_special = True
        elif self.episode is not None and self.episode == 0: # e00 => special
            self.is_special = True
        else:
            parentd = os.path.basename(os.path.dirname(videopath))
            if VideoParser.specialsdir_pat.match(parentd): # in Specials => special
                self.is_special = True
            else:
                mat = VideoParser.seasondir_pat.match(parentd)
                if mat and int(mat.group(1)) == 0:
                    self.is_special = True


    def __init__(self, videopath, expect_episode=None, expect_movie=None):
        videopath = os.path.abspath(videopath)  # need full path to get TV/Movie hint
        self.corename, self.ext = os.path.splitext(os.path.basename(videopath))
        if self.ext[1:] not in self.vid_sub_exts:
            self.corename, self.ext = self.corename + self.ext, ''
        self.title, self.raw_title, self.is_repack, self.year = None, None, None, None
        self.season, self.episode, self.episode_hi = None, None, None
        self.re_key, self.hint, self.is_special = '', '', False
        if expect_episode is None and expect_movie is None:
            hint = self.type_hint_by_path(videopath)
            lg.tr9('VideoParser type_hint:', vars(hint))
            expect_episode, expect_movie = hint.tv, hint.movie
        self._parse(expect_episode=expect_episode, expect_movie=expect_movie)
        self.check_special(expect_movie, videopath)

    def get_essence_dict(self):
        """Returns the 'essential' vars that represent the result."""
        rv = {}
        for key in ('title', 'raw_title', 'is_repack', 'year', 'season', 'episode', 'episode_hi'):
            rv[key] = getattr(self, key)
        return rv

    def mini_str(self, verbose=True):
        """TBD"""
        key = self.re_key if self.re_key else 'n/a'
        hint = self.hint if self.hint else 'any'

        return (f'{key + " " if verbose else ""}"{self.title}"'
                + (f' s{self.season:}e{self.episode}' if self.episode is not None else '')
                + (f'-{self.episode_hi}' if self.episode_hi else '')
                + (f' Y={self.year}' if self.year else '')
                + (f'{" special" if self.is_special else ""}')
                + (f'{" repack" if self.is_repack else ""}')
                + (f'{" " + hint if verbose else ""}')
                + (f' {self.ext if self.ext else "n/a"}'))


    def _parse(self, expect_episode=None, expect_movie=None):
        """From the regex lists above, assemble and test REs against the
        filename until a match is reached or the lists are exhausted.
        We must always dig out:
          - title (of show)
          - season of episode
          - episode number of episode
          - file suffix

        """
        # pylint: disable=no-member
        if bool(expect_movie) and not bool(expect_episode):
            cats = ('movie', 'tv')
            self.hint = 'movie'
        elif not bool(expect_movie) and bool(expect_episode):
            cats = ('tv', 'movie')
            self.hint = 'episode'
        else:
            cats = ('movie', 'tv')

        lg.tr9('DB cats:', cats)

        hits = []
        force_tv = -1 # if set indicates we need to force the tv hit
        for cat in cats:
            # for idx, pat in enumerate(self.regexes[cat]):
                # for idx, pat in enumerate(self.regexes[cat]):
            for idx in range(len(self.regexes[cat])):
                key = f'{cat[:3]}{idx}'
                lg.tr8('VideoParser: trying:', key, self.regexes[cat][idx])
                compiled_re = self.compiled_regexes.get(key, None)
                if not compiled_re:
                    pat = self.regexes[cat][idx][1]
                    compiled_re = re.compile(self.trash_in_front_re + pat
                            + r'.*?(\brepack\b|)', re.IGNORECASE)
                    self.compiled_regexes[key] = compiled_re

                match = compiled_re.match(self.corename)
                lg.tr9('VideoParser pat:', compiled_re.pattern, self.corename, match,
                        match.groups() if match else '')
                if match:
                    lg.tr7('VideoParser: matched:', self.regexes[cat][idx])
                    if self.accumulate_junk:
                        print('    MATCH:', match.group(0))
                        print('    END:', self.corename[match.end():])
                        words = re.split(r'[\s\.\-=]+', self.corename[match.end():])
                        idx = 0
                        for word in words:
                            if len(word) < 3:
                                continue
                            if re.match(r'^\d+$', word):
                                continue
                            word = word.lower()
                            count = self.junk.get(word, 0)
                            count += 1
                            self.junk[word] = count
                            print('   ' if idx>0 else '', word, self.junk[word])
                            idx += 1

                    hit = SimpleNamespace(season=None, episode=None, episode_hi=None,
                            year=None, is_repack=False, re_key=None)
                    # pylint: disable=broad-except
                    hit.raw_title = match.group(1)
                    hit.title = match.group(1).replace('.', ' ')
                    if self.regexes[cat][idx][0]:
                        force_tv = len(hits)
                    hits.append(hit)
                    if cat == 'tv':
                        hit.season = match.group(2)
                        hit.season = 1 if hit.season == '' else int(hit.season)
                        hit.episode = int(match.group(3))
                        hit.episode_hi = match.group(4)
                        hit.episode_hi = int(hit.episode_hi) if hit.episode_hi else None
                        hit.is_repack = bool(match.group(5))
                        hit.re_key = key
                        # NOTE: this is speculative ... use date of specials to disambiguate
                        lg.tr5('VideoParser hit:', vars(hit))
                    else:
                        hit.year = match.group(2)
                        hit.year = int(hit.year) if hit.year else None
                        hit.re_key = key
                    break
            ### if hits and self.hint: # with a hit, take the first hit
                ### break

        if len(hits) == 0:
            self.raw_title = self.corename
            self.title = self.corename.replace('.', ' ')
            return
        if len(hits) == 1:
            winner = hits[0]
        elif len(hits) == 2:
            winner, loser = hits[0], hits[1]
            if force_tv >= 0:
                winner, loser = hits[force_tv], hits[0 if force_tv else 1]
            elif hits[1].year and hits[0].season and hits[0].episode:
                # preferred tv, but the tv season episode looks like a valid year
                # and there is a movie year match.  Go for the movie.
                if 1900 <= 100*int(hits[0].season) + int(hits[0].episode) <= 2099:
                    winner, loser = hits[1], hits[0]
                    lg.tr1('VideoParser: override as movie')
            elif not hits[0].year and hits[1].season and hits[1].episode:
                # preferred movie, but NOT a strong movie match, and a strong season/episode
                # match, so pick the TV episode match
                lg.tr1('VideoParser: override as tvshow')
                winner, loser = hits[1], hits[0]
            if winner.season and winner.episode:
                # if year or other junk precedes the season/episode, get rid if year/junk
                if len(loser.title) < len(winner.title):
                    winner.title = loser.title
                    winner.year = loser.year  # seems to be a net win; jury out
        else:
            assert False, hits


        self.title = winner.title
        self.raw_title = winner.raw_title
        self.season = winner.season
        self.episode = winner.episode
        self.episode_hi = winner.episode_hi
        self.year = winner.year
        self.is_repack = winner.is_repack
        self.re_key = winner.re_key
        lg.tr1('VideoParser: result:', vars(self))


    @staticmethod
    def run_regressions(verbose=False):
        """TBD"""
        tests = yaml.load(VideoParser.tests_yaml)
        fail_cnt, results = 0, {}
        for filename, result_dict in tests.items():
            # lg.info(filename)
            parsed = VideoParser(filename)
            nres = parsed.mini_str()
            ores = result_dict.get('result', {})
            ok = 'OK' if nres == ores else 'FAIL'
            if ok != 'OK' or verbose:
                lg.pr(f'{ok:4s}: {filename}')
                lg.pr(f'- nres: {nres}')
                if ok != 'OK':
                    lg.pr(f'- ores: {ores}')
                    fail_cnt += 1
            results[filename] = {'result': nres}

        lg.pr(f'TEST Summary: {fail_cnt} failures of {len(tests)} tests')

        if verbose and fail_cnt:
            lg.pr("\nTEST DUMP w new results:\n")
            yaml_dump(results, flow_nodes=('result',), indent=4)

    @staticmethod
    def parse_file(filename, verbose=False):
        """Test code for actual files."""
        parsed = VideoParser(filename)
        whynot = ''
        has_s_e = bool(parsed.season is not None and parsed.episode is not None)
        has_s_or_e = bool(parsed.season is not None or parsed.episode is not None)
        has_yr = bool(parsed.year is not None)
        if parsed.hint == 'episode':
            seems_ok = bool(has_s_e or parsed.is_special)
            if not seems_ok:
                whynot = 'expecting TV episode but w/o Season+Episode'
        elif parsed.hint == 'movie':
            seems_ok = not has_s_or_e and not parsed.is_special and has_yr
            if not seems_ok:
                whynot = 'expecting movie but' + (' w Season or Episode' if has_s_or_e else ''
                        ) + ('' if has_yr else ' w/o Year')
        else:
            seems_ok = (has_s_e and not has_yr) or (not has_s_or_e and has_yr) or parsed.is_special
            if not seems_ok:
                whynot = 'unsure of category but parses neither as TV episode/special nor movie'

        if verbose or not seems_ok:
            dirname, basename = os.path.dirname(filename), os.path.basename(filename)
            lg.pr('\n' + basename, f'IN {dirname}' if dirname else '')
            lg.pr(f'    {parsed.mini_str(verbose=True)}')
            if not seems_ok:
                lg.pr('    ERROR:', whynot)
        return seems_ok

    tests_yaml = r"""
    !!omap
    - Yellowstone.2018.S03E08.720p.HEVC.x265-MeGusta.mkv: !!omap
      - result: tv0 "Yellowstone" s3e8 Y=2018 any .mkv
    - Law.and.Order.S18E01-E02.Called.Home.and.Darkness.2008.DVDRip.x264-TVV.mkv: !!omap
      - result: tv0 "Law and Order" s18e1-2 any .mkv
    - The.Amazing.World.of.Gumball.S03E13E14.720p.WEB-DL.AAC2.0.H.264-iT00NZ-7.mkv: !!omap
      - result: tv0 "The Amazing World of Gumball" s3e13-14 any .mkv
    - The Amazing World of Gumball - 132 - The Curse-28.mkv: !!omap
      - result: tv3 "The Amazing World of Gumball" s1e32 any .mkv
    - when.calls.the.heart.s06e07.repack.webrip.x264-tbs.mkv: !!omap
      - result: tv0 "when calls the heart" s6e7 any .mkv
    - penny.dreadful.205.hdtv-lol.mp4: !!omap
      - result: tv3 "penny dreadful" s2e5 any .mp4
    - American Experience s24e03-04 The Clinton Years.avi: !!omap
      - result: tv0 "American Experience" s24e3-4 any .avi
    - Homeland S01 E01 - 480p - BRRip - x264 - AAC 5.1 -={SPARROW}=-.mp4: !!omap
      - result: tv0 "Homeland" s1e1 any .mp4
    - Friends - [1x08] - The One where Nana dies Twice.mkv: !!omap
      - result: tv1 "Friends" s1e8 any .mkv
    - Captain Alatriste The Spanish Musketeer (2006).mkv: !!omap
      - result: mov0 "Captain Alatriste The Spanish Musketeer" Y=2006 any .mkv
    - Wonder.Woman.1984.2020.720p.HMAX.WEBRip.AAC2.0.X.264-EVO.mkv: !!omap
      - result: mov1 "Wonder Woman 1984" Y=2020 any .mkv
    - law.and.order.svu.220.dvdrip.avi: !!omap
      - result: tv3 "law and order svu" s2e20 any .avi
    - '[HorribleSubs] One Punch Man S2 - 11 [480p].mkv': !!omap
      - result: tv5 "One Punch Man" s2e11 any .mkv
    - Gone with the Wind.1939: !!omap
      - result: mov1 "Gone with the Wind" Y=1939 any n/a
    - Gone with the Wind.avi: !!omap
      - result: n/a "Gone with the Wind" any .avi
    - Big.Little.Lies.Part.1.iNTERNAL.720p.HEVC.x265-MeGusta.mkv: !!omap
      - result: tv7 "Big Little Lies" s1e1 any .mkv
    - The.Flash.2014.S06E06.720p.HEVC.x265-MeGusta.mkv: !!omap
      - result: tv0 "The Flash" s6e6 Y=2014 any .mkv
    - Borat.PROPER.DVDRip.XviD-DoNE.avi: !!omap
      - result: mov2 "Borat" any .avi
    - Samurai Jack - 0xSpecial 4 - Genndy\'s Scrapbook.avi: !!omap
      - result: n/a "Samurai Jack - 0xSpecial 4 - Genndy\'s Scrapbook" any .avi
    - American Experience s22e06b Eleanor Roosevelt 2.mp4: !!omap
      - result: n/a "American Experience s22e06b Eleanor Roosevelt 2" any .mp4
    """



def runner(argv):
    """
    VideoParser.py [H] implements:
        - VideoParser - decodes downloaded video filenames into basic parts
        - VideoFinder - provides an iterator for all the discovered videos
          given a list of files and folders OR search terms (i.e., targets).
    Its runner() implements three distinct flavors/tests:
    (1) --regression:
        Runs regression tests on the parsing alone. See the tests_yaml string
        for the tests and expected results to survey handled filenames.
    (2) -j/--just-search {terms}
        Shows the results of searches as locations which are:
          - the directories of TV shows
          - the video file of movies
    (3) {targets}
        Shows the video files corresponding to the targets; in case of
        a search, only shows "shortest" match (although 'subshop' commands
        normally process all matches). Use -e/--every for all matches.
    """
    import argparse
    parser = argparse.ArgumentParser(prog='VideoParser.py',
            description='test torrent filename parser')
    parser.add_argument('--regression', action='store_true',
            help='run regression tests')
    parser.add_argument('-e', '--every', action='store_true',
            help='when searching title, act on every match not just first')
    parser.add_argument('-j', '--just-search', action='store_true',
            help='report show directories and movie video files')
    parser.add_argument('-o', '--only', default=None, choices=('tv', 'movie'),
            help='select only for videos under tv or movie roots')
    parser.add_argument('-p', '--use-plex', action='store_true',
            help='use Plex for searches (if configured)')
    parser.add_argument('-P', '--avoid_plex', action='store_true',
            help='do NOT use Plex for searches')
    parser.add_argument('-v', '--verbose', action='store_true',
            help='show all parsed videos, not just exceptions')
    parser.add_argument('-V', '--log-level', choices=lg.choices,
        default='INFO', help='set logging/verbosity level [dflt=INFO]')
    parser.add_argument('targets',
            help="video files/folders/spec (uses built-in tests if none)", nargs='*')

    opts = parser.parse_args(argv)
    lg.setup(level=opts.log_level)
    opts.use_plex = True if opts.use_plex else False if opts.avoid_plex else None

    if opts.regression:
        lg.pr("RUNNING REGRESSION TESTS")
        VideoParser.run_regressions(verbose=opts.verbose)
    elif opts.just_search:
        for location in VideoFinder(opts.targets, every=opts.every, only=opts.only,
                use_plex=opts.use_plex, just_locations=True):
            print(location)
    else:
        if not opts.verbose:
            lg.pr('PRINTING:'
                    '\n - TV Videos w/o detected Season/Episode'
                    '\n - Movie Videos w/o detected Year OR w detected Season or Episode')
        ok_cnt, not_ok_cnt = 0, 0
        for video in VideoFinder(opts.targets,
                every=opts.every, only=opts.only, use_plex=opts.use_plex):
            if VideoParser.parse_file(video, verbose=opts.verbose):
                ok_cnt += 1
            else:
                not_ok_cnt += 1
        print(f'\nSUMMARY: ok={ok_cnt} not_ok={not_ok_cnt}')

        if VideoParser.accumulate_junk:
            words = sorted(list(VideoParser.junk.keys()), key=lambda x: VideoParser.junk[x])
            for word in words:
                print(VideoParser.junk[word], word)
