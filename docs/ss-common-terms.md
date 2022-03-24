
## Common terms and options
### subshop's Options, Sub-Commands, and Targets
The `subshop` sub-commands often share terminology and conventions.  The typical form of a subcommand is:
```
    $ subshop -h # shows the available subcommands
    $ subshop {subcmd} -h # help for the given subcommand
    $ subshop {subcmd} [{options}] {targets} # typical use
```
You can only run one `subshop` instance at a given time.  File locking is used to ensure exclusivity, and since file locking is imperfect, it may be necessary to remove the lock file shown when the lock cannot be obtained ONLY IF IN ERROR.  File locking protects the integrity of its various state files.  Generally, if a state file becomes corrupted, you should remove it (states files typically reside in `~/.cache/subshop/`).

#### Selecting subshop "Options"
Options are specified with `-{letter}` or `--{word}` arguments. In Python 3.7+, options and non-options can be intermixed; otherwise, you must place all sub-command options immediately after the {subcmd}.  Here are a few common options:

* `-h/--help`: shows basic usage
* `-n/--dry-run`: shows what a sub-command would do, more or less.
* `-v/--verbose`: add more detail to output
* `-V/--log-level {level}`: where the {level} may be standard logging levels (e.g. "INFO") or any of the custom levels shown by `--help`.
* `-o/--only {tv|movie}`: select only TV episodes or movie.
* `-O/--one`: select just the shortest title match, preferring TV episodes if both a TV show and movie match.
* `-p/--plex`: if Plex is configured, use Plex for searches.
* `-P/--avoid-plex`: even if Plex is configure, use built in search.

See the description of every sub-command in the "Sub-Commands" section below.

#### Selecting subshop "Targets"
Most of the sub-command operate on video file "targets".
The {targets} may be either:

* a list of folders and/or video files, or
* a TV show, season, or episode specifying the title and options season and episode; e.g.,

    * `blue bloods`     # all seasons/episode
    * `blue bloods 1x`  # or s01 to specify season 1
    * `blue bloods 1x3` # or s01e03 to specify a specific episode
* a movie title; e.g. `wonder woman`

For a non-PLEX search, a given title matches the video file only if:
1. the specified title is an exact substring in the parsed video file title (ignoring case), and
2. (for tv episodes only) if supplied, the given season/episode matches in spirit (e.g., "2x3" matches "s02e03")

In a non-PLEX titles search, the matched video with the shortest video name are selected by default; so you may need to lengthen the name for a precise match.  Also, you can opt:

* `-e/--every` to have every title match be selected

If the title search is inadequate, using the pathname to video (or folder of videos) always works.

You may restrict targets to TV episodes or movies with the option:

* `-o/--only{type}` where `{type}` may be "tv" or "movie".

### Reference Subtitles
Reference subtitles are generated (and cached) by the external tool, [autosub](https:/github.com/agermanidis/autosub), or the internal tool, `video2srt`.

 * Reference subtitles are generally unusable as "real", external subtitles because they have too many omissions/errors.
 * But, reference subtitles are generally good enough to correlate with external subtitles to synchronize those with the video;
 * Reference are also used to judge how well subtitles are synced with the video.

`video2srt` generally does a more accurate job than `autosub`, but `autosub` might be preferred if local CPU and/or memory resources are scarce since most the (considerable) effort is exported to the cloud.

`video2srt` uses [vosk · PyPI](https://pypi.org/project/vosk/) to create reference subtitles.


### Subtitle Score
Subtitles are given a score from 1 to 19 that represents:

* the tenths of seconds of standard deviation of the subtites to the reference, plus
* a penalty of 0 to 20 if the number captions correlated to the reference subtitles is under 50

If the net subtitle score is not between 1 and 19, then it is coereced within.  For filtering purposes, an unscored subtitle is given an arbitrary, large score (e.g., 100) but that score is not store.

**Filtering on score.** Some sub-commands honor options:

* `-m/--min-score {score}`: filter for videos with subtitles only as poor as the given floor
* `-M/--max-score {score})`: filter for videos with subtitles no worse than then given score.