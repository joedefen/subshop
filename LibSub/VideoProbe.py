#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Get probed video info from cache or probing with 'ffprobe' command.
  - ffprobe is pretty "slow" (takes a second) and that is a lot
    for some higher level takes that, say, need to know whether there
    are interal subs.
  - the cache location is set from a higher level (i.e., SubCache),
    and, in fact, this is normally called via SubCache.

"""
# pylint: disable=broad-except,import-outside-toplevel
# pylint: disable=consider-using-f-string
import os
from types import SimpleNamespace
from ruamel.yaml import YAML
from LibGen.CustLogger import CustLogger as lg
from LibSub import ConfigSubshop

yaml = YAML()
yaml.default_flow_style = False

class VideoProbe:
    """TBD"""
    params = ConfigSubshop.get_params()

    def __init__(self, subcache, refresh=False, persist=True):
        """
        Probe the video file; on success, return an object with:
            - subt_streams - [] (e.g., {'eng': '0:2'})
            - audio_streams - [] (e.g., {'eng': '0:1'})
            - duration - float (e.g., 45.7)
            - height - integer (e.g, 640)
            - mod_time - float mod time of videofile (cause refresh if does not match video)
        """
        self.subt_streams = None
        self.audio_streams = None
        self.duration = None
        self.height = None
        self.mod_time = None
        self._subcache = subcache
        # self.videopath = os.path.abspath(videopath)
        # self.cachepath = os.path.abspath(cachepath)
        self.persist = persist
        self.probe(refresh=refresh)

    def _reset(self):
        self.subt_streams = None
        self.audio_streams = None
        self.duration = None
        self.height = None
        self.mod_time = None

    def probe(self, refresh=False):
        """TBD"""
        videopath = self._subcache.get_videopath()
        if not os.path.isfile(videopath):
            raise ValueError('not a file: {}'.format(videopath))

        info = None if refresh or self.mod_time is None else self

        if not info and not refresh:
            info = self._from_cache()
            if info:
                lg.tr1('cached probe_info:', vars(info))

        if not info:
            info = self.probe_primitive(videopath)
            lg.tr8('probed raw_info:', vars(info))
            if self.persist:
                self._to_cache(info)
        self._sanitize(info)

    def get_subt_stream(self, lang3=None):
        """Get internal subs stream of the desired language."""
        return self.subt_streams.get(lang3 if lang3 else self.params.my_lang3, None)

    def get_audio_stream(self, lang3=None):
        """Get the audio track stream of the desired language."""
        return self.audio_streams.get(lang3 if lang3 else self.params.my_lang3,
                self.audio_streams.get('und', None))

    def to_str(self, lang3=None):
        """Returns Concise string representation of the probe info."""
        lang3 = lang3 if lang3 else self.params.my_lang3
        rep = f'{"SUBS" if self.get_subt_stream(lang3) else "subs"}'
        rep += f'={self.subt_streams}'
        rep += ' '
        rep += f'{"AUDIO" if self.get_audio_stream(lang3) else "audio"}'
        rep += f'={self.audio_streams}'
        rep += f' dur={self.duration}s'
        rep += f' hgt={self.height}'
        return rep

    def _sanitize(self, raw_info):
        """Return a version for external consumption"""
        duration = raw_info.duration
        self.duration = round(duration, 3) if isinstance(duration, float) else 0.0
        self.mod_time = raw_info.mod_time if isinstance(raw_info.mod_time, float) else 0.0
        subs = raw_info.subt_streams
        self.subt_streams = dict(subs) if isinstance(subs, dict) else {}
        tracks = raw_info.audio_streams
        self.audio_streams = dict(tracks) if isinstance(tracks, dict) else {}
        height = raw_info.height
        self.height = height if isinstance(height, int) else 1

    def _from_cache(self):
        # pylint: disable=too-many-boolean-expressions
        try:
            with open(self._subcache.get_probeinfopath(), "r", encoding='utf-8') as fh:
                info = yaml.load(fh)
        except Exception as exc:
            lg.tr8('cannot open/load:', self._subcache.get_probeinfopath(), exc)
            return None
        lg.tr8('VideoProbe: cached info:', info)
        if not isinstance(info, dict):
            return None
        expected_keys = {'audio_streams', 'subt_streams', 'duration', 'mod_time', 'height'}
        info_keys = set(info.keys())
        if expected_keys != info_keys: # NOTE: could check for types too
            return None
        info = SimpleNamespace(**info)
        if info.mod_time != os.path.getmtime(self._subcache.get_videopath()):
            return None
        return info

    def _to_cache(self, info):
        """Overwrite the cache file with an updated version."""
        folder = os.path.dirname(self._subcache.get_probeinfopath())
        if not os.path.isdir(folder):
            os.makedirs(folder)
        info = {'subt_streams': info.subt_streams,
                'audio_streams': info.audio_streams,
                'duration': info.duration,
                'height': info.height,
                'mod_time': info.mod_time}

        with open(self._subcache.get_probeinfopath(), "w", encoding='utf-8') as fh:
            yaml.dump(info, fh)


    @staticmethod
    def probe_primitive(path):
        """Use roll-my-own parser. PyProbe drops some key info
        including whether subtitle is forced.  Arrrgh.
        """
        # pylint: disable=too-many-nested-blocks
        lg.tr8('probe:', path)
        import subprocess
        import json
        info = SimpleNamespace(**{'duration': None, 'subt_streams': None,
            'audio_streams': None, 'height': None, 'mod_time': None})
        info.mod_time = os.path.getmtime(path)

        try:
            output = subprocess.run([
                'ffprobe',
                '-hide_banner',
                '-loglevel', 'fatal',
                '-show_error',
                '-show_streams',
                '-show_format',
                '-print_format', 'json',
                path
                ], check=False, stdout=subprocess.PIPE).stdout.decode('utf-8').casefold()
            # note: casefold() is called to ensure lowercase for keys, and we don't
            # use any values where case matters; otherwise this may fail
            # do to, say 'LANGUAGE' being a key where 'language' is expected.
            lg.tr4('ffprobe output:\n', output)
            obj = json.loads(output)
            # from YamlDump import yaml_str
            # lg.tr4('ffprobe output:\n', yaml_str(obj)) # expensive
            if 'error' in obj:
                lg.db('FAILED: probe of ', path, '[', 'ffprobeCmdFailed',
                        obj['error']['string'], ']')
                return info

            duration = obj['format']['duration']
            lg.tr2('duration:', type(duration), duration)
            try:
                info.duration = float(duration)
            except Exception:
                info.duration = 0.0

            info.height = 1
            info.subt_streams = {}
            info.audio_streams = {}

            for stream in obj['streams']:
                # pylint: disable=too-many-boolean-expressions
                if 'codec_type' in stream:
                    str_idx = stream['index']
                    # str_id = f'{str_no}:{str_idx}'
                    str_id = f'0:{str_idx}' # not sure when not 0????`
                    if stream['codec_type'] == 'video':
                        if 'height' in stream:
                            lg.tr2('video stream:', 'height:', stream['height'])
                            info.height = max(info.height, int(stream['height']))
                    if 'tags' in stream and 'language' in stream['tags']:
                        lang = stream['tags']['language']
                    else:
                        lang = 'eng'

                    if stream['codec_type'] == 'audio':
                        lg.tr2('audio:', str(stream))
                        info.audio_streams[lang] = str_id

                    elif stream['codec_type'] == 'subtitle':
                        lg.tr2('subtitle_stream:', str(stream))
                        if 'disposition' in stream and 'forced' in stream['disposition']:
                            if not stream['disposition']['forced']:
                                info.subt_streams[lang] = str_id # explicitly not 'forced'
                        else:
                            info.subt_streams[lang] = str_id  # not quite sure if 'forced'
            return info

        except Exception as exc:
            lg.db('FAILED: probe of ', path, '\n', type(exc).__name__, exc)
            return info

def runner(argv):
    """
    VideoProbe.py [H] - implements interpretation/digestion of ffprobe information.
    Its runner() expands its role a bit:
        - dumps the probe of the videos in its {targets} and their quirks
        - with --I/--set-ignore:  sets the IGNORE quirk for every video
        - with --C/--clear-ignore:  clears the IGNORE quirk for every video
    In dump mode, similar to 'subshop stat' but more detailed by default.
    """
    import argparse
    from LibSub.SubCache import SubCache
    from LibSub.VideoParser import VideoFinder
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--force-refresh', action='store_true',
            help='force probe file file and refresh cache')
    parser.add_argument('-I', '--set-ignore', action='store_true',
            help='set the ignore quirk')
    parser.add_argument('-C', '--clear-ignore', action='store_true',
            help='clear IGNORE quirks if set')
    parser.add_argument('-V', '--log-level', choices=lg.choices,
        default='INFO', help='set logging/verbosity level [dflt=INFO]')
    parser.add_argument('targets', nargs='*', help='{videoFileOrFolder}..')
    args = parser.parse_args(argv)
    lg.setup(level=args.log_level)

    for video in VideoFinder(args.targets):
        subcache = SubCache(video)

        # info = VideoProbe(subcache=subcache, refresh=args.force_refresh)
        info = subcache.get_probeinfo(refresh=args.force_refresh)
        quirk = subcache.get_quirk()
        if args.set_ignore:
            if subcache.quirk_trumps(SubCache.IGNORE):
                subcache.force_set_quirk(SubCache.IGNORE)
                quirk = subcache.get_quirk()
        elif args.clear_ignore:
            if quirk in (SubCache.IGNORE):
                subcache.clear_quirks()
                quirk = subcache.get_quirk()
        quirk_str = subcache.get_quirk_str()

        lg.pr(f'{os.path.basename(video)}:\n        {info.to_str()}'
                + (f' quirk={quirk_str}' if quirk_str else ''))
        # from YamlDump import yaml_str
        # lg.pr(yaml_str(vars(info))
        # lg.pr(vars(info), os.path.basename(video))
        # lg.pr('duration:', type(info.duration), info.duration)
