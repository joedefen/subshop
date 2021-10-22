#!/usr/bin/env python3
"""
Cleanse/shift SRT files.
"""
# pylint: disable=import-outside-toplevel,too-many-instance-attributes,broad-except,no-else-return
# pylint: disable=too-many-lines,invalid-name,too-many-public-methods,too-many-format-args
# pylint: disable=too-many-arguments,too-many-nested-blocks,using-constant-test
# pylint: disable=too-many-boolean-expressions,too-many-branches
# pylint: disable=consider-using-f-string
import argparse
import os
import re
import shutil
import sys
import statistics
import math
import copy
from types import SimpleNamespace

# from io import FileIO as file
from LibGen.CustLogger import CustLogger as lg
from LibSub import ConfigSubshop


debug_str = os.environ.get('SubFixerDB', None)
DEBUG = bool(debug_str and debug_str not in ('0', 'f', 'false'))

DBfillBucket = False
DBdumpBuckets = False
DBdumpLrAns = False

def getch():
    """TBD"""
    import termios
    import tty
    file_descriptor = sys.stdin.fileno()
    settings = termios.tcgetattr(file_descriptor)
    try:
        tty.setraw(file_descriptor)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(file_descriptor, termios.TCSADRAIN, settings)

class Caption:
    """Defines one caption of an SRT file."""
    begin_re_str = r'^(\d+):(\d+):(\d+),(\d+)\s+--\>\s+(\d+):(\d+):(\d+),(\d+)$'
    begin_re_matcher = None

    def __init__(self):
        """The constructor creates an empty caption."""
        self.leader, self.beg_ms, self.end_ms, self.lines = '', None, None, None
        if not Caption.begin_re_matcher:
            Caption.begin_re_matcher = re.compile(Caption.begin_re_str)

    def set(self, beg_s, end_s, text, caplist=None, leader=0):
        """Use to create captions roll-your-own caption list.  E.g.,
            caplist = []
            while ....: Caption.append(beg_s, end_s, text, caplist)

        Arguments:
        - caplist - a list to append the new caption
          - if caplist is given, then 'leader' is set to "1", "2", ...
        - leader is expected to be an integer if given (ignored if caplist is given)
        - text will be split on line separators; empty lines removed

        Returns:
         - the caption object on success
         - None if not given valid text with some non-whitespace chars
        """
        lines, self.lines = text.splitlines(), []
        for line in lines:
            line = line.strip()
            if line:
                self.lines.append(line)
        if not lines:
            self.leader, self.beg_ms, self.end_ms, self.lines = '', None, None, None
            return None # indicates invalid
        self.beg_ms = int(round(beg_s * 1000))
        self.end_ms = int(round(end_s * 1000))
        if isinstance(caplist, list):
            caplist.append(self)
            self.leader = str(len(caplist))
        else:
            self.leader = None if leader is None else str(leader)
        return self

    @staticmethod
    def compose(caplist):
        """Compose string from a list of Captions that represents the guts
        of an srt file."""
        outs = ''
        for idx, caption in enumerate(caplist):
            outs += '\n' if idx else ''
            outs += caption.to_str(idx+1)
        return outs

    @staticmethod
    def write_to_file(out_file, caplist):
        """Write a list of Captions to a file."""
        outs = Caption.compose(caplist)
        with open(out_file, 'w', encoding = 'utf-8', errors='ignore') as out:
            wrcnt = out.write(outs)
            lg.tr5('------> Wrote', wrcnt, 'bytes to', out_file)

    @staticmethod
    def _ms_str(millis, prefix=''):
        """This is for readability"""
        if millis < 0:
            millis = -millis
            prefix = '-'
        hrs = millis // (60*60*1000)
        mins = (millis // (60*1000)) % 60
        secs = (millis // 1000) % 60
        millis = millis % 1000
        rv = ('{:02d}:'.format(hrs) if hrs else ''
              ) + ('{:02d}:'.format(mins) if hrs or mins else ''
                   ) + ('{:02d}.{:03d}'.format(secs, millis))
        return prefix + (rv[1:] if rv.startswith('0') else rv)

    def __repr__(self):
        """Debugging representation for readability. Intended to be concise
        on liner with endtime being relative."""
        return '{}{} {}'.format(self._ms_str(self.beg_ms),
                self._ms_str(self.end_ms-self.beg_ms,'+'), ' '.join(self.lines))

    def delta_str(self, caplist):
        """Representation showing time from beginning or end which
        ever is closer."""
        to_end_ms = self.beg_ms - caplist.captions[-1].end_ms # negative, presumbly
        rel_ms = self.beg_ms if abs(self.beg_ms) < abs(to_end_ms) else to_end_ms
        return f'{self._ms_str(rel_ms)} {" ".join(self.lines)}'

    def to_str(self, idx=None):
        """Formal representation of caption per the specs except
        for the empty line between captions."""
        def ms_str(millis):
            hrs = millis // (60*60*1000)
            mins = (millis // (60*1000)) % 60
            secs = (millis // 1000) % 60
            millis = millis % 1000
            return '{:02d}:{:02d}:{:02d},{:03d}'.format(hrs, mins, secs, millis)

        rv = str(idx) if idx is not None else self.leader
        rv += '\n{} --> {}\n'.format(ms_str(self.beg_ms), ms_str(self.end_ms))
        rv += '\n'.join(self.lines) + '\n'
        return rv

    def mini_str(self, max_wds=7):
        """Abbreviated one-liner of caption debugging .. a very
        terse form w/o endtime and limited # of words.
        """
        def sec_str(millis):
            secs = int(round(millis / 1000))
            hrs = secs // (60*60)
            mins = (secs // 60) % 60
            secs = secs % 60
            return '{}{:02d}:{:02d}'.format(f'{hrs}:' if hrs else '', mins, secs)

        rv = sec_str(self.beg_ms) + ' ' + ' '.join((' '.join(self.lines)).split()[0:max_wds])
        return rv

class CaptionList:
    """TBD"""
    CHARFIXES = {'¶': '♪'}

    REGEX = [#r'\dx',
            r'\.(com|net|org)\b', r'\bsync\b.*\b(fixed|corrected)\b',
             r'\bair date\b', r'\bArt Subs\b', r'\bcaption',
             r'\bHawkeye\d', r'\b[Nn]anban', r'\bsubtitle', r'\bTVShow\b',
             r'\bwww\.', 'âª']

    subshop_params = ConfigSubshop.get_params()
    ad_params = subshop_params.ad_params

    def __init__(self, srt_file):
        """Create a caption list from a open caption file."""
        self.captions = []
        self.anomalies = []
        self.misnum_cnt = 0
        self.code_option_score_lengths = False
        self.purge_ads_cnt = 0
        self.ads = []
        self.fixed_char_cnt = 0
        self.delay_cnt = 0
        self.trans_table = str.maketrans(''.join(CaptionList.CHARFIXES.keys()),
                ''.join(CaptionList.CHARFIXES.values()))
        self.limited_pats = [re.compile(pattern, re.IGNORECASE)
                             for pattern in CaptionList.ad_params.limited_regexes]
        self.global_pats = [re.compile(pattern, re.IGNORECASE)
                             for pattern in CaptionList.ad_params.global_regexes]
#       self.formulas = None # computed formulas
#       self.lri = None # linear regression vs reference

        if isinstance(srt_file, list):
            self.captions = srt_file
            return

        if isinstance(srt_file, str):
            with open(srt_file, 'r', encoding = 'utf-8', errors='ignore') as srt:
                lines = srt.readlines()
        else:
            lines = srt_file.readlines()
        while lines:
            self._get_next(lines)

    def is_updated(self):
        """TBD"""
        return self.anomalies or self.purge_ads_cnt or self.fixed_char_cnt or self.delay_cnt

    def _add_anomaly(self, *terms):
        terms = [str(term) for term in terms]
        self.anomalies.append(' '.join(terms))

    def _fix_chars(self, line):
        fixed = line.translate(self.trans_table)
        self.fixed_char_cnt += 1 if fixed != line else 0
        return fixed

    def _get_next(self, lines):
        """Get next caption from remaining lines.
        - Returns caption if another is found else None
        """
        def to_ms(nums):
            """ms from [hr, min, sec, ms]"""
            return int(nums[3]) + 1000 * (
                    int(nums[2]) + 60 * (int(nums[1]) + 60 * int(nums[0])))

        caption = Caption()
        while lines:
            line = lines.pop(0).strip()
            if caption.beg_ms is None:
                mat = Caption.begin_re_matcher.match(line)
                if mat:
                    caption.beg_ms = to_ms(mat.group(1, 2, 3, 4))
                    caption.end_ms = to_ms(mat.group(5, 6, 7, 8))
                    caption.lines = []
                else:
                    caption.leader = line # last one wins
            else:
                if line:
                    caption.lines.append(self._fix_chars(line))
                elif not caption.lines:
                    self._add_anomaly('empty caption:', str(caption))
                    caption.beg_ms = None # anomally
                else:
                    lg.tr9('caption:', vars(caption))
                    break

        if caption.beg_ms is not None and caption.lines:
            self.captions.append(caption)

    def repair(self, verbose=False, title=None):
        """TBD"""
        deletions = []

        order_errs = 0

        for idx, caption in enumerate(self.captions):
            if not caption:
                continue

            if not re.match(r'\d+$', caption.leader):
                pass # who cares
                # self._add_anomaly('fix malformed leader:', caption.leader, caption)
            elif int(caption.leader) != idx + 1:
                self._add_anomaly('fix misnumbered:', caption.leader, 'not', idx + 1, caption)
                self.misnum_cnt += 1

            if caption.beg_ms < 0:
                if caption.end_ms <= 0:
                    self._add_anomaly('rmv negative offset:', caption)
                    deletions.insert(0, idx)
                else:
                    caption.beg_ms = 0
                    self._add_anomaly('adj negative offset:', caption)
                continue

            n_caption = None
            if idx+1 < len(self.captions):
                n_caption = self.captions[idx+1]
                if caption.beg_ms > n_caption.beg_ms:
                    self._add_anomaly('out-of-order:', caption, '\n   ', n_caption)
                    order_errs += 1

        for deletion in deletions:
            del self.captions[deletion]

        lg.tr2('repair: #captions', len(self.captions))
        if order_errs:
            self.captions = sorted(self.captions, key=lambda x: x.beg_ms)

        # fix overlaps and such in reverse order
        prev_caption = None
        for idx in range(len(self.captions) - 1, -1, -1):
            caption = self.captions[idx]
            n_caption, prev_caption = prev_caption, caption

            if caption.end_ms <= caption.beg_ms:
                if n_caption:
                    next_delta = n_caption.beg_ms - caption.end_ms
                    if next_delta < 200: # so short; force overlap to fix in next block
                        # report as overlap
                        caption.end_ms = n_caption.beg_ms + 1
                    else:
                        self._add_anomaly('fix non positive duration:', caption)
                        caption.end_ms = caption.beg_ms + min(2000, next_delta)
                else:
                    self._add_anomaly('fix non positive duration:', caption)
                    caption.end_ms = caption.beg_ms + 2000 # arbitrary

            if n_caption and caption.end_ms  > n_caption.beg_ms:
                self._add_anomaly('fix caption overlap:', caption, '\n   ', n_caption)
                # try to split fairly
                duration = max(n_caption.end_ms, caption.end_ms) - caption.beg_ms
                tot_lines = len(caption.lines) + len(n_caption.lines)
                duration1 = int(round(duration * len(caption.lines) / tot_lines))
                duration2 = duration - duration1
                caption.end_ms = caption.beg_ms + duration1
                n_caption.beg_ms = caption.end_ms
                n_caption.end_ms = n_caption.beg_ms + duration2

        if self.anomalies:
            if title:
                lg.pr(title)
            lg.pr('------> Fixing', len(self.anomalies), 'anomalies')
            if verbose:
                misnumbered = 0
                for anomaly in self.anomalies:
                    if 'misnumbered' in anomaly:
                        misnumbered += 1
                    else:
                        lg.pr('err:', anomaly)
                if misnumbered:
                    lg.pr('err: AND fixed', misnumbered, 'misnumbered captions')

        for idx, caption in enumerate(self.captions):
            caption.leader = str(idx + 1)


    def detect_ads(self, limit_s=None, use_config_pats=True, pattern=None):
        """TBD"""
        lg.tr5('detect_ads(): limit_s:', limit_s, 'use_config_pats:',
                use_config_pats, 'pattern=', pattern)
        if not self.captions: # avoid exception if no subs
            return
        limit_ms = (self.ad_params.limit_s if limit_s is None else limit_s) * 1000
        save_from_ms = self.captions[0].beg_ms + limit_ms
        save_to_ms = self.captions[-1].end_ms - limit_ms
        for idx, caption in enumerate(self.captions):
            text = '\n'.join(caption.lines) + '\n'
            matched = False
            if use_config_pats and save_from_ms < caption.beg_ms > save_to_ms:
                for pat in self.limited_pats:
                    if pat.search(text):
                        lg.tr1('ad match', text)
                        self.ads.append((pat.pattern, idx))
                        matched = True
                        break
            if use_config_pats and not matched:
                for pat in self.global_pats:
                    if pat.search(text):
                        lg.tr1('ad match', text)
                        self.ads.append((pat.pattern, idx))
                        matched = True
                        break
            if pattern and not matched:
                if pattern.search(text):
                    lg.tr1('ad match', text)
                    self.ads.append((pattern.pattern, idx))

    def purge_ads(self):
        """NOTE: for this to work, all detect_ads() first."""
        if self.ads:
            deletions = [] # must be built in reverse order
            for pair in self.ads:
                _, idx = pair # pair is (regex, idx)
                deletions.insert(0, idx)
            for deletion in deletions:
                del self.captions[deletion]
            self.ads = [] # prevent double purge
            self.purge_ads_cnt += len(deletions)

            for idx, caption in enumerate(self.captions):
                caption.leader = str(idx + 1)

    def delay_subs(self, delay_ms):
        """TBD"""
        deletions = []
        for idx, caption in enumerate(self.captions):
            caption.beg_ms += delay_ms
            caption.end_ms += delay_ms
            if caption.beg_ms < 0:
                if caption.end_ms >= 0:
                    caption.beg_ms = 0
                    self.delay_cnt += 1
                else:
                    self._add_anomaly('lost frame (negative time):', caption)
                    deletions.insert(0, idx)
            else:
                self.delay_cnt += 1

        for deletion in deletions:
            del self.captions[deletion]

    @staticmethod
    def linear_regression(x, y, b_rnd=3, m_rnd=5):
        """Compute linear regression.
        Returns: intercept, slope, goodness-of-fit, description
        """
        # pylint: disable=invalid-name
        N = min(len(x), len(y))
        x_mean = statistics.mean(x) if x else 0
        y_mean = statistics.mean(y) if y else 0

        B1_num, B1_den, xy_sum, xx_sum, x_sum, yy_sum, y_sum = 0, 0, 0, 0, 0, 0, 0
        for idx in range(N):
            X, Y = x[idx], y[idx]
            B1_num += ((X - x_mean) * (Y - y_mean))
            B1_den += ((X - x_mean)**2)
            xy_sum += X*Y
            x_sum += X
            y_sum += Y
            xx_sum += X*X
            yy_sum += Y*Y

        B1 = B1_num / B1_den if B1_den else 0
        B0 = y_mean - (B1*x_mean)

        stdev, squares_sum = 0.0, 0.0
        for idx in range(N):
            X, Y = x[idx], y[idx]
            Ycalc = B1*X + B0
            squares_sum += (Y-Ycalc)**2
        if N:
            stdev = math.sqrt(squares_sum / N)

        num = (N * xy_sum) - (x_sum * y_sum)
        den = math.sqrt((N * xx_sum - x_sum**2) * (N * yy_sum - y_sum**2))
        R = num / den if den > 0 else 1.0


        lri = SimpleNamespace()
        lri.intercept = round(B0, b_rnd)
        lri.slope = round(B1, m_rnd)
        lri.x_left = x[0] if x else 0
        lri.x_right = x[-1] if x else 0
        lri.y_left = round(B0 + B1*lri.x_left, b_rnd)
        lri.y_right = round(B0 + B1*lri.x_right, b_rnd)
        lri.stdev = round(stdev, b_rnd+1)
        lri.R = round(R, 4)
        lri.RR = round(R*R, 4)
        lri.N = N
        lri.squares_sum = squares_sum
        lri.line = f'y = {lri.intercept} + {lri.slope:.5f}*x'

        return lri

    @staticmethod
    def clear_text(cap):
        """Extract clear text from captions."""
        rv = []
        for line in cap.lines:
            if '<' in line: # remove <b> </b> and the like
                line = re.sub(r'<[^>]*>', '', line)
            if r"{"'\\' in line:  # remove {\an8}, {^G6} and the like
                line = re.sub(r'{[^}]*}', '', line)
            line = line.strip()
            if line:
                rv.append(line)
        return rv

    @staticmethod
    def hhmmss_str(seconds):
        """TBD"""
        seconds = int(round(seconds))
        hrs = seconds // 3600
        mins = (seconds // 60) % 60
        secs = seconds % 60
        rv = '{}{:02d}:{:02d}'.format('{}:'.format(hrs) if hrs else '', mins, secs)
        return re.sub(r'^0', r'', rv)

    def compare(self, orig_caplist, video_duration, do_lri=True):
        """Compare "original" captions to these captions.
        Assumes:
            - only time shifts and caption duration shifts are being done
            - the original can have more frames and extras are at beginning
        """
        # pylint: disable=too-many-locals,too-many-branches
        def secs(millis):
            return round(millis/1000, 3)

        def skip_to(o_idx, o_caps, n_cap, limit):
            n_clear_text = self.clear_text(n_cap)
            for idx, o_cap in enumerate(o_caps[o_idx:]):
                if self.clear_text(o_cap) == n_clear_text:
                    return o_idx + idx
                if idx >= limit:
                    return None
            return None

        huge = 1000*1000*1000
        min_offset, max_offset, sum_offset = huge, -huge, 0
        min_delta, max_delta, sum_delta = huge, -huge, 0    # for caption durations

        for caplist in (orig_caplist, self): # normalize the lists
            caplist.detect_ads()
            caplist.purge_ads()

        lg.db('compare():', '#orig_caps:', len(orig_caplist.captions),
                '#caps:', len(self.captions))
        orig_caplist.repair()  # gotta repair the older on for a sane comparison and stats
        o_caps = orig_caplist.captions
        n_caps = self.captions
        lg.tr1('compare(): (after repair)', '#orig_caps:', len(orig_caplist.captions),
                '#caps:', len(self.captions))


        caption_cnt = len(n_caps)
        delta_caption_cnt = len(o_caps) - len(n_caps)
        unfound_caption_cnt = 0
        found_caption_cnt = 0
        removed_where = []

        o_millis, offsets, deltas, oo_caps, nn_caps = [], [], [], [], []
        skip_max = abs(delta_caption_cnt) + 10 # how far ahead to look
        n_idx, o_idx = -1, -1
        while True:
            n_idx, o_idx = n_idx+1, o_idx+1
            if n_idx >= len(n_caps):
                if o_idx < len(o_caps):
                    print('REMOVED {} caps at END:'.format(len(o_caps) - o_idx))
                    removed_where.append('END')
                    while o_idx < len(o_caps):
                        print('  ', o_caps[o_idx])
                        o_idx += 1
                break

            n_cap, o_cap = n_caps[n_idx], o_caps[o_idx]

            lg.tr9('compare(): n_cap', n_cap)
            o_found_idx = skip_to(o_idx, o_caps, n_cap, skip_max)
            if o_found_idx is None:
                unfound_caption_cnt += 1
                o_idx -= 1 # don't advance the old captions
                print('UNFOUND:', n_cap, '\n at ocap:', o_cap)
                continue

            if o_idx < o_found_idx:
                where = 'pos{}/{}'.format(n_idx+1, len(n_caps)) if n_idx else 'START'
                removed_where.append(where)
                print('REMOVED {} caps at {}:'.format(o_found_idx - o_idx, where))
                while o_idx < o_found_idx:
                    print('  ', o_cap)
                    o_idx += 1
                    o_cap = o_caps[o_idx]

            found_caption_cnt += 1
            oo_caps.append(o_cap)
            nn_caps.append(n_cap)
            o_millis.append(o_cap.beg_ms)
            offset = n_cap.beg_ms - o_cap.beg_ms
            offsets.append(offset)
            min_offset = min(min_offset, offset)
            max_offset = max(max_offset, offset)
            sum_offset += offset
            delta = (n_cap.end_ms - n_cap.beg_ms) - (o_cap.end_ms - o_cap.beg_ms)
            deltas.append(delta)
            min_delta = min(min_delta, delta)
            max_delta = max(max_delta, delta)
            sum_delta += delta
            lg.tr8('compare(): offset:', offset, min_offset, max_offset,
                    'delta:', delta, min_delta, max_delta,
                    '\n  ', o_cap, '\n  ', n_cap)

        result = ''
        if do_lri:
            lri = self.linear_regression(o_millis, offsets, b_rnd=0) if offsets else None
            result = self.make_compare_str(lri)

            if offsets:
                if self.code_option_score_lengths:
                    avg_delta = secs(round(statistics.mean(deltas)))
                    range_delta = secs(max(avg_delta - min_delta, max_delta - avg_delta))
                    if abs(avg_delta) >= 0.050 or range_delta >= 0.050:
                        result += ' lengths by: {}s'.format(avg_delta)
                        if range_delta >= 0.050:
                            result += '+-{}'.format(range_delta)
                else:
                    anomaly_cnt = len(self.anomalies) - self.misnum_cnt
                    if orig_caplist:
                        anomaly_cnt += len(orig_caplist.anomalies) - orig_caplist.misnum_cnt
                    if anomaly_cnt:
                        result += ' w {} anomalies'.format(anomaly_cnt)

                    for idx, o_milli in enumerate(o_millis):
                        n_milli = o_milli + offsets[idx] # recompute new milli
                        linear_milli = lri.intercept + (1+lri.slope)*o_milli

                        delta_ms = int(round(n_milli - linear_milli))
                        lg.tr4('intercept:', int(round(lri.intercept)),
                                'slope:', round(lri.slope, 4),
                                'o_ms:', o_milli, 'n_ms:', n_milli,
                                'linear_ms', int(round(linear_milli)),
                                'delta_ms:', delta_ms)

                        if DEBUG:
                            print('offset:', n_milli, 'delta:', delta_ms,
                                    'EXCEPTION' if abs(delta_ms) >= 10 else '',
                                    '\n  o:', oo_caps[idx], '\n  n:', nn_caps[idx])

        if unfound_caption_cnt:
            result += ' w {} unmatched'.format(unfound_caption_cnt)

        if delta_caption_cnt:
            result += ' w {} removed{}'.format(delta_caption_cnt,
                    ' at {}'.format(removed_where[0] if len(removed_where) == 1 else ''))

        video_duration = int(round(video_duration))
        if video_duration and n_caps:
            last_caption_secs = n_caps[-1].end_ms / 1000
            delta = int(round(video_duration - last_caption_secs)) # how much longer is video?

            if delta < 0:
                late_captions = [ cap for cap in n_caps if cap.end_ms/1000 > video_duration]
                print('{} CAPTIONS BEYOND VIDEO END at {}:'.format(len(late_captions),
                    self.hhmmss_str(video_duration)))
                for cap in late_captions:
                    print('  ', cap)

            lg.tr2('compare(): delta:', delta, last_caption_secs, video_duration)
            if delta < -5:
                result += ' short by {}s'.format(-delta)

            if delta > 180:
                result += ' long by {}s'.format(delta)

        result += ' of {} captions'.format(caption_cnt)
        if self.purge_ads_cnt:  # won't find any
            result += ' -{} ads'.format(self.purge_ads_cnt)
        return result

    @staticmethod
    def make_compare_str(lri):
        """TBD"""
        result = ''
        if lri:
            lg.tr1('make_compare_str(): regression:', vars(lri))
            stdev = round(lri.stdev/1000, 2) # stdev in seconds
            result += ' dev {:0.2f}s'.format(stdev)

            intercept_s = round(lri.intercept/1000, 1) # intercept_s in seconds
            if intercept_s >= 0.1:
                result += f' shift {intercept_s}s'
            slope_pct = round(lri.slope*100, 2)  # slope_pct in percent
            if abs(slope_pct) >= .01:
                result += f' rate {slope_pct:0.2f}%'
            # fit = round(fit*100, 2)  # fit now in percent
            # if fit < 99.995:
                # result += ' fit {:0.2f}%'.format(fit)

            result += f' pts {lri.N}'

        return result




class CaptionListAnalyzer(CaptionList):
    """This class enables comparing a CaptionList to a "Reference"
    CaptionList (e.g., derived from speed-to-text automatically).

    Normally, just call analyze() is called with the reference CapList.
    """
    def __init__(self, srt_file):
        super().__init__(srt_file)
        self.xmcaps = None      # list of matched caption objects
        self.lri = None         # linear regression of whole
        self.formulas = None    # formulas for correction to reference
        self.point_cnt = 0      # should match len(self.xmcaps)
        self.far_out_point_cnt = 0      # points with timing too dubious to use
        self.verbosity = 0

    def analyze(self, ref_caplist, video_duration, out_file=None,
            verbosity=0, fallback_caplist=None):
        """Compare "reference" captions (conventionally with suffix .REF.srt) to these
        captions PHRASE by PHRASE.  How we do this:
        - extract the "phrases" from the reference and studied subtitles
          all the time of the reference subtitles
        """
        def is_better(lri, nlri, min_deltadev=None):
            if min_deltadev is None:
                min_deltadev = lims.min_deltadev
            if not lri:
                return True
            if not nlri:
                return False
            lg.tr8('is_better(): deltadev:', lri.stdev - nlri.stdev, min_deltadev)
            lg.tr8('is_better(): deltaoffset:',
                    abs(nlri.intercept) - abs(lri.intercept),
                    lims.min_deltaoffset)

            return bool(lri.stdev - nlri.stdev >= min_deltadev or
                    abs(lri.intercept) - abs(nlri.intercept)
                    >= lims.min_deltaoffset)

        lims = self.subshop_params.sync_params
        # pylint: disable=too-many-locals,too-many-branches
        if out_file:
            assert isinstance(out_file, str)
        new_caplist = None
        best_caplist, alt_caplist = self, None
        decision = 'KEEP unadjusted subs'
        devs = [-1, -1, -1]  # for unadjusted, linear adj, rift adj

        whynot = self.best_linear_fit(ref_caplist, 'unadjusted', verbosity)
        best_lri = self.lri
        devs[0] = int(round(best_lri.stdev)) if best_lri else 100000

        if self.formulas and len(self.xmcaps) >= lims.min_ref_pts and (
                abs(best_lri.intercept) >= lims.min_offset
                    or abs(best_lri.slope*100) >= lims.min_rate):
            lg.pr('     <<<< Doing linear adjustment ... >>>>')
            alt_caplist = CaptionListAnalyzer(copy.deepcopy(self.captions))
            alt_caplist.replicate_xmcaps(self.xmcaps)
            alt_caplist.adjust_by_formulas(self.formulas)
            lg.tr3('whynot:', whynot, '#formulas:', len(alt_caplist.formulas)
                    if alt_caplist.formulas else None)
            whynot = alt_caplist.best_rifts_fit(ref_caplist,
                    'linear-adjusted', verbosity)
            lg.tr3('whynot:', whynot, '#formulas:', len(alt_caplist.formulas))
            devs[1] = int(round(alt_caplist.lri.stdev)) if alt_caplist.lri else 100000
            if is_better(best_lri, alt_caplist.lri, min_deltadev=20):
                best_caplist, best_lri = alt_caplist, alt_caplist.lri
                decision = 'PICK linear adjusted subs'
            lg.tr2('#formulas:', len(alt_caplist.formulas))

        rift_cnt = 0
        if (alt_caplist and len(alt_caplist.formulas) > 1
                and len(best_caplist.xmcaps) >= lims.min_ref_pts
                and (abs(best_lri.intercept) >= lims.min_offset
                    or abs(best_lri.slope*100) >= lims.min_rate
                    or best_lri.stdev >= lims.min_dev)):

            lg.pr('     <<<< Looking for rifts ... >>>>')
            new_caplist = CaptionListAnalyzer(copy.deepcopy(alt_caplist.captions))
            new_caplist.replicate_xmcaps(alt_caplist.xmcaps)
            new_caplist.adjust_by_formulas(alt_caplist.formulas)
            rift_cnt = len(alt_caplist.formulas) -1

            whynot = new_caplist.best_linear_fit(ref_caplist,
                    'rift-adjusted', verbosity)
            if whynot:
                if best_caplist == self:
                    return whynot + ' [ADJUSTED SUBS]'
            else:
                devs[2] = int(round(new_caplist.lri.stdev))
                if is_better(best_lri, new_caplist.lri):
                    best_caplist = new_caplist
                    decision = 'PICK rift adjusted subs'
                elif best_caplist != self:
                    decision = 'PICK linear adjusted subs'
                    best_caplist.formulas = []
                    rift_cnt = 0

        if best_caplist == self:
            decision = 'KEEP unadjusted subs'
        decision += f' {devs[0]}/{devs[1]}/{devs[2]}ms'

        if fallback_caplist:
            lg.pr('     <<<< Analyze fallback subs ... >>>>')
            whynot = fallback_caplist.best_linear_fit(ref_caplist, 'unadjusted',
                    verbosity=-1)
            best_lri, fb_lri = best_caplist.lri, fallback_caplist.lri
            if not is_better(fb_lri, best_lri, min_deltadev=20):
                if fb_lri and best_lri:
                    decision = 'KEEP fallback subs offs:{}/{}ms devs:{}/{}ms [fb/new]'.format(
                            int(fb_lri.intercept), int(best_lri.intercept),
                            int(fb_lri.stdev), int(best_lri.stdev))
                elif fb_lri:
                    decision = 'KEEP fallback subs offs:{}ms devs:{}ms [fb]'.format(
                            int(fb_lri.intercept), int(fb_lri.stdev))
                else:
                    decision = 'KEEP fallback subs'
                best_caplist = fallback_caplist
                rift_cnt = 0

        if out_file:
            lg.pr('=>', decision)
        else:
            decision = f'WOULD {decision}'

        # print('recurse:', recurse, 'outf:', out_filename)
        if best_caplist != fallback_caplist and out_file:
            lg.db('compare(): writing:', out_file)
            with open(out_file, 'w', encoding = 'utf-8', errors='ignore') as out:
                outs = ''
                for idx, caption in enumerate(best_caplist.captions):
                    outs += '\n' if idx else ''
                    outs += caption.to_str(idx+1)
                wrcnt = out.write(outs)
                # updated = True
                lg.tr5('------> Wrote', wrcnt, 'bytes to', out_file)


        result = best_caplist.make_resultstr(
                None if best_caplist == fallback_caplist else self,
                video_duration, rift_cnt)

        rv = f'OK {result} [{decision}]'
        # lg.pr('rv:', rv)
        return rv

    def make_resultstr(self, src_caplist, video_duration, rift_cnt):
        """TBD"""
        result = self.make_compare_str(self.lri)

        anomaly_cnt = len(self.anomalies)
        if src_caplist and self != src_caplist:
            anomaly_cnt += len(src_caplist.anomalies)

        if anomaly_cnt > 0:
            result += f' w {anomaly_cnt} anomalies'

        if rift_cnt > 0:
            result += f' w {rift_cnt} rifts'

        return result

    def best_linear_fit(self, ref_caplist, phase, verbosity=0):
        """Core analysis."""

        self.lri, self.formulas = None, []

        for caplist in (ref_caplist, self): # normalize the caption lists (e.g., remove ads)
            caplist.detect_ads()
            caplist.purge_ads()
            caplist.repair(verbose=True,
                    title=f'=> Audit {phase if caplist == self else "reference"} subs')

        xvals, yvals = self.make_xygrid(ref_caplist, verbosity)
        if xvals and yvals:
            lri = self.lri = self.linear_regression(xvals, yvals, b_rnd=0)
            if verbosity >= 0:
                self.print_lri(lri, prefix=f'=> Linear fit of {phase} to REF:')
        else:
            lri = None

        lims = self.subshop_params.sync_params
        lg.tr1('lims:', vars(lims))
        whynot = None
        if not lri:
            whynot = f'cannot compute linear regression [pts={len(self.xmcaps)}]'
        elif abs(lri.slope*100) > lims.max_rate:
            whynot = f'rate-too-big(abs ({lri.slope*100})>{lims.max_rate})'
        elif abs(lri.intercept) > lims.max_offset:
            whynot = f'offset-too-big (abs({lri.intercept})>{lims.max_offset})'
        elif lri.stdev > lims.max_dev:
            whynot = f'dev-too-big ({lri.stdev}>{lims.max_dev})'
        elif self.point_cnt < 100:
            whynot = f'two-few-points({self.point_cnt}<{lims.min_ref_pts})'
        if whynot:   # too bad to try
            return f'FAILED: analysis [{whynot}]'

        if whynot:
            return whynot  # too awful to try adjustment

        self._add_formula(0, len(xvals), self.lri)
        return whynot

    def _add_formula(self, xbot, xtop, lri):
        ns = SimpleNamespace(**{'xbot': xbot, 'xtop': xtop, 'lri': lri})
        lg.tr5('add formula:', vars(ns))
        self.formulas.append(ns)


    def best_rifts_fit(self, ref_caplist, phase, verbosity=0):
        """Find the best fit using rifts (i.e., multiple linear fits)."""
        whynot = self.best_linear_fit(ref_caplist, phase, verbosity)
        if whynot:
            return whynot
        self.formulas = []
        self.find_breaks(nominal_slope=self.lri.slope)
        return None


    def make_xygrid(self, ref_caplist, verbosity):
        """
        Verbosity: 1=lots, 0=little, -1=minimal
        """
        xwords = self.make_wordlist()
        ywords = self.make_wordlist(ref_caplist)

        xwords_keys = self.make_phrase_keys(xwords)

        self.correlate_xy(ywords, xwords_keys, xwords, verbosity)

        self.purge_outliers()
        if verbosity > 0:
            if self.xmcaps:
                self.dump_xmcaps()
            else:
                lg.pr('WARNING: NO MATCHED CAPS')

        xvals, yvals = self.make_xyvals()
        return xvals, yvals


    def make_wordlist(self, ref_caplist=None):
        """TBD"""
        if ref_caplist:
            captions = ref_caplist.captions
        else:
            captions = self.captions
            self.init_xmcaps() # sparse ... one-to-one with captions

        words = []
        max_word_ms = int(round((1000*60/100))) # 100 w/min min rate
        min_word_ms = int(round((1000*60/160))) # 160 w/min max rate
        fudge = 2  # how far out-of-expection the caption lenght can be

        # pylint: disable=too-many-nested-blocks
        for capno, caption in enumerate(captions):
        # for mcap in self.xmcaps:
            mcap = None if ref_caplist else self.xmcaps[capno]
            lg.tr8('make_wordlist(): caption:', caption)
            raw_words, cooked_words = ' '.join(self.clear_text(caption)).lower().split(), []
            for idx, word in enumerate(raw_words):
                word = re.sub('^[^a-z]*', '', word)
                word = re.sub('[^a-z]*$', '', word)
                if word:
                    cooked_words.append(word)
            if not cooked_words:
                continue
            ms_per_word = (caption.end_ms - caption.beg_ms) / len(cooked_words)
            if ms_per_word < min_word_ms/fudge or ms_per_word > max_word_ms*2:
                continue
            ms_per_word = min(ms_per_word, max_word_ms)
            ms_per_word = max(ms_per_word, min_word_ms)
            lg.tr9('make_wordlist(): ms_per_word', ms_per_word)
            for idx, cooked_word in enumerate(cooked_words):
                word = SimpleNamespace()
                word.word = cooked_word
                word.mcap = mcap
                word.pos = idx
                word.ms = int(round(caption.beg_ms + idx * ms_per_word))
                words.append(word)

#       if False:
#           print('WORDSET:')
#           for idx, word in enumerate(words):
#               if True or idx < 10 or idx >= len(words) - 10:
#                   print('word:', idx, vars(word))

        return words

    @staticmethod
    def get_phrase_words(words, wordno):
        """TBD"""
        max_phrase_words = 16
        phrase_words = [words[wordno]]
        for idx in range(wordno+1, min(wordno+max_phrase_words, len(words))):
            if words[idx].ms - words[idx-1].ms > 1000:
                break
            phrase_words.append(words[idx])
        return phrase_words

    def make_phrase_keys(self, words):
        """TDB"""
        tune = self.subshop_params.phrase_params
        rv = {}
        for idx in range(len(words)):
            phrase_words = self.get_phrase_words(words, idx)
            for cnt in range(1, len(phrase_words)):
                phrase = ' '.join([w.word for w in phrase_words[0:cnt]])
                max_word_len = max([len(w.word) for w in phrase_words[0:cnt]])
                # - min phrase length is 8
                # - min phrase length is 10 with one 5-letter word
                # - if multiple hits, we 'None' it out to indicate multiple
                # if len(phrase) >= 10 and max_word_len >= 5:
                if len(phrase) >= tune.min_str_len and max_word_len >= tune.min_word_len:
                    wordno = rv.get(phrase, 'unfound')
                    rv[phrase] = idx if isinstance(wordno, str) else None
        if False: # for initial debugging
            ambig_cnt = 0
            for phrase, wordno in rv.items():
                if wordno is None:
                    lg.pr('phrase:', phrase, ':: [ambigous] multiple hits')
                    ambig_cnt += 1
            print('#keys:', len(rv), '#ambiguous:', ambig_cnt)
        return rv

    def correlate_xy(self, ywords, xwords_keys, xwords, verbosity):
        """TBD"""
        skip = 0
        matched_cnt = 0
        far_out_cnt = 0
        far_out_max = 10 # limit how far from begining of subtitle
        far_out_capnos = set() # the captions NOT matched due to too far out
        matched_capnos = set() # the captions NOT matched due to too far out
        for idx in range(len(ywords)):
            if skip > 0:
                skip -= 1
                continue
            # get a list of words at idx of limited size and believed
            # to be separated by less than a second or so
            phrase_words = self.get_phrase_words(ywords, idx)
            for cnt in range(len(phrase_words)-1, 0, -1):
                phrase = ' '.join([w.word for w in phrase_words[0:cnt]])
                xwordno = xwords_keys.get(phrase, None)
                if not xwordno:
                    # lg.tr9('correlate_xy(): FAILED lookup:', phrase)
                    continue
                for widx in range(cnt):
                    xword = xwords[xwordno + widx]
                    if xword.mcap.capno in matched_capnos:
                        continue # don't match same caption twice
                    if xword.mcap.capno in far_out_capnos:
                        continue # don't reject same caption twice
                    yword = ywords[idx + widx]
                    if xword.pos + yword.pos > far_out_max:
                        far_out_capnos.add(xword.mcap.capno)
                        continue
                    if not xword.mcap.matches:
                        matched_cnt += 1
                        matched_capnos.add(xword.mcap.capno)

                    xsubphrase = [xwd for xwd in xwords[widx:cnt]
                            if xwd.mcap.capno == xword.mcap.capno]

                    xword.mcap.matches.append(SimpleNamespace(**{'phrase': phrase,
                        'delta_ms': yword.ms - xword.ms,
                        'ypos': yword.pos, 'xpos': xword.pos,
                        'xlen': len(xsubphrase)}))
                    if xword.pos + yword.pos > far_out_max:
                        far_out_capnos.add(xword.mcap.capno)
                        continue
                skip = cnt - 1
                break # if longest sub-phrase is consumed, done

        far_out_cnt = len(far_out_capnos - matched_capnos)
        self.far_out_point_cnt = far_out_cnt
        self.point_cnt = matched_cnt

        if verbosity >= 1:
            print('\n=> Matched', matched_cnt, 'xcaps of', len(self.xmcaps),
                    'less', far_out_cnt, 'questionable')

    def dump_xmcaps(self):
        """TBD"""
        # for idx in range(min(1000, len(xmcaps))):
        for mcap in self.xmcaps:
            output = 'xcap:{}\n'.format(str(mcap.caption))
            for match in mcap.matches:
                output += ' {:5.3f}s [x{}y{}] {}\n'.format(match.delta_ms/1000,
                        match.xpos, match.ypos, match.phrase)
            lg.pr(output)

    def replicate_xmcaps(self, o_xmcaps):
        """TBD"""
        self.xmcaps = [SimpleNamespace(**{'caption': cap, 'capno': idx, 'matches': []})
                for idx, cap in enumerate(self.captions)]
        for omcap in o_xmcaps:
            mcap = self.xmcaps[omcap.capno] # works because now one-to-one with captions
            for match in omcap.matches:
                mcap.matches.append(SimpleNamespace(**vars(match))) # deep copy does not work
        self.squeeze_xmcaps()

    def init_xmcaps(self):
        """Create a 'sparse' list of 'mcaps' from the captions; mcaps have both
        caption info and correlation/match information."""
        self.xmcaps = [SimpleNamespace(**{'caption': cap, 'capno': idx, 'matches': []})
                for idx, cap in enumerate(self.captions)]

    def squeeze_xmcaps(self):
        """TBD"""
        xmcaps = [p for p in self.xmcaps if p.matches]
#       ocnt = len(self.xmcaps)
#       if False and ocnt > len(xmcaps):
#           lg.pr('SQUEEZED xmcaps from', ocnt, 'to', len(xmcaps))
        self.xmcaps = xmcaps

    def make_xyvals(self, bot=None, top=None):
        """TBD"""
        xvals, yvals = [], []
        bot = 0 if bot is None else bot
        top = len(self.xmcaps) if top is None else top
        for mcap in self.xmcaps:
            for match in mcap.matches:
                xvals.append(mcap.caption.beg_ms)
                yvals.append(match.delta_ms)
        return xvals, yvals

    def purge_outliers(self):
        """TBD"""
        self.squeeze_xmcaps()
        for dist in (5, 4, 3, 2):
            self.remove_unordered(dist)

        outlier_cnt = 1 # prime the pump
        while outlier_cnt:
            xvals, yvals = self.make_xyvals()
            lri = self.linear_regression(xvals, yvals, b_rnd=0)
            lg.tr1('1st linear regression:', vars(lri))
            outlier_cnt = 0
            for mcap in self.xmcaps:
                ok_matches = []
                for match in mcap.matches:
                    y_calc = lri.intercept + lri.slope * mcap.caption.beg_ms
                    if abs(match.delta_ms - y_calc) < 3 * lri.stdev:
                        ok_matches.append(match)
                    else:
                        outlier_cnt += 1
                mcap.matches = ok_matches

            lg.tr1('OUTLIER_CNT:', outlier_cnt)
            self.squeeze_xmcaps()

        # NOW, reduce matches to just the best match
        for mcap in self.xmcaps:
            if len(mcap.matches) < 2:
                continue
            over30s = [m for m in mcap.matches if len(m.phrase) >= 30]
            closest_val, closest_match = 10000, None
            candidates = over30s if over30s else mcap.matches
            for match in candidates:
                if closest_val > match.xpos + match.ypos:
                    closest_val = match.xpos + match.ypos
                    closest_match = match

            mcap.matches = [closest_match]

    def remove_unordered(self, dist):
        """Only for dist >= 2
        TODO: check these ranges
        """
        xmcaps = self.xmcaps
        for idx in range(len(xmcaps)-1, dist-1, -1):
            mcap = xmcaps[idx]
            ok_matches = []
            for match in mcap.matches:
                cap_ms = mcap.caption.beg_ms + match.delta_ms
                for oidx in range(1, dist+1):
                    omcap = xmcaps[idx-oidx]
                    ocaption, omatches = omcap.caption, omcap.matches
                    ocap_ms_min = ocaption.beg_ms + min([m.delta_ms for m in omatches])
                    if cap_ms > ocap_ms_min:
                        ok_matches.append(match)
                        break
            mcap.matches = ok_matches
        self.xmcaps = xmcaps
        self.squeeze_xmcaps()

        xmcaps = self.xmcaps
        for idx in range(len(xmcaps) - dist):
            mcap = xmcaps[idx]
            ok_matches = []
            for match in mcap.matches:
                cap_ms = mcap.caption.beg_ms + match.delta_ms
                for oidx in range(dist):
                    omcap = xmcaps[idx+oidx]
                    ocaption, omatches = omcap.caption, omcap.matches
                    ocap_ms_max = ocaption.beg_ms + max([m.delta_ms for m in omatches])
                    if cap_ms < ocap_ms_max:
                        ok_matches.append(match)
                        break
            mcap.matches = ok_matches
        self.xmcaps = xmcaps
        self.squeeze_xmcaps()

    def find_breaks(self, nominal_slope):
        """TBD"""

        def best_break(self, xvals, yvals, bot, top, lri):

            if lri.slope < 0:
                yvals = [-y_ms for y_ms in yvals]
            cur_bot, cur_top = bot, top
            best_value, best_mid, gap = None, 0, None # no best gap < 0 will be acceptable
            border_wid = (cur_top - cur_bot) // tune.border_div
            floor = bot + border_wid
            ceiling = top - border_wid

            for mid in range(floor, ceiling):
                left = max(min(mid - tune.pref_pts, bot), 0)
                right = min(max(mid + tune.pref_pts, bot), len(xvals))

                if mid-left < tune.min_pts or right-mid < tune.min_pts:
                    continue

                l_lri = self.linear_regression(xvals[bot:mid], yvals[bot:mid], b_rnd=0)
                if abs(l_lri.slope - nominal_slope) > tune.max_slope_delta:
                    continue
                r_lri = self.linear_regression(xvals[mid:top], yvals[mid:top], b_rnd=0)
                if abs(r_lri.slope - nominal_slope) > tune.max_slope_delta:
                    continue

                value = math.sqrt((l_lri.squares_sum + r_lri.squares_sum)/(l_lri.N + r_lri.N))
                if best_value is None or value < best_value:
                    best_value, best_mid = value, mid

            if best_value:
                mid = best_mid
                l_lri = self.linear_regression(xvals[bot:mid], yvals[bot:mid], b_rnd=0)
                r_lri = self.linear_regression(xvals[mid:top], yvals[mid:top], b_rnd=0)
                joint_stdev = math.sqrt((l_lri.squares_sum + r_lri.squares_sum)
                        /(l_lri.N + r_lri.N))
                if DBdumpLrAns or DEBUG:
                    self.print_lri(lri, indent=10)
                    self.print_lri(l_lri, indent=10)
                    self.print_lri(r_lri, indent=10)
                y_range = abs(lri.y_left - lri.y_right)
                if joint_stdev >= lri.stdev * tune.min_dev_frac:
                    if DBdumpLrAns or DEBUG:
                        print('NOPE: did not reduce std deviation enough [{:.1f}%]'.format(
                                round(joint_stdev/lri.stdev)*100, 1))
                if (l_lri.stdev > lri.stdev * tune.max_dev_frac
                        or r_lri.stdev > lri.stdev * tune.max_dev_frac):
                    if DBdumpLrAns or DEBUG:
                        print('NOPE: left/right brk dev too big [{.0f}%, {:.0f}]'.format(
                                100*l_lri.stdev/lri.stdev, 100*r_lri.stdev/lri.stdev))
                    best_value = None
                elif abs(l_lri.slope - r_lri.slope) > tune.max_parallel_delta:
                    if DBdumpLrAns or DEBUG:
                        print('NOPE: slopes not parallel')
                    best_value = None

            else:
                if DBdumpLrAns or DEBUG:
                    print('NOPE: best_value not found', best_value, '/', y_range)
                best_value = None
            if best_value is not None:
                if DBdumpLrAns or DEBUG:
                    print('YES: gap works', best_value, '/', y_range,
                            '[', bot, best_mid, top, ']')
                x_ms = (xvals[best_mid-1] + xvals[best_mid])/2
                lval = l_lri.intercept + l_lri.slope * x_ms
                rval = r_lri.intercept + r_lri.slope * x_ms
                gap = int(round(lval - rval))
                if False:
                    print('found gap:', gap, 'at:', self.hhmmss_str(x_ms/1000),
                            '\n   ', self.xmcaps[best_mid-1].caption,
                            '\n   ', self.xmcaps[best_mid].caption,
                            '\n   ', mid
                            )

            return best_value, lri.stdev, best_mid, gap


        tune = self.subshop_params.rift_params
        # print('tune:', vars(tune))
        xvals, yvals = self.make_xyvals()

        gap_positions = [(0, 0, 0, 0)]
        # ans_whole = self.linear_regression(xvals, yvals, b_rnd=0)
        # self.print_lri(ans_whole, prefix='=== LINEAR FIT (WHOLE):')

        break_cnt_hint = 1 + int(round(self.captions[-1].end_ms
            / ( tune.trial_mins*60*1000)))
        break_cnt_hint = max(tune.min_trial_segs, break_cnt_hint)

        section_len = (len(yvals) + break_cnt_hint - 1) // break_cnt_hint
        bot, top = 0, section_len
        while True:
            if DBdumpLrAns or DEBUG:
                print('bot:', bot, 'top:', top)
            lri = self.linear_regression(xvals[bot:top], yvals[bot:top], b_rnd=0)
            if abs(lri.y_right - lri.y_left) < 300: # don't bother trying
                stdev, o_stdev, pos, gap = 0, 0, 0, None
            else:
                stdev, o_stdev, pos, gap = best_break(self, xvals, yvals, bot, top, lri)
            # compute next bot
            bot = bot + int(round(section_len
                    * (tune.border_div-3)/tune.border_div))
            if stdev:
                gap_positions.append((pos, gap, round(stdev, 0), round(o_stdev, 0)))
                lg.tr1('gaps:', gap_positions[-1])
                bot = max(bot, pos+1)  # don't let next bot precede break
            top = min(len(yvals), bot + section_len)
            if top - bot < section_len / 2:
                break

        gap_positions.append((len(yvals), 0, 0, 0))
        if DEBUG:
            print('gaps:', gap_positions)

        points, squares_sum = 0, 0
        for idx, gapinfo in enumerate(gap_positions):
            gap, _, _, _ = gapinfo
            if idx < len(gap_positions) - 1:
                next_gap = gap_positions[idx+1][0]
                bot, top = gap, next_gap
                lri = self.linear_regression(xvals[bot:top], yvals[bot:top], b_rnd=0)
                # self.print_lri(lri, prefix='SEGMENT:')
                points += lri.N
                squares_sum += lri.squares_sum
                self._add_formula(bot, top, lri)
#       if False and len(gap_positions) > 2:
#           print('#segments:', len(gap_positions)-1, 'stdev:',
#                   int(round(math.sqrt(squares_sum/points))))


    def adjust_by_formulas(self, formulas):
        """TBD"""

        def adjust_ms(millis, lri):
            return int(round(millis + lri.intercept + lri.slope*millis))

        def pick_best_rift1(bot, top):
            nonlocal self
            DB = False
            if DB:
                lg.pr('pick_best_rift:', bot, top)
            best_gap_ms, best_capno = -100000, bot
            ocaption = self.captions[bot] # advance for non-trite captions only
            for idx in range(bot, top):
                caption = self.captions[idx+1]

                gap_ms = caption.beg_ms - ocaption.end_ms
                if DB:
                    star = '*' if gap_ms > best_gap_ms else ' '
                    lg.pr(f'{star} {gap_ms}ms #{idx} {caption}')
                if gap_ms > best_gap_ms:
                    best_gap_ms, best_capno = gap_ms, idx+1
                for line in caption.lines:
                    if re.search(r'[a-zA-Z]{2,}', line):
                        ocaption = caption

            return best_capno

        # firstly, find the nominial rifts as caption numbers
        rifts = [0] * len(formulas)
        rifts[-1] = len(self.captions)
        for idx in range(0, len(formulas)-1):
            formula, nformula = formulas[idx], formulas[idx+1]

            low = self.xmcaps[formula.xtop-1].capno
            high = self.xmcaps[nformula.xbot].capno
            rifts[idx] = pick_best_rift1(low, high)


        # finally, adjust the captions per the formula while honoring the rifts
        rift_idx, formula = 0, formulas[0]
        self.print_lri(formula.lri, prefix='=>               ')
        for idx, caption in enumerate(self.captions):
            if idx >= rifts[rift_idx]:
                rift_idx += 1
                formula, oformula = formulas[rift_idx], formulas[rift_idx-1]
                lri, olri = formula.lri, oformula.lri
                delta_ms = (adjust_ms(caption.beg_ms, lri)
                            - adjust_ms(caption.beg_ms, olri))
                caption.beg_ms = adjust_ms(caption.beg_ms, lri)
                caption.end_ms = adjust_ms(caption.end_ms, lri)
                cap_str = caption.mini_str()
                lg.pr(f'=> {cap_str} <<{"="*max(0,58-len(cap_str))} {delta_ms}ms rift')
                self.print_lri(lri, prefix='=>               ')
            else:
                lri = formula.lri
                caption.beg_ms = adjust_ms(caption.beg_ms, lri)
                caption.end_ms = adjust_ms(caption.end_ms, lri)


    def print_lri(self, lri, indent=0, prefix=None):
        """Print a summary of the linear regression result."""
        print(' '*indent + (prefix + ' ' if prefix else ''),
                '[{} to {}]'. format(
                    self.hhmmss_str(lri.x_left/1000),
                    self.hhmmss_str(lri.x_right/1000)),
                # int(round(lri.stdev)), 'y-l/r:',
                # int(round(lri.y_left)), int(round(lri.y_right)),
                # int(round(lri.intercept)),
                # '+m:', f'{lri.slope:.5f}',
                lri.line,
                'dev:', int(round(lri.stdev)),
                # int(round(lri.intercept)),
                'pts:', lri.N
                )


class SubFixer:
    """Handler for scrubbing one SRT file at a time"""

    def __init__(self, opts):
        """Accepts the namespace created by ArgumentParser OR the list
        of command line arguments to give to ArgumentParser."""
        if isinstance(opts, list):
            opts = self.parse_args(opts)
        self.opts = opts
        self.caplist = None

    @staticmethod
    def parse_args(args=None):
        """Argument parsing."""
        parser = argparse.ArgumentParser(
                description = 'Scrub SRT files with optional offset.')
        parser.add_argument('-O', '--no-overwrite', action = "store_false", dest='overwrite',
                help = "do NOT overwite original file leaving temp file")
        parser.add_argument('-f', '--force', action = "store_true",
                help = "write temp file even if unchanged")
        parser.add_argument('-i', '--interactive', action = "store_true",
                help = "prompt whether to remove ads, etc")
        parser.add_argument('-T', '--temp-file', help="specify name of temp file")
        parser.add_argument('-v', '--verbose', action = "store_true", default = False,
                help = "choose whether show details")
        parser.add_argument('-V', '--log-level', choices=lg.choices,
            default='INFO', help='set logging/verbosity level [dflt=INFO]')
        parser.add_argument('--compare', action="store_true",
                help='compare orig_srt_file to synced_srt_file only')
        parser.add_argument('--analyze', action="store_true",
                help='word-by-word analysis of reference .srt to synced_srt_file only')
        parser.add_argument('-d', '--duration', type=float, default=None,
                help="specify video duration in seconds")
        parser.add_argument('srt_files', nargs='+', help='list pairs of delay and SRT file')
        return parser.parse_args(args)


    def do_one_file(self, delay_ms, srt_file, make_analyzer=False):
        """TBD"""
        lg.tr4(delay_ms, srt_file)
        if not srt_file.lower().endswith('.srt') or not os.path.isfile(srt_file):
            lg.err('invalid srt file:', srt_file)
            return False

        if self.opts.compare or self.opts.analyze:
            out_filename = '/dev/null'
        else:
            out_filename = (self.opts.temp_file if self.opts.temp_file
                    else os.path.splitext(srt_file)[0] + '.TEMP.srt')
        updated = False
        with open(out_filename, 'w', encoding = 'utf-8', errors='ignore') as out:
            with open(srt_file, 'r', encoding = 'utf-8', errors='ignore') as srt:
                self.caplist = (CaptionListAnalyzer(srt) if make_analyzer
                        else CaptionList(srt))
                if self.opts.compare or self.opts.analyze:
                    return False

                self.caplist.repair(verbose=self.opts.verbose)

                if delay_ms:
                    lg.db(f'delay_subs({delay_ms})')
                    self.caplist.delay_subs(delay_ms)
                lg.tr9('detecting ads...')
                self.caplist.detect_ads()
                if self.caplist.ads:
                    lg.pr('\n------> Will remove these ads:')
                    for pair in self.caplist.ads:
                        regex, idx = pair
                        lg.pr('   [{}] {}'.format(regex, str(self.caplist.captions[idx])))


                    if self.opts.interactive:
                        lg.pr('------> OK? ', end='')
                        sys.stdout.flush()
                        response = getch().lower()
                    else:
                        response = 'y'

                    if response == 'y':
                        self.caplist.purge_ads()

                if self.caplist.is_updated() or self.opts.force:
                    outs = ''
                    for idx, caption in enumerate(self.caplist.captions):
                        outs += '\n' if idx else ''
                        outs += caption.to_str(idx+1)
                    rv = out.write(outs)
                    updated = True
                    lg.pr('------> Wrote', rv, 'bytes')
                else:
                    lg.pr('------> NO changes')


        if updated:
            if self.opts.overwrite:
                shutil.move(out_filename, srt_file)
            return True
        else:
            if self.opts.overwrite:
                os.unlink(out_filename)
            return False

    def grep_one_file(self, srt_file, pattern=None, use_config_pats=False):
        """Run the grep function on one SRT file."""
        if not pattern and not use_config_pats:
            use_config_pats = True
        with open(srt_file, 'r', encoding='utf-8', errors='ignore') as srt:
            caplist = CaptionList(srt)
            caplist.detect_ads(pattern=pattern, use_config_pats=use_config_pats)
            if caplist.ads or self.opts.verbose:
                print('\n=>', os.path.basename(srt_file),
                    "IN", os.path.dirname(srt_file))
            for regex, idx in caplist.ads:
                lg.pr('   [{}] {}'.format(regex,
                        caplist.captions[idx].delta_str(caplist)))
            if caplist.ads and self.opts.force:
                self.do_one_file(delay_ms=0, srt_file=srt_file)
        return bool(caplist.ads)

def runner(argv):
    """
    SubFixer.py [H] - fixes subtitle errors (e.g., overlaps), removes ads,
    and syncs against a reference.  Normally, use 'subshop ...' to implicitly
    use this where needed. The runner() provides access to the primitive tool.
    """
    opts = SubFixer.parse_args(argv)
    fixer = SubFixer(opts)
    lg.setup(level=opts.log_level)
    delay_ms = 0
    orig_caplist = None  # any subs for compare() or reference subs for analyze()

    for token in opts.srt_files:
        if re.match(r'[\-\+]?\d+(|\.\d+)$', token):
            offset = float(token)
            if -50.0 < offset <= 50.0:
                delay_ms = int(round(offset * 1000))
            else:
                delay_ms = int(round(offset))
        else:
            fixer.do_one_file(delay_ms, token,
                    make_analyzer=bool(orig_caplist and opts.analyze))

            if opts.compare and orig_caplist:
                compare_str = fixer.caplist.compare(orig_caplist, opts.duration)
                lg.pr(compare_str)
                sys.exit(0)
            elif opts.analyze and orig_caplist:
                compare_str = fixer.caplist.analyze(orig_caplist,
                        opts.duration, opts.temp_file,
                        verbosity=1 if opts.verbose else 0)
                lg.pr(compare_str)
                sys.exit(0)
            elif opts.compare or opts.analyze:
                orig_caplist = fixer.caplist
    if opts.compare or opts.analyze:
        lg.pr('Usage error: must provide {reference_srt_file} and {synced_srt_file}\n')
