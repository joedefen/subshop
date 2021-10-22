#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Loader/tester for subshop.yaml configuration file."""
# pylint: disable=broad-except

import sys
from LibGen.YamlConfig import YamlConfig
from LibGen.CustLogger import CustLogger as lg
import LibSub.SubShopDirs as ssd

SUBSHOP_TEMPLATE=r'''
!!omap
# ---- Subtitle download / handling options
- my_lang2: en   # two char language preference (only 'en' actually supported)
- my_lang3: eng  # three char language preference (only 'eng' actually supported)
- tv-root-dirs:  # all installed tv episodes expected any level below these absolute paths
  - /YOUR-TV-ROOTDIRS
- movie-root-dirs:  # all installed movies expected any level below these absolute paths
  - /YOUR-MOVIE-ROOTDIRS
- credentials: !!omap # various credentials
  - omdb-apikey: YOUR-OMDB-APIKEY # from omdbapi.com (1000/day free)
  - imdb-apikey: YOUR-OMDB-APIKEY # from imdb-api.com (100/day free)
  - tmdb-apikey: YOUR-TMDB-APIKEY # from tmdb-api.com
  - opensubtitles-org-usr-pwd: YOUR-USER YOUR-PASSWD # from opensubtitles.org (200down/day free)
  - plex-url-token: YOUR-PLEX-URL YOUR-PLEX-TOKEN # if empty string, plex is not enabled
- image-viewer: YOUR-IMAGE-VIEWER-COMMAND # use '{}' to place image path; else appended
- srt-auto-download: true # if no SRTs, fetch when video installed if true TODO: move/remove
- srt-keep-original: false # keep original after ad removal/sync  TODO: purge
- reference-tool: video2srt # autosub or video2srt
- download-params: !!omap
  - max-choices: 32 # shown only top so-many choices
  - imdb-timeout-secs: 10.0 # IMDb/OMDb query timeout in seconds (else hangs 'forever')
  - omdb-timeout-secs: 10.0 # generic movie DB query timeout (just in case)
- subcache-purge-days: !!omap  # based on "access" (or last read) time
  - AUTOSUB: 0 # recommend 0 (keep forever)
  - REFERENCE: 0 # recommend 0 (keep forever)
  - TORRENT: 0 # recommend 0
  - EMBEDDED: 0 # recommend 0
  - linked: 0 # recommend 0 when linked to current subtitle
  - unlinked: 0 # recommend 0 or 180+
- speech-to-text-params: !!omap
  - thread-cnt: 0 # computed if not set positive to roughly 75% of cpu count
- cmd-opts-defaults: !!omap  # subshop command defaults
  - search-using-plex: false # search for videos w plex (if configured)?
  - redos-cache-limit: 4 # auto redos stops when cached subs reaches limit
  - auto-retry-max-days: 30.0 # auto dos/redos max retry interval in days
  - defer-redos-sub-cnt: 3 # begin AUTODEFER redos when this many downloaads
- plex-query-params: !!omap  # PlexApi options
  - plex-path-adj: "" # set -/{prefix} and/or +/{prefix} to make local path
  - warn-if-nonexistent: false # warn for non-existent paths (can be just noise)
- score-params: !!omap
  - scored_names: true # put score in subt names (e.g., foobar.en07.srt)
  - pts_min_penalty: 50     # start penalty for too few points
  - pts_max_penalty: 0      # max penalty for too few pts (1.0s)
- quirk-params: !!omap
  - misfit_A: !!omap  # mediocre fit thresholds
    - max_pts: 50
    - min_stdev: 0.75
  - misfit_B: !!omap  # lousy fit thresholds
    - max_pts: 20
    - min_stdev: 1.0
  - misfit_C: !!omap  # broken fit thresholds
    - max_pts: 10
    - min_stdev: 2.0
- todo-params: !!omap  # to control todo list
  - per_list_limit: 500  # limit on each of the TODO sub-lists (forced to >= 20)
  - min_score:  10      # minimum score for redos
  - max_score:  20      # maximum score for redos
  - vip_days:   30      # how long new video get priority
- sync-params: !!omap  # to control when to try/replace orig subs
  # NOTE: if one of the max-* is met, the orignal is too bad to adjust (or adjust too bad to use)
  - max-dev: 30000 # max allowd stdev (ms)
  - max-offset: 300000 # max allowed offset (ms)
  - max-rate: 15.0 # max allowed rate change (%)
  # NOTE: any one of the min-* must be matched to adjust the original
  - min-deltadev: 100 # min required stdev improvmement (ms)
  - min-deltaoffset: 100 # min required offset improvement (ms)
  - min-rate: 0.10 # min required rate change (%)
  - min-dev: 350 # min required rate change (ms)
  - min-offset: 100 # min required offset (ms)
  - min-ref-pts: 100 # minimum number of points
- phrase-params: !!omap # phrase complexity tuning params
  - min_word_len: 5 # match phrase must have word of this length
  - min_str_len: 8 # match phrase string length must be this long
- rift-params: !!omap # rift (a.k.a., "break") searching tuning params
  - min-pts: 10       # required # pts in break seg
  - pref-pts: 20      # preferred min pts in break seg (if possible)
  - border-div: 6     # "border" fractional part of trial segment
  - max-slope-delta: 0.025  # how much break sections can vary from linear fit
  - max-parallel-delta: 0.02  # how parallel the lines on each side of break must be
  - min-dev-frac: 0.80    # weighted net improvement expected by finding a break
  - max-dev-frac: 1.25    # how much worse dev either break seg can be
  - trial-mins: 12.0       # (nominal) minutes in each trial segment
  - min-trial-segs: 3     # minimum number of trial segments
- ad-params: !!omap  # advertising removal params
  - limit_s: 120 # restricts some regexes to 'limit_s' of start/end
  - limited-regexes: # these are matched only if within 'limit_s' of start/end
    - \.(com|net|org)\b
    - \bair date\b
    - \bArt Subs\b
    - \bcaption
    - \bsubtitle
    - \bTVShow\b
    - \bwww\.
  - global-regexes:  # these match captions unconditionally 
    - \bopensubtitles\b
    - \baddic7ed\b
    - \bsync\b.*\b(fixed|corrected)\b
    - \brate\b.*\bsubtitles\b
    - '\bsubtitles:'
    - \bsubtitles by\b
    - \bsynchronized by\b
    - \bcaption(ing|ed) by\b
- download-score-params: !!omap # weights to choose best matching subtitle
    - hash-match: 40  # if video hash matches
    - imdb-match: 20  # if IMDB ID matches
    - season-episode-match: 30 # if parsed filename season/episode matches
    - year-match: 20 # if parsed filename year matches
    - title-match: 10 # if parsed filename title matches
    - name-match-ceiling: 9 # name score scaled from 0 based on simlilarity
    - hearing-impaired: 2 # if marked hearing impaired
    - duration-ceiling: 40 # duration score scaled from 0 based on closeness
    - lang-pref: 80  # (moot) if multiple langanges, boost for being 1st
'''

class ConfigSubshop(YamlConfig):
    """Class to load config file."""
    def __init__(self, config_dir=None, dry_run=False, auto=True):
        self.config_dir = config_dir if config_dir else ssd.config_d
        super().__init__(filename='subshop.yaml', config_dir=self.config_dir,
                templ_str=SUBSHOP_TEMPLATE, dry_run=dry_run, auto=auto)

config = ConfigSubshop() # config object (use to refresh params)
def get_params():
    """Get a snapshot of the params."""
    return config.params

def runner(argv):
    """
    Standard YamlConfig-based verifier.  Plus, make sure the
    ad removal regex's compile.
    """
    # pylint: disable=import-outside-toplevel
    import re
    ConfigSubshop(auto=False).generic_main(argv)
    # special case: ensure the regex's compile
    for regexes in ('limited-regexes', 'global-regexes'):
        regex_list = getattr(config.params.ad_params, regexes.replace('-', '_'))
        for idx, regex in enumerate(regex_list):
            try:
                re.compile(regex)
            except Exception as exc:
                lg.err(f'cannot compile ad-params.{regexes}[{idx}] ({regex}) [{exc}]')
                # raise exc
                sys.exit(15)
        lg.pr(f'NOTE: ad-params.{regexes}: compiled {len(regex_list)} patterns')
