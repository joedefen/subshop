#!/bin/env python3
# -*- coding: utf-8 -*-
"""
Wrapper for getting certain info from Plex using plexapi.
 - plex.tv/users/account
 - to get token
"""
# pylint: disable=invalid-name,broad-except,import-outside-toplevel)

import os
from plexapi.server import PlexServer
from LibGen.CustLogger import CustLogger as lg, parse_mixed_args
from LibSub import ConfigSubshop


class PlexQuery:
    """Wrapper for plexapi."""
    params = ConfigSubshop.get_params()

    def __init__(self, url=None, token=None):
        self.plex = None
        words = self.params.credentials.plex_url_token.split()
        url = words[0] if not url and len(words) == 2 else url
        token = words[1] if not token and len(words) == 2 else token

        if len(words) == 2:
            self.plex = PlexServer(baseurl=url, token=token, timeout=10)

        self.prefix_trim, self.prefix_add = '', ''
        words = self.params.plex_query_params.plex_path_adj.split()
        for word in words:
            if word.startswith('-'):
                self.prefix_trim = word[1:]
            elif word.startswith('+'):
                self.prefix_add = word[1:]

    def get_locations(self, phrase, tv=False, movie=False, limit=20):
        """Returns the video file() for movies and folder for shows."""
        if not tv and not movie:
            mtypes = ('show', 'movie')
        elif tv:
            mtypes = ('show',)
        else:
            mtypes = ('movie',)

        tvshows, movies = [], []
        for mtype in mtypes:
            for video in self.plex.search(phrase, mediatype=mtype, limit=limit):
                for location in video.locations:
                    if self.prefix_trim and location.startswith(self.prefix_trim):
                        location = location[len(self.prefix_trim):]
                    if self.prefix_add:
                        location = self.prefix_add + location

                    if os.path.isfile(location):
                        movies.append(location)
                    elif os.path.isdir(location):
                        tvshows.append(location)
                    elif self.params.plex_query_params.warn_if_nonexistent:
                        print(f'warning: plex returned nonexistent "{location}"')
                # from YamlDump import yaml_str
                # lg.info(yaml_str(video))
                # lg.info(video.guid)  # later? put guid in companion map/list/whatever
        return tvshows, movies

def runner(argv):
    """
    PlexQuery.py: runner() tests either searches or does reverse
    lookups on the targets to see if they would be found.
    """
    import argparse
    from LibSub.VideoParser import VideoFinder
    from LibSub.SubCache import SubCache
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url', help='manually set your Plex URL')
    parser.add_argument('-t', '--token', help='manually set your Plex Token')
    parser.add_argument('-V', '--log-level', choices=lg.choices,
        default='INFO', help='set logging/verbosity level [dflt=ERROR]')
    parser.add_argument('-o', '--only', default=None, choices=('tv', 'movie'),
            help='select only for videos under tv or movie roots')
    parser.add_argument('-r', '--reverse-lookup',
            action="store_true",  help='profile files / foldes or "ALL"')
    parser.add_argument('terms', nargs='+',
            help='search terms for show/movie')
    opts = parse_mixed_args(parser, argv)
    lg.setup(level=opts.log_level)

    tool = PlexQuery(url=opts.url, token=opts.token)
    if not opts.reverse_lookup:
        phrase = ' '.join(opts.terms)
        # lg.info(phrase)
        shows, movies = tool.get_locations(phrase, tv=bool(opts.only=='tv'),
                movie=bool(opts.only=='movie'))
        if shows:
            lg.pr('SHOWS:\n   ' + '\n   '.join(shows))
        if movies:
            lg.pr('MOVIES:\n   ' + '\n   '.join(movies))
    else:
        dones = set()
        found_cnt, not_found_cnt = 0, 0
        terms = [] if opts.terms == ['ALL'] else opts.terms
        for video in VideoFinder(terms):
            cache = SubCache(video)
            omdbinfopath = cache.get_omdbinfopath()
            if omdbinfopath in dones:
                continue
            dones.add(omdbinfopath)
            phrase = cache.parsed.title
            # if cache.parsed.year:
                # phrase += f' {cache.parsed.year}'

            shows, movies = tool.get_locations(phrase, tv=bool(opts.only=='tv'),
                    movie=bool(opts.only=='movie'))
            found = False
            if movies and video in movies:
                # print('MOVIE:',  video)
                found = True
            elif shows:
                for show in shows:
                    if os.path.commonpath([show, video]) == show:
                        # print('TV:' + '\n   '.join(shows))
                        found = True
                        break
            if found:
                found_cnt += 1
            else:
                not_found_cnt += 1
                print('NOT FOUND:', phrase, '\n   ', video)
        print('found:', found_cnt, 'not_found:', not_found_cnt)
