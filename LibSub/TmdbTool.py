#!/bin/env python3
# -*- coding: utf-8 -*-
"""Tool for TMDb queries. Matches are return as an array of namespaces having:
    - Title (e.g, 'Blue Bloods')
    - Year (e.g, '2010', '2010+', '2011-2013')
    - imdbID (i.e, ttXXXXXXX)
    - Type (i.e, 'movie', 'series', 'episode')
    - Overview (i.e., 'Blah blah blah')

NOTE: uses imdb as backup
"""
# pylint: disable=broad-except,import-outside-toplevel,too-many-instance-attributes
import sys
import os
import json
import re
import traceback
import readline
import shutil
import textwrap
from types import SimpleNamespace
import urllib
import requests
from requests.exceptions import ReadTimeout
from ruamel.yaml import YAML
from LibGen.YamlDump import yaml_dump, yaml_str
from LibGen.CustLogger import CustLogger as lg
from LibSub import ConfigSubshop
from LibSub.VideoParser import VideoParser, VideoFinder
# from YamlDump import yaml_dump

yaml = YAML()
yaml.default_flow_style = False

class TmdbTool:
    """Class for find and selecting best IMDB ID for video."""
    categories = {'m': 'movie', 's': 'series', 'e': 'episode'}
    expected_keys = {'Title', 'Year', 'imdbID', 'Type', 'Overview'}

    params = ConfigSubshop.get_params()
    tmdb_service = 'https://api.themoviedb.org/3'
    tmdb_apikey = params.credentials.tmdb_apikey

    terminal_columns = shutil.get_terminal_size((79, 20))[0]
    # lg.info('terminal_size:', shutil.get_terminal_size((79, 20)))

    def __init__(self):
        """TBD"""
        self.status_code = None # if 200, then there are matches
        self.matches = None
        self.winner = None
        self.search_phrase = None  # most recent value (a string)
        self.search_cat = None  # most recent value
        self.search_year = None  # most recent value
        self.search_is_movie = None # most recent value
        self.videopath = None # set when tied to video file
        self.subcache = None
        self.cached_omdbinfo = None

    def reset(self):
        """Reinitalize object."""
        self.__init__()

    @staticmethod
    def override(tmdb_apikey=None):
        """override configured APIKEY and or Image Viewer."""
        if tmdb_apikey:
            TmdbTool.tmdb_apikey = tmdb_apikey

    @staticmethod
    def info_str(match, w_overview=False, max_lines=None, indent=0, indent2=8):
        """return string representation of match."""
        if not match:
            return 'None'
        if isinstance(match.Year, str):
            year = match.Year[0:4] + ('+' if match.Year[4:] else '')
        else:
            year = None
        year_str = f' ({year})' if year else ''
        text = f'{match.Title}{year_str} {match.imdbID} [{match.Type}]'
        if w_overview:
            text += ' :: ' + match.Overview
        pref1 = ' '*indent if isinstance(indent, int) else str(indent)
        pref2 = ' '*indent2 if isinstance(indent2, int) else str(indent2)
        lines = textwrap.wrap(text, width=max(TmdbTool.terminal_columns, 40),
                max_lines=max_lines, initial_indent=pref1, subsequent_indent=pref2)
        return '\n'.join(lines)

    def get_omdbinfo(self, videopath, subcache):
        """Resolve the OMDB info for the given videofile and cached info file.
        """
        self.reset()
        if not os.path.isfile(videopath):
            raise ValueError('not a file: {videopath}')
        videopath = os.path.abspath(videopath)
        self.videopath, self.subcache = videopath, subcache

        info, imdbID = self._from_cache()
        if info:
            lg.tr5('cached info:', vars(info))
            # lg.info('cached info:', vars(info))
            self.search_cat = info.Type # influence searches
        else:
            # lg.info('no omdbinfo ...', imdbID)
            if isinstance(imdbID, str) and imdbID.startswith('tt'):
                infos = self.tmdb_lookup(imdbID)
                # lg.info('infos ...', infos)
                info = infos[0] if infos else None
                lg.tr5('replaced omdbinfo:', info)

            if not info:
                # lg.info('search ...', videopath)
                info = self.search_by_videopath(videopath, subcache.is_tvdir)
            if info:
                lg.tr1('updated info:', vars(info))
                self.commit_to_cache(info)
            else:
                lg.tr1('search for IMDb info failed:', videopath)


        self.cached_omdbinfo = info
        return info

    def _from_cache(self):
        # pylint: disable=too-many-boolean-expressions
        try:
            with open(self.subcache.get_omdbinfopath(), "r", encoding='utf-8') as fh:
                info = yaml.load(fh)
        except Exception:
            return (None, None)
        # lg.db('TmdbTool: cached info:', info)
        if not isinstance(info, dict):
            return None, None
        info_keys = set(info.keys())
        if self.expected_keys != info_keys:
            return None, info.get('imdbID', None)
        info = SimpleNamespace(**info)
        return info, info.imdbID

    def search_by_videopath(self, path, is_series):
        """Find the info by videopathname and whether in TV-land or Movie-land"""
        lg.tr1(f'search_by_videopath(path={path}, is_series={is_series}')
        parsed = VideoParser(path, expect_episode=is_series)
        lg.tr8('parsed:', vars(parsed))
        if parsed.is_error():
            lg.warn(f'VideoParser() failed to parse: {os.path.basename(path)}')
        elif is_series and not parsed.is_tv_episode():
            lg.warn('VideoParser() expected TV episode but parsed:', parsed.mini_str(),
                    '\n    ', os.path.basename(path))
        phrase = parsed.title if parsed.title else os.path.basename(path)
        if self.subcache.is_tvdir and self.subcache.omdb_dpath:
            # getting the phrase/title from the show folder is more consistent and
            # better than from the video file
            phrase = os.path.basename(self.subcache.omdb_dpath)
            # lg.info('phrase1:', phrase)
            mat = re.match(r'^(.*?)\s+\d+x[\d\-\,x]*$', phrase, re.IGNORECASE)
            if mat: # trimming 2x 2x-3x 2x,4x
                phrase = mat.group(1)
                # lg.info('phrase2:', phrase)

        # always OMDB first here since has highest quota
        self.tmdb_search_primitive(phrase, year=None if is_series else parsed.year,
                category='series' if is_series else 'movie')
        if self.matches:
            return self.matches[0]
        return None


    def commit_to_cache(self, info):
        """Overwrite the config file with an updated version."""
        folder = os.path.dirname(self.subcache.get_omdbinfopath())
        if not os.path.isdir(folder):
            os.makedirs(folder)
        with open(self.subcache.get_omdbinfopath(), "w", encoding='utf-8') as fh:
            yaml.dump(vars(info), fh)
        self.cached_omdbinfo = info


    def tmdb_request(self, cmd, params):
        """TBD"""
        # pylint: disable=protected-access
        params = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        try:
            service = f'{self.tmdb_service}/{cmd}'
            lg.tr9(f'calling requests.get({service}, {params}')
            resp = requests.get(service,  params=params,
                    timeout=self.params.download_params.imdb_timeout_secs)
        except ReadTimeout:
            lg.info(f'requests.get({service}, {params}) timeout')
            return None

        lg.tr9(vars(resp))
        self.status_code = resp.status_code
        if self.status_code != 200:
            lg.err(f'query failed: status={self.status_code} err={str(resp)}\n'
                    f'   cmd={cmd} params={params}')
            return None
        content =  json.loads(resp._content)
        return content

    @staticmethod
    def tmdb_make_namespace(cat, match, imdbID=None):
        """Make the OMDb namespace from the result."""
        try:
            ns = SimpleNamespace()
            ns.Title = match.get('name', match.get('title', None))
            ns.Year = match.get('first_air_date', match.get('release_date'))
            if isinstance(ns.Year, str):
                ns.Year = ns.Year[0:4]
            else:
                ns.Year = None
            ns.imdbID = imdbID
            ns.Type = cat if cat else match.get('media_type', None)
            ns.Type = 'series' if ns.Type and ns.Type == 'tv' else ns.Type
            ns.Overview = match['overview']
        except Exception as exc:
            lg.err(f'tmdb_make_namepace() failed [{exc}]\n' + yaml_str(match))
            raise
        return ns

    def tmdb_lookup(self, imdbID):
        """Makes the requested OMDb lookup with the given imdbID (of form ttNNNNNN)
        and returns:
            - the status_code (e.g., 200 is success)
            - if 200, the result as a SimpleNamespace
            - else a string describing the error
        """
        self.status_code, self.matches, self.winner = 0, None, None
        params = {'api_key': str(self.tmdb_apikey), 'external_source': 'imdb_id'}
        self.search_phrase = imdbID
        cmd = f'find/{imdbID}'
        content = self.tmdb_request(cmd, params)

        if content:
            if content['movie_results']:
                cat, match = 'movie', content['movie_results'][0]
            elif content['tv_results']:
                cat, match = 'series', content['tv_results'][0]
            else:
                cat, match = None, None

        if match:
            ns = self.tmdb_make_namespace(cat, match, imdbID=imdbID)
            self.matches = [ns]
        return self.matches

    def tmdb_search_primitive(self, phrase, year=None, category=None):
        """Makes the requested query with
            - mandatory title string,
            - optional year (i.e. 19xx or 20xx)
            - optional category (i.e., 'movie', 'series', 'episode') or 1st letter

        Returns the matches.
        """
        # pylint: disable=protected-access
        lg.tr1('tmdb_search_primitive:', phrase, 'yr:', year, 'cat:', category)
        if re.match(r'^tt\d+$', phrase):
            return self.tmdb_lookup(phrase)

        self.status_code, self.matches, self.winner = 0, None, None
        params = {'api_key': str(self.tmdb_apikey), 'query': phrase}
        self.search_phrase = phrase

        if year:
            year = str(year)
            self.search_year = None
        if year and re.match(r'^(19|20)\d\d$', year):
            self.search_year = params['year'] = year
        elif self.search_year:
            params['year'] = self.search_year

        if category:
            category = category[0:1].lower()
            category = TmdbTool.categories.get(category, None)
            self.search_cat = None
        if category:
            self.search_cat = category
        if self.search_cat == 'series':
            cmd = 'search/tv'
        elif self.search_cat == 'movie':
            cmd = 'search/movie'
        else:
            cmd = 'search/multi'

        content = self.tmdb_request(cmd, params)

        if content:
            # tb.info(yaml_dump(content))
            self.matches = []
            for result in content['results']:
                if result.get('media_type', 'tv') not in ('movie', 'tv'):
                    # multi may return junk; no media type in others
                    continue
                ns = self.tmdb_make_namespace(self.search_cat, result)
                tmdb_id = result['id']
                subcmd = f'tv/{tmdb_id}' if ns.Type == 'series' else f'movie/{tmdb_id}'
                subparams = {'api_key': str(self.tmdb_apikey),
                        'append_to_response': 'external_ids'}
                content = self.tmdb_request(subcmd, subparams)
                if content:
                    if 'imdb_id' in content:
                        ns.imdbID = content['imdb_id']
                    elif 'external_ids' in content and 'imdb_id' in content['external_ids']:
                        ns.imdbID = content['external_ids']['imdb_id']
                    else:
                        yaml_dump(content, indent=8)
                        lg.err(f'Cannot find IMDB ID for tmdb_id={tmdb_id}', yaml_str(content))

                    if ns.imdbID is not None:
                        # lg.info('RESOLVED IMDB ID:\n' + yaml_str(ns, indent=0))
                        self.matches.append(ns)

        return self.matches

    def toggle_search_primitive(self, phrase, year=None, category=None):
        """TBD"""
        if not year and not category: # seriously, no idea? ... then figure it out
            was_movie_search = bool(self.search_cat and self.search_cat == "movie")
            parsed = VideoParser(phrase, expect_episode=bool(not was_movie_search))
            lg.info('was_movie:', was_movie_search, 'parsed:', vars(parsed))
            category = ('series' if parsed.is_tv_episode() else
                    'movie' if parsed.is_movie_year() else None)
            year = parsed.year
            year = None if year in (1900, 2099) else year
            phrase = parsed.title

        return self.tmdb_search_primitive(phrase, year=year, category=category)


    def search_again(self, phrase):
        """Search again with presumable another phrase but other params
        inherited from original search. If it fails catastrophically,
        the last successful state/result is restored.
        """
        o_state = self.matches, self.status_code, self.search_phrase, self.winner
        self.status_code = 0
        try:
            self.toggle_search_primitive(phrase)
        except Exception as exc:
            lg.err(f're-search("{phrase}") failed [{exc}]')
            lg.pr(traceback.format_exc())

        if self.status_code != 200:
            lg.info(f'restoring previous result: status_code={self.status_code}')
            self.matches, self.status_code, self.search_phrase, self.winner = o_state
        return self.matches

    def show_matches(self, choice=-1, leader=''):
        """Show the current matches from the last online search or from the cache."""
        try:
            if not self.matches:
                if self.cached_omdbinfo:
                    self.matches = [self.cached_omdbinfo]
                if not self.matches:
                    self.matches = []
                    print(f'{leader} NO matches')
                    return
            # eliminate dups
            ids = set()
            for idx in range(len(self.matches)-1, -1, -1):
                match = self.matches[idx]
                # print(f'match={match}')
                if match.imdbID in ids:
                    self.matches.pop(idx)
                else:
                    ids.add(match.imdbID)

            cur_imdbID = self.cached_omdbinfo.imdbID if self.cached_omdbinfo else 'n/a'
            for idx, match in enumerate(self.matches):
                if choice < 0 or idx == choice:
                    cur_indicator = ''
                    if cur_imdbID:
                        cur_indicator = ' *' if cur_imdbID == match.imdbID else '  '
                    pref = f'{leader}{idx+1}:{cur_indicator} '
                    print(self.info_str(match, indent=pref, w_overview=True, max_lines=2))
        except Exception:
            lg.err("Caught exception running show_matches(), so exiting ...")
            lg.pr(traceback.format_exc())
            sys.exit(15)

    def search_interactively(self, phrase=None, year=None, category=None, indent=0):
        """Prompt user to pick the best match for the video."""
        leader = ' ' * indent
        lg.tr5('search_interactively', 'phr:', phrase, 'y:', year, 'cat:', category)
        if phrase:
            self.toggle_search_primitive(phrase=phrase, year=year, category=category)
            if category == 'series':
                phrase += ' 1x1'
            elif year:
                phrase += f'({year})'
            readline.add_history(phrase + '?')
        choice = -1
        major_prompt = True
        while (choice < 0 or choice > len(self.matches)):
            try:
                if major_prompt:
                    which = 'TMDb'
                    if self.search_phrase:
                        print(f'\n{leader}>>> {which} Search Results for "{self.search_phrase}"'
                                + (f' ({self.search_year})' if self.search_year else '')
                                + (f' [{self.search_cat}]' if self.search_cat else '')
                                + ': ')
                    elif self.matches:
                        print(f'\n{leader}>>> Current {which} matches:')
                    elif self.cached_omdbinfo:
                        print(f'\n{leader}>>> Cached {which} Info: ')
                    else:
                        print(f'\n{leader}>>> Empty {which} Info: ')
                    self.show_matches(leader=leader)
                    print(f'{leader}\033[91m[0]\033[0m Cancel search')
                    major_prompt = False
                choice = input(f'\n{leader}>> Enter (0-{len(self.matches)})'
                        ' -OR- <New-Search-Phrase>?: ')
                print('------------> choice=', choice)

                choice = choice.strip().lower()
                if choice.startswith('?') or choice.endswith('?'):
                    choice = choice[1:] if choice.startswith('?') else choice[:-1]
                    choice = choice.strip()
                    if choice:
                        self.search_again(phrase=choice)
                        choice = -1 # force another loop
                        major_prompt = True
                        continue
                choice = int(choice)
            except KeyboardInterrupt:
                print('Keyboard Interrupt ... exiting')
                sys.exit(15)
            except Exception as exc:
                print(f'ERROR: Expecting integer [{exc}]')
                choice = -1

        # Return the result
        choice -= 1
        if choice < 0:
            print("Cancelling selection...")
        else:
            self.winner = self.matches[choice]
            print(f'\nNOTE: Selected: {self.info_str(self.matches[choice])}')
        return choice


def runner(argv):
    """
    TMDbTool.py [H]: tool to access TMDb to fetch, primarily, the IMDb ID,
    but also gets the synopsis and other info.  Normally, use impicitly
    via 'subshop', but can be used to specifically set/repair the IMDb info
    (normally, use -i/--interactive for corrections .. w/o, it will set
    the most likely choice per TMDb.
    """
    from LibSub.SubCache import SubCache
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-T', '--tmdb-apikey',
            help='manually set your TMDb API Key')
    parser.add_argument('-i', '--interactive', action='store_true',
            help='pick best match [else 1st is chosen automatically]')
    parser.add_argument('--testing', action='store_true',
            help='do search-and-compare')
    parser.add_argument('-V', '--log-level', choices=lg.choices,
        default='INFO', help='set logging/verbosity level [dflt=ERROR]')
    parser.add_argument('terms', nargs='+', help='search terms OR files')
    args = parser.parse_args(argv)
    lg.setup(level=args.log_level)

    TmdbTool.override(tmdb_apikey=args.tmdb_apikey)

    tool = TmdbTool()

    dones = set()
    for video in VideoFinder(args.terms):
        basename = os.path.basename(video)
        cache = SubCache(video)
        if cache.omdb_dpath in dones:
            continue
        dones.add(cache.omdb_dpath)
        lg.pr(f'\n=====> {basename} IN {os.path.dirname(video)}')
        info = cache.get_omdbinfo(omdbtool=tool)
        if args.interactive:
            choice = tool.search_interactively()
            if 0 <= choice < len(tool.matches):
                tool.commit_to_cache(tool.matches[choice])
        elif args.testing:
            test_info = tool.search_by_videopath(video, cache.is_tvdir)
            if not test_info:
                lg.pr(' FAILED LOOKUP')
            elif test_info.imdbID == info.imdbID:
                lg.pr(' SAME imdbID:', info.imdbID)
            else:
                lg.pr(' DIFFERENT imdbID:\n',
                    tool.info_str(info, w_overview=True, max_lines=1, indent=3) + '\n',
                    tool.info_str(test_info, w_overview=True, max_lines=1, indent=3))

        else:
            info_str = tool.info_str(info, w_overview=True, max_lines=2, indent=3)
            lg.pr(f'{basename}:\n{info_str}')
