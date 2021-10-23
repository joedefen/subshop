# SUBSHOP
Tools to download, remove ads, and synchronize subtitles.
<!--ts-->
* [SUBSHOP](#subshop)
   * [Purpose](#purpose)
   * [Limitations](#limitations)
   * [Required Web Credentials](#required-web-credentials)
* [Installation, Configuration, and Preparation](#installation-configuration-and-preparation)
   * [Installation Procedure](#installation-procedure)
   * [Configuration](#configuration)
   * [Verify the Installation](#verify-the-installation)
   * [Optional: Install autosub](#optional-install-autosub)
   * [Optional: Automating Download/Sync of Subtitles](#optional-automating-downloadsync-of-subtitles)
* [Expected Video Folder Organization](#expected-video-folder-organization)
      * [Video File Naming Conventions](#video-file-naming-conventions)
      * [Description/Rationale for the Cached Files](#descriptionrationale-for-the-cached-files)
* [SUBSHOP Command Use](#subshop-command-use)
   * [Common terms and options](#common-terms-and-options)
      * [subshop's Options, Sub-Commands, and Targets](#subshops-options-sub-commands-and-targets)
         * [Selecting subshop "Options"](#selecting-subshop-options)
         * [Selecting subshop "Targets"](#selecting-subshop-targets)
      * [Reference Subtitles](#reference-subtitles)
      * [Subtitle Score](#subtitle-score)
   * [Sub-commands](#sub-commands)
      * [subshop stat {targets}  # get basic subtitle status](#subshop-stat-targets---get-basic-subtitle-status)
      * [subshop search {targets} # search for TV shows and/or movies](#subshop-search-targets--search-for-tv-shows-andor-movies)
      * [subshop ref {targets} # generate reference subtitles](#subshop-ref-targets--generate-reference-subtitles)
      * [subshop dos {targets}  # download-and-sync subtitles](#subshop-dos-targets---download-and-sync-subtitles)
      * [subshop redos {target}  # re-download-and-sync subtitles](#subshop-redos-target---re-download-and-sync-subtitles)
      * [subshop sync {target} # synchronize (yet again) subtitles](#subshop-sync-target--synchronize-yet-again-subtitles)
      * [subshop anal {targets} # analyze the quality of subtitles](#subshop-anal-targets--analyze-the-quality-of-subtitles)
      * [subshop todo {targets} # create TODO lists for maintenance](#subshop-todo-targets--create-todo-lists-for-maintenance)
      * [subshop ignore {targets} # disable subtitle actions](#subshop-ignore-targets--disable-subtitle-actions)
      * [subshop unignore {targets} # re-enable subtitle actions](#subshop-unignore-targets--re-enable-subtitle-actions)
      * [subshop zap {targets} # remove external subtitles](#subshop-zap-targets--remove-external-subtitles)
      * [subshop -D{secs} delay {targets}  # manually shift subtitle times](#subshop--dsecs-delay-targets---manually-shift-subtitle-times)
      * [subshop grep {targets} # find patterns in subtitles](#subshop-grep-targets--find-patterns-in-subtitles)
      * [subshop parse {targets} # check parsability of video filenames](#subshop-parse-targets--check-parsability-of-video-filenames)
      * [subshop imdb {targets} # verify/update IMDB info for videos](#subshop-imdb-targets--verifyupdate-imdb-info-for-videos)
      * [subshop tvreport # summarize missing subtitles for TV shows](#subshop-tvreport--summarize-missing-subtitles-for-tv-shows)
      * [subshop inst {video}... {folder} # "install" videos](#subshop-inst-video-folder--install-videos)
      * [subshop dirs # show subshop's persistent data directories](#subshop-dirs--show-subshops-persistent-data-directories)
      * [subshop tail # follow the log file](#subshop-tail--follow-the-log-file)
      * [subshop run {module} # run low-level module](#subshop-run-module--run-low-level-module)
* [Remedying Missing/Misfit Subtitles](#remedying-missingmisfit-subtitles)
   * [A. When You Need Better Fitting Subtitles](#a-when-you-need-better-fitting-subtitles)
   * [B. When OpenSubtitles.org Does Not Have the Subtitles](#b-when-opensubtitlesorg-does-not-have-the-subtitles)
   * [C. When No Subtitles Fit](#c-when-no-subtitles-fit)
   * [D. When Internal Subtitles Fit Poorly](#d-when-internal-subtitles-fit-poorly)
   * [E. When 'subshop' Falls Back to Less Desired Subtitles](#e-when-subshop-falls-back-to-less-desired-subtitles)
   * [F. Manually Adjusting Subtitles](#f-manually-adjusting-subtitles)
* [Theories of Operation](#theories-of-operation)
   * [Choosing Subtitles to Download](#choosing-subtitles-to-download)
   * [Synchronizing Subtitles](#synchronizing-subtitles)
* [Related and Inspirational Projects](#related-and-inspirational-projects)
   * [<a href="https://github.com/sc0ty/subsync">GitHub - sc0ty/subsync: Subtitle Speech Synchronizer</a>](#github---sc0tysubsync-subtitle-speech-synchronizer)
   * [<a href="https://github.com/kaegi/alass">GitHub - kaegi/alass</a>](#github---kaegialass)
   * [<a href="https://github.com/emericg/OpenSubtitlesDownload">GitHub - emericg/OpenSubtitlesDownload</a>](#github---emericgopensubtitlesdownload)
   * [<a href="https://pypi.org/project/subnuker/" rel="nofollow">subnuker · PyPI</a>](#subnuker--pypi)
   * [<a href="https://github.com/platelminto/parse-torrent-title">GitHub - platelminto/parse-torrent-title</a>](#github---platelmintoparse-torrent-title)
   * [<a href="https://www.reddit.com/r/PleX/comments/m8g1km/super_fast_way_to_add_srt_subtitles_to_your_movies/" rel="nofollow">Super Fast Way to Add SRT Subtitles to Your Movies : PleX</a>](#super-fast-way-to-add-srt-subtitles-to-your-movies--plex)

<!-- Added by: joe, at: Sat Oct 23 11:59:35 AM EDT 2021 -->

<!--te-->
## Purpose
`subshop`, or "Subtitle Workshop", is a set of subtitle tools intended to mostly automate:

* the downloading of subtitles (if needed) for video files,
* synchronizing external subtitles with the audio track, and
* removing ads from the subtitles.

When necessary and preferred, the tools can be use manually for in-a-hurry situations and/or improving/correcting the automated decisions.

There are some novel features that enhance the user experience including:

* explicitly and intuitively scoring the subtitle synchronization so that the user (and tasks) know which subtitles need remediation,
* caching "precious" information, like reference subtitles, so that multiple subtitle sync trials can be done quickly,
* implementing both linear and segmented linear adjustments to subtitles for best chance at synchronization.

## Limitations
Current limitations of these tools are:

* only **English** subtitles and audio tracks are supported,
* only **srt** subtitles are supported
* for best / most automated operation, movies and TV episodes must be organized in a PLEX-like directory structure,
* auxiliary information is stored (mostly) in a "cache" directory, one per video file,
* must run on a modern Linux (or sufficient Linux comparable) operating system.
* Python 3.6 is the bare minimum, but Python 3.8+ is best.
* Python 2.x is required if you choose to use [autosub](https:/github.com/agermanidis/autosub).

## Required Web Credentials
You are expected to obtain:

* an opensubtitles.org account and know your username and password; this allows for 200 subtitles per day.
* [The Movie Database API](https://developers.themoviedb.org/3/getting-started/introduction) key;  see the instructions on the linked page.
* (optional) your Plex server URL and token;
    * the default is "http:/localhost:32400"
    * to get the token, see [Finding an authentication token / X-Plex-Token | Plex Support](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)

OpenSubtitles.org is fairly unreliable (e.g., you might find it down 10% of the day). `subshop` attempts to use these unreliable/stingy resources efficiently, and automating tasks in the background can reduce frustration.  The cache files are an important part of that strategy.

Plex is used narrowly; if you have a large collection and/or very limited CPU/RAM resources, you can configure `subshop` to use Plex for its searches which, for some installs, reduces searches for videos from, say, 10 minutes to nearly instantaneous.

# Installation, Configuration, and Preparation
## Installation Procedure
Clone the project into, say, your home directory; and install into, say, your your directories:
```
    $ cd; git clone https://github.com/joedefen/subshop.git
    $ cd subshop; pip3 install . --user 
        # ---OR--- do a virtualenv install
    $ cd subshop
    $ python -m venv .venv
    $ source .venv/bin/activate
    $ pip install .
        # run tests and use as described within the virtualenv only
    # deactivate # disable virtualenv
    $ rm -rf .venv # cleanup virtualenv

```
Having installed the code and its python dependencies,
now install the non-python dependencies (e.g., `ffmpeg`, `ffprobe`, and the [VOSK Model](https://alphacephei.com/vosk/models)).
```
    $ ./setup-sys-deps
```
NOTE: `inst-sys-deps` will not work for every Linux variant, and you may need to whatever it cannot.

As a quick test, run `subshop dirs`; this shows the folders that `subshop` uses to store persistent data and it creates the default configuration file (which always requires adjustment).

## Configuration
The configuration is stored in `subshop.yaml`, and, by default, in the `~/.cache/subshop/` folder.

You'll need to edit `subshop.py` and:

* at least, change the **YOUR-{something}** values; use the comments to enlighten you on what is needed.
* review other values and ensure the defaults are desirable for you.

The essential configuration to update is:
```
  - /YOUR-TV-ROOTDIRS
  - /YOUR-MOVIE-ROOTDIRS
  - tmdb-apikey: YOUR-TMDB-APIKEY # from tmdb-api.com
  - opensubtitles-org-usr-pwd: YOUR-USER YOUR-PASSWD # from opensubtitles.org (200down/day free)
```
Note:
* You must list your TV and Movie directory trees for:
    * the built-in search
    * for giving type hints to the video filename parser.
* The Movie Database API is used to ascertain and save IMDB IDs for accurate downloads.  
* The OpenSubtitles.org user/password is required for downloading subtitles.

And, you may wish to configure PLEX sooner rather than later (to be sure, PLEX is NOT required); otherwise, disable it.
```
  - plex-url-token: YOUR-PLEX-URL YOUR-PLEX-TOKEN # if empty string, plex is not enabled
  - search-using-plex: false # search for videos w plex (if configured)?
  - plex-path-adj: "" # set -/{prefix} and/or +/{prefix} to make local path
```
Specifically, for PLEX:
* The plex-url-token is needed if you wish to search for video files using Plex vs the built-in search;  the bigger and slower your disk, the more likely Plex will be faster (and sometimes night-and-day faster).  Also, the Plex searches are "smarter". Also,
    * Set `search-using-plex` to true if you wish that default.
    * Set `plex-path-adj` appropriately if plex's view of the file system disagrees with the local view (and your are using Plex for searches).

**Tip**:
* after making/writing changes to `subshop.yaml`, stay in the editor and run in `subshop run ConfigSubshop` in a subshell.
* make a few changes, write, check, and repair; the more changes you make w/o checking, the harder to isolate the problem.

The config will not load if:
* there are YAML syntax errors, or
* the expected basic type of a parameter is incorrect (e.g., you change a string parameter to a numberic type).

## Verify the Installation
After install, it would be a good idea to ensure a working setup and make adjustments.  Here are some commands to try.

* `subshop dirs`:  dumps the persistent data folder locations (if the configuration is loadable).
* `subshop stat {video-folder}`:  dumps the status of the videos in the given folder. With no arguments, it will run on your entire collection; depending on the size of your collection, the first run may be much slower than later run because `ffprobe` information will be cached for subsequent runs.
* `subshop dos {subless-video-file}`: given a video file w/o internal or external subtitles, tries to download and sync subtitles. This should test that your credentials for OpenSubtitles.org and TheMovieDatabase.com are working, that your voice recognition is working, etc.
* `subshop redos -i {video-file-with-external-subs}`:  interatively, attempts to download and sync replacement subtitles.  You are given a chance to fix a incorrect IMDB identification, select an alternative subtitle to try, and after synchronization, try again on move on.
* `subshop sync {video-file-with-external-subs}`: run the synchronization logid on the given video and its subtitles, make adjustments, and report the goodness of fit.
* `subshop todo`: creates various TODO lists for automating process of getting will fitted subtitles.  Depending on the size of collection, this may take quite a while. Similar to the `subshop stat` trial above, you can pass in a {video-folder} to limit the scope of the TODO lists and cut the time for the initial trial.

## Optional: Install `autosub`
If you are running on a system with limited resources for voice recognition, then it may be more practical to use [autosub](https:/github.com/agermanidis/autosub). To to so:
* follow the `autosub` install procedure (note it uses python2/pip2).
* in `subshop.yaml`, change the `reference-tool` to `autosub` (rather than the included `video2srt` script).

Using `video2srt` is the preferred configuration. On a modern, typical desktop/server, voice recognition requires about 1s per minute of video (using, say, 6 threads).  If running signficantly longer than that, then `autosub` is likely preferrable.

## Optional: Automating Download/Sync of Subtitles
You may wish to add a daily cron job; the current version of the included `subs-cronjob` is:
```
#!/bin/bash
# A recommended daily cronjob for subtitle maintenance
# e.g.:
# 13 0 * * * bash -c subs-cronjob >~/.last-subs-cron-job 2>&1
set -x
    # update the todo list
subshop todo
    # try to download/sync subs for new videos (<30 days) AND a random selection
subshop dos --todo
    # try to fix poorly scored subs
subshop redos --todo
    # try to download reference files for videos lacking them
subshop ref --todo
```
NOTES:
* `subshop todo`: creates TODO lists for automation; it limits the size of each.
* `subshop dos --todo`: performs download-and-sync on videos w/o subtitles that are on its TODO list.
* `subshop redos --todo`: performs download-and-sync on videos with misfit subtitles that are on its TODO list.
* `subshop ref --todo`: creates "reference" subtitles for videos w/o substitles or reference subtitles.  Having the reference subtitles speeds subsequent manual or automated  subtitle operations.

# Expected Video Folder Organization
TV series and movies should be organized similar to this:
```
/TV Series Root1/  # there can be many tv root folders
    Alpha Show/
        omdbinfo.yaml # subshop cached IMDB info (from OMDb usually)
        alpha.show.s01e01.anything.mkv # .ext can vary
        alpha.show.s01e01.anything.en.srt # .en.srt can vary
        alpha.show.s01e01.anything.cache/ # subshop cached info folder
        alpha show 1x2 anything.avi # .ext can vary
        alpha show 1x2 anything.en04.srt # .en04.srt can vary
        alpha show 1x2 anything.cache/ # subshop cached info
        ...
    Beta Show/
        omdbinfo.yaml # subshop cached IMDB info (from OMDb usually)
        /Season 01  # episodes under seasons share omdbinfo
            /beta.show.s01e01.anything.mkv # .ext can vary
            ...
        ...
    Gamma Show/
        Gamma Show 1/  # episodes under non-season dirs have own omdbinfo
            omdbinfo.yaml # subshop cached IMDB info (from OMDb usually)
            /gamma.show.s01e01.anything.mkv # .ext can vary
            ...
        ...
/Movie Root1/  # there can be many movie root folders
    Movies for Mom/ there can be many movie group folders
        Movie.Alpha.2020.anything.mkv # .ext may vary
        Movie.Alpha.2020.anything.en07.srt # .en07.srt may vary
        Movie.Alpha.2020.anything.cache/ # subshop cache info
            omdbinfo.yaml # omdb is specific to one movie
            ...
        Movie Beta (1999) anything/ # hierachical vs (above) flat
            Movie Beta (1999) anything.mkv # .ext may vary
            Movie Beta (1999) anything.en07.srt # .en07.srt may vary
            Movie Beta (1999) anything.cache/ # subshop cache info
                omdbinfo.yaml # omdb is specific to one movie
            ...
```
NOTES:
* If your video collection is compatible with either PLEX or Emby, you likely have a suitable organization already.
* You supply the video files and existing external subtitles (optionally, with `.en.srt` or `.srt` extensions) and the basic folder hierarchy that:
    * separates TV series and movies at a high level.
    * that creates groups TV series and movies arbitrarily.
    * places TV episodes into season folders or not (consistently per TV show).  If you have season folders, then "Season 00/" and "Specials/" folders indicate TV specials.
    * places movies in subfolders with the video filenames less extensions or not (consistency is NOT required even withing one group).
* `subshop` adds subtitles files and cached information; all its cached data is in `.cache` folders except for TV series `omdbinfo.yaml` files.
### Video File Naming Conventions
Video filenames should be "parsable" by SubShop (see `subshop parse` subcommand) meaning:

*  for TV episodes, `subshop` can parse the show name, season number, and episode number, and
*  for movies, `subshop` can parse the title and year.
    * if the year is not present, `subshop` may work well.
    * if the year is wrong, `subshop` likely will not work well.
    
`subshop` uses its own parser, `VideoParser.py` to parse the names. Within the script, you can verify what is likely to work and what is not by looking for:

* `regexes`: examine the regular expressions and comments
* `tests_yaml`: look at the tests (mostly hard cases) and the parsing results; notice that a few cases near the end are "failures".

Anyhow, we advise running `subshop parse` on your entire collection, and, if you wish `subshop` to work well, fix its complaints (although movies w/o the year are more optional than unparsable tv episodes numbers).

### Description/Rationale for the Cached Files
`subshop` creates a number of cached files; specifically:
* `omdbinfo.yaml`: caches/stores the IMDB ID and other info gathered from TMDb (The Movie Database).  Caching this information makes it "sticky" so that retrying a subtitle search for a better fit is more reliable.
* `probeinfo.yaml`: caches selected info from `ffprobe` to avoid the second or so per video file to determine if it has embedded subtitles, has an English audio stream, etc.
* `*.REFERENCE.srt` or `*.AUTOSUB.srt`: caches the (very expensive) audio-to-text conversion needed to sync / score the fit of subtitles; having this makes finding better subtitles, etc., much, much faster.
* `*.EMBEDDED.srt`: `subshop` can extract and sync embedded subtitles when you wish to do so because they are misfits.
* `*.TORRRENT.srt`: stores any "original" subtitle (via torrent or not).  If you replace the original, you can return to it or reprocess it for any reason.
* `*.srt`: other downloaded subtitles are kept for possible reprocessing but also to know what has been tried so that re-download subtitles for a better fit can avoid duplicate downloads.
* `quirk.*`: per cache, `subshop` stores at most one "quirk" file for faster screening.  The quirk types from highest priority to least are:
    * `quirk.FOREIGN`: has no English audio track (so automatically ignored).
    * `quirk.IGNORE`: manually ignored (because you don't care or you wish to stop trying to find/sync subtitles for "lost causes").
    * `quirk.SCORE.{NM}`: the two-digit "score" of the defaulted subtitle (usually name `*.en.srt`); scores are used to automatically select the best subtitle fit.
    * `quirk.AUTODEFER`: the automatic download failed or sync produced poor results.  The age of this file and the age of the video file determine when automatic retries are done.
    * `quirk.INTERNAL`: has embedded subtitles; this file is acts as a "soft" automatic ignore; you can extract/sync the embedded subtitles or "force" the download of subtitles to override the automatic reluctance.


# SUBSHOP Command Use
## Common terms and options
### subshop's Options, Sub-Commands, and Targets
The subshop sub-commands often share terminology and conventions.  The typical form of a subcommand is:
```
    $ subshop -h # shows the available subcommands
    $ subshop {subcmd} -h # help for the given subcommand
    $ subshop {subcmd} [{options}] {targets} # typical use
```
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

## Sub-commands
### subshop stat {targets}  # get basic subtitle status
Shows the summary subtitle information of the targets.

* `-v/--verbose`: shows much detail including all cached information
* `-m/--min-score`: process only subtitles with at least the given minimum score
* `-M/--max-score`: process only subtitles with no more than given maximum score

### subshop search {targets} # search for TV shows and/or movies
Shows a "search" result meaning:
* tvshow folders, and
* movie video files.

This command requires a search phrase built from the {targets}; for this subcommand {targets} cannot be files/folders and at least on is required.

If Plex is required, you may wish to compare/time searches with and without Plex (i.e., `-p` and `-P`).  Also, this command is handy if you wish to know where certain media is stored.

The search results are usually fairly similar **unless `subshop` and Plex do search the same folders; to use Plex, ensure they agree.**

Search times will depend on many factors; but, the slower your disk performance, the more likely that Plex will perform better comparatively.

### subshop ref {targets} # generate reference subtitles
Generates reference subtitles for the given targets ONLY if (1) the target has no reference subtitles, and (2) the target has external subtitles OR has no internal subtitles, (3) there is an English audio stream, and (4) the video is in the "IGNORE" state.

* `-n/--dryrun`: use to verify how many/which reference subtitles you generate.
* `--random`: randomize the targets
* `-q/--quota`: cut off target after the limit
* `--todo`: work down the TODO list (see "todo" subcommand) rather than {targets}
* `-d/--days`: only process videos newer than a given number of days

Note, generating reference subtitles is usually a byproduct of `subshop dos`, but that might be limited by quota or outages and pre-generating the reference subtitles can speed the eventual download-and-sync operation whether done manually or in the backgrond.

### subshop dos {targets}  # download-and-sync subtitles
Download and sync subtitles for the targets. Requires (1) an English audio stream, (2) not in IGNORE state, (3) no internal or externals subs, (4) not a TV special, and (5) either interactive or not auto maintenance deferred.

* `-i/--interactive`: for manual control over selecting the OMDB match and subtitles (although normally, use the non-interactive mode unless expecting/having problems getting the initial subtitles)
* `-n/--dryrun`: use to verify how many/which reference subtitles you generate.
* `--todo`: work down the TODO list (see "todo" subcommand) rather than {targets}
* `-q/--quota`: cut off target after the limit

The `dos` sub-command can be run rather indiscriminately because it restricts itself to targets that need subs, can have subs, and subs are desired.

### subshop redos {target}  # re-download-and-sync subtitles
Re-do the download and sync of subtitles for the targets; this is typically only done to correct automatic subtitle download and sync resulting in no found subtitles or misfit subtitles. Requires (1) an English audio stream, (2) not in IGNORE state, (3) has internal or externals subs.

* `-i/--interactive`: for manual control over selecting the OMDB match and subtitles `(although normally, use the interactive mode to manually repair problems).
* `-m/--min-score`: process only subtiles with at least the given minimum score
* `-M/--max-score`: process only subtiles with no more than given maximum score
* `--todo`: work down the TODO list (see "todo" subcommand) rather than {targets}

Running `redos` interactively allows you to correct IMDB information and search differently for subtitles in the case automatic search results were poor.

### subshop sync {target} # synchronize (yet again) subtitles
Re-do the sync of subtitles for the targets (w/o a download) for whatever reason (e.g., changed sync parameters or replaced reference subtitles or reexamine details of the synchronization). The reference subtitles will be regenerated if necessary. Requires (1) an English audio stream,
(2) not in IGNORE state, (3) has internal or externals subs.

* `-m/--min-score`: process only subtitles with at least the given minimum score
* `-M/--max-score`: process only subtitles with no more than given maximum score
* `-v/--verbose`: shows the correlated reference/non-reference subtitles and timing differences; if there are many non-trivial text matches, then the video and subtitles are very likely to belong to the same movie or episode; if the timing differences have large discontinuities, there are huge rifts in the video relative to the subtitles.

### subshop anal {targets} # analyze the quality of subtitles
Re-analyzes the subtitles. If tuning parameters have changed, you might get
different results.

* `-m/--min-score`: process only subtitles with at least the given minimum score
* `-M/--max-score`: process only subtitles with no more than given maximum score
### subshop todo {targets} # create TODO lists for maintenance
Creates lists of videos that need subtitles, need reference subtitles, or have poor fits suggesting that retrying is in order.  The commands that honor the `--todo` option will try to work down appropriate lists. The lists are named:
* `vip-dos`: newer videos w/o subs but with reference subs.
* `vip-ref-dos`: newer videos w/o subs and w/o reference subs.
* `dos`:  videos w/o subs but with reference subs.
* `ref-dos`: videos w/o subs and w/o reference subs.
* `redos`: videos with misfit subs ready to retry.
* `defer-dos`: videos w/o subs awaiting auto retry.
* `defer-redos`: videos with misfit subs awaiting auto retry.

**Notes**:

* Normally, running this command overwrites the current set of TODO lists (i.e., there can only be one set).
* In some installs, this command can takes minutes, but the commands working down the TODO lists should start fast.
* Normally, provide no targets so your entire collection is scanned; if you wish to focus on a subset of your collection, then provide targets.
* The number of TODO items per list actually stored is limited by configuration (since there is no need items than doable in a day); the stored items are a random sample; when other commands tackle a TODO list, they do so in random order.

Some commonly used options with `todo`:
* `-v/--verbose`: shows all the TODO items, not just the summary.
* `-n/--dry-run`: only shows the current state of the TODO list; with `-v` shows every remaining item.

### subshop ignore {targets} # disable subtitle actions
Sets the state to IGNORE for the video; this will inhibit most sub-command actions on the target except for 'unignore'.

### subshop unignore {targets} # re-enable subtitle actions
Clears the IGNORE state for the video; this enables most sub-command actions on the target.

### subshop zap {targets} # remove external subtitles
Remove external subtitles for the {targets}. Obviously, use with caution since you can easily remove all your subtitles.

* `-n/--dryrun`: use to verify how many/which subtitles you would remove.

### subshop -D{secs} delay {targets}  # manually shift subtitle times
Delays the subtitles by the amount given in the -D/--delay-secs option. A negative amount make the subtitles appear earlier rather than later. Requires an "installed" (apparently English) subtitle and acts only on the preferred one (e.g, "video.en.srt" is preferred over "video.srt").

One use case is to adjust English subtitles for a foreign language video since `subshop` does not support non-English language audio.

Your media player likely has a mechanism to ascertain the delay manually; e.g.:
*  **mpv player**: 'z' adds 100ms delay; 'Z' subtracts 100ms delay; pass the cumulative amount as the -D value.
*  **VLC media player**: 'h' adds 50ms delay and 'g' subtracts 50ms delay; pass the cumulative amount as the -D value.
*  **PLEX web player**: select "Playback Settings / Subtitle Offset" and then click buttons to adjust the offset by +50ms or -50ms; pass the **negative of** the cumulative offset as the -D value.  Note that PLEX on Roku does not support subtitle offset adjustment.

Honored options include:
* `-D/-delay-secs`: the amount of time to delay the subtitles; if the absolute value is not under 50, then the time is presumed to be in milliseconds.  Setting `-D0.0` makes sense if desiring only to rerun the ad detection and removal.
* `-i/--interactive`: if ads are detected, you get a chance to allow/deny their removal.

**Beware**:
* Avoid specifying multiple targets since the same delay will be applied to every target.
* Ads will be removed again; if your ad detection parameters are changed, then more ads may be removed.
* This command overwrites the subtitle file.
* If you specify a positive delay, subtitles with negative times are removed and not reversable with another run with a negative delay.

### subshop grep {targets} # find patterns in subtitles
Used to verify what ads would be removed if run on the current, external subtitles for the targeted videos, and optionally remove the matching subtitles.  With `-g`, you can specify an ad hoc pattern;  with `-G`, you can apply the configured regexes.  You can specify both `-g` and `-G`, and if you specify neither, then `-G` is assumed.

Suggested uses:
* Use `-g` to search for a possible pattern to configure if it is a good identifier of ads (i.e., very few or no false positives).
* Use `-G` to determine what ads would be removed if (presumably) updated, configured regexes were applied.
* Use `-fG` to remove ads per the current set of configured regexes.

Honored options include:
* -g/--grep {regex} - grep for the given {regex}
* -G/--grep-regexes - grep the configured regexes.
* -f/--force - update the subtitles by removing the matched captions.
### subshop parse {targets} # check parsability of video filenames
Used to check the parsing accuracy of your video files; i.e.,

* for TV episodes, `subshop` should be able to parse the show name, the season and the episode number.
* for movies, `shopshop` should be able to parse the title and year.

*It not necessary that **EVERY** video file is parsable*, but unparseable videos will impair both automated and manual download tasks. Less "fits-the-pattern" episodes (e.g., "special" episodes, double episodes, etc.) are problematic no matter how named.  You can decide to rename parsing exceptions or not.


* `-v/--verbose`: shows how every target is parsed; by default, only likely errors are shown.

### subshop imdb {targets} # verify/update IMDB info for videos
Views, sets, and corrects the IMDB information for the TV show or movie. For downloading the correct subtitles automatically, having a correct IMDB association reduces error considerably.


* `-i/--interactive`: shows the IMDB information and gives you opportunity to update it.
* `-n/--dryrun`: use to see whether the IMDB is cached or not.

To generate a list of TV shows / movies w/o cached IMDB info, run:
* `subshop -n imdb | grep -B1 create`

Here is an example of setting IMDB info:
```
<svr binsb> subshop -i imdb spirited away

=> Spirited Away 2001 720p BluRay x264-REKD.mkv IN /heap/Videos/Movies/Movies=Old
2021-09-17:17:13:40.452 ERR  imdb-api query failed: status=404 reason=Not Found err=<Response [404]>
   url=https://imdb-api.com/en/API//SearchMovie/k_eu9efx7m/Spirited%20Away%202001 [OmdbTool.py:337]

>>> OMDb Search Results for "Spirited Away" (2001): 
 NO matches
[0] Cancel search

>> Enter (0-0) [add "p" for poster] -OR- <New-Search-Phrase>?: 

```
At this point, you can:
* Enter "0" to quit trying.
* Or type in a new search; e.g., "spirited away?" or "tt0245429?".
    * If the search string is simply and IMDB ID, then it actually does a lookup.
    * Each search will alternately go to the OMDb API or the IMDb API.


For this video, "spirited away?" is ineffective, but entering the IMDB ID yeilds:
```
>> Enter (0-0) [add "p" for poster] -OR- <New-Search-Phrase>?: tt0245429?

>>> IMDb Search Results for "tt0245429" (2001): 
1:   Sen to Chihiro no kamikakushi (2001) tt0245429 [movie] Poster
[0] Cancel search

>> Enter (0-1) [add "p" for poster] -OR- <New-Search-Phrase>?: 
```
Now the choices are:
* Enter "1" to set the IMDB per that line.
* Enter "1p" to launch your image viewer to show the poster.
* Enter "0" to quit w/o setting the IMDB information.
* Enter another search followed by "?".

In this (hard) case, "Spirited Away" is the English title, but that is not stored in the IMDb/OMDb API databases.  Hence, we manually search on imdb.com where the search engines are more powerful and complete.  When we visit the corresponding page, the IMDB ID (i.e,. ttXXXXXXX) is in the URL.

### subshop tvreport # summarize missing subtitles for TV shows
Create a summary report for TV shows of episodes w/o subtitles.
It may look like:
```
==== Missing Subtitle Report:
        Prime Suspect (1991): 13-1/15 2s2 2s3 3-1s4 2s5 2s6 2s7
            ...
TOTAL: 332-21 missing-unavailable of 4738 videos
```
This reports that "Prime Suspect" has 13 missing subtitles (of which one seems unavailable), and two are missing in season 2, two are missing in season 3, etc.

If shows with missing subtitles are high on your watch list and subtitles are important, then this report can guide your immediate efforts.
Of course, to try to download-and-sync its season 2, then you could try:
```
    subshop dos prime suspect 2x
```

### subshop inst {video}... {folder} # "install" videos
Installation tool for moving downloaded "raw" videos/subtitles into your TV and Movie folders per the conventions we expect. Notes:

* Many, many assumptions are made, and if it does not work for your purposes, then do install manually or with your own script.
* Each given {video} may be a video file or a folder containing video files.
* This tool attempts to move the video(s) and associated English subtitle(s) to the single, given folder; if the videos do not belong in the same destination folder, use separate invocations.
* You are completely responsible for determining the correct destination folder.

### subshop dirs # show subshop's persistent data directories
Shows a list of directories that subshop uses for persistent data; i.e.:

* `config_d`: where its configuration file, `subshop.yaml` resides
* `cache_d`: where its state files reside
* `log_d`: where its log files reside
* `model_d`: where its voice recognition model resides

The `-v` option will list the files in each directory.

By default, `config_d=~/.config/subshop`, and the other three are set to `~/.cache/subshop`. You can override the defaults in your environment;
e.g, setting the variable `SUBSHOP_CONFIG_D` overrides `config_d`.

### subshop tail # follow the log file
subshop duplicates most of what it prints to its log file(s).
This sub-command will run `less -F` on the current and previous log file
(there are two files in the "rotation"). NOTE (as a `less -f` quickstart):

* you start in "follow" mode at the current file.
* `CTRL-C` will return to "normal" mode (and `F` returns to "follow" mode).
* `:n` switches to the previous log and `:p` returns to the current log.

### subshop run {module} # run low-level module
`subshop` includes a number of foundation modules and they can exercised using `subshop run`.  Some examples:

* `subshop run -h`: list all the modules and describe what they do if `run`.  The quaality of desriptions may vary widely.
* `subshop run {module} -h`: provides help for the particular module.
* `subshop run ConfigSubshop`: verifies/dumps the current configuration.
* `subshop run VideoParser`: run the filename parser on every video in your collection (per your configuration) and shows those with issues; e.g., it reports:
    * TV shows w/o a parsable season/episode ("specials" often are unparsable),
    * movies w/o a parseable year (making identification less certain).
* `subshop run VideoParser --regression -v`: run the filename parser regression tests and show the tests; you can see examples of parseable and unparseable filenames.
* `subshop run PlexQuery blood`: if you have configure PLEX for queries, shows the result of querying for the given terms ('blood' in this example).
* `subshop run TmdbTool -i {targets}`: interactively sets the IMDB info for the video targets; normally, this is part of the download operation.

--

# Remedying Missing/Misfit Subtitles
If the sync is lousy or the summary results are concerning, here are some
possible actions.

## A. When You Need Better Fitting Subtitles
It is not uncommon to need better fitting subtitles. You can try:

* `subshop -i redos {target}` to redress particular video files.
* `subshop -T defer-redos` to redress the deferred problem cases.

When given the dialog to choose subs:

* Notice the IMDB information.  Ensure that it looks like the correct match; if not, enter a new IMDB search phrase followed by "?"; for example, "blue bloods 1x1?" or "wonder woman 1984 (2019)?".
    * the IMDB info for all episodes of the same show is shared; so take care not to mess with the settings if most of the episodes have well fitted subtitles.
    * for TV shows, always supply something that looks like season/episode as a hint that it is a TV show.
    * for movies, supply no season/episode, but do supply a year to hint that you are looking for movie (but don't supply a wrong year).
    * if you are unsure which of several choices and you have configured an image viewer, then you can view the "Poster" (if available) for some clues.
* Once the IMDB info looks right, download another subtitle file.
    * The ones already downloaded are marked with a '\*'.
    * The duration is shown for each subtitle file; if the durations are exactly the same, the subtitles are probably minor variations; so prefer a subtitle of a different duration; but also prefer a duration similar to the duration of the video.
    * If you can tell the source of the video (e.g., DVD, HDTV, Web), then prefer a subtitle file indicating a similar source.
    * If you cannot find a fit in the first two or so subtitle replacements, then you are probably need to do something else.
* If think no remedy will ever be found, when prompted, enter "ignore!" to mark the video ignored for most operations.
        
## B. When OpenSubtitles.org Does Not Have the Subtitles
If you cannot find usable subtitles on OpenSubtitles.org, then you can look for them on other sites; IMHO, this it is quite uncommon to only find them elsewhere.
* if you manually download some, place them in the `.cache` folder of corresponding video and they become available in the download dialog (you need to remember the names if there is are several competitors).
* some (of many) alternative sites to find subtitles are:
    * https://www.addic7ed.com
    * https://subscene.com
    * http://www.tvsubs.net

## C. When No Subtitles Fit
For tough problems,  rerun the sync: `subshop sync {target}`
* Reported anomalies might help diagnose the problem.
* Generally, you'll see a summary line like: `OK  dev 0.92s pts 131 [...]`. Take special note of:
    * `dev 0.92s` - meaning the standard deviation of the subtitle timing error is 0.92s.  Generally, errors over 0.8s are annoyingly bad.
    * `pts 131` - the number of correlated subtitles between the reference subtitles and the installed subtitles.  The more the merrier, but under 50 or so becomes very concerning.
* Very high 'dev' and/or very low 'pts' may indicate:
    * the subtitles are for a different video,
    * the video is misnamed or corrupt.
    * the video has little dialog.

If still more clues are needed, especially if the point count is low, re-run the sync in verbose mode: `subshop -v sync {target}`. This shows the correlations between the installed and reference subtitles.

* If the correlated phrases have "non-trite" agreement, you have the properly matched video and subtitles, and otherwise not and you may need to replace the video file
* Notice the deltas; if there are huge "rifts" where the delta jumps by 10s or 100s of seconds, the video or subtitles may be flawed and need replacment.
   
## D. When Internal Subtitles Fit Poorly
If the video has poorly fit internal subs (which does happens), run `subshop -fi dos {target}` and choose 'EMBEDDED' from the list; the internal subtitles will be extracted and synced (now as external subtitles).

Adjusted internal subtitles often are good enough; but if not, now you can use `subshop -i redos` to replace those.

## E. When 'subshop' Falls Back to Less Desired Subtitles
If subshop falls back to "undesired" subtitles when trying to replace them, then remove the existing subtitles with: `subshop zap {target}`.
* With the current subtitles out of the way, run whatever command will install the desired subtitles; often that is `subshop -i redos`.
* Note that `subshop` will keep existing subtitles (which it calls the "fallback") if the new subs do not score sufficiently better than the existing.

## F. Manually Adjusting Subtitles
For subtitle/language cases that `subshop` does not handle, (e.g., for English subs and foreign audio), then many players allow shifting (i.e., delaying or advancing the subtitles by a constant shift. See the `subshop delay` subcommand for details.

# Theories of Operation
## Choosing Subtitles to Download
Automatically selecting a good candidate subtitle file to download is a challenged. My experience was that weighted criteria works more accurately than more simplistic strategies, but, of course, not perfectly.

Listed are the download selection criteria, defaults weights, "tag", and brief descriptions.

* `hash-match: 40 ` (Hs) --  video hash matches. You might think this would be a "killer" factor, but (a) hits are few, and (a) when it hits, false positives are common; so the weight is high but just one factor.
* `imdb-match: 20` (Id) --  given if IMDB ID matches;  not as strong a factor as you might think.
* `season-episode-match: 30` (Ep) -- if parsed filename season/episode matches
* `year-match: 20` (Ep) -- if parsed filename year matches
* `title-match: 10` (Tt) -- given if the parsed filename title matches the show name or movie title (after some normaization of case, special characters, etc.)
* `name-match-ceiling: 9` -- given a scaled value depending on the similarity of the video filename to the subtitle filename.
* `hearing-impaired: 2` -- given if marked hearing impaired (for more complete subtitles)
* `duration-ceiling: 40` (Du8,...,Du1) -- assigned a scaled score based how the closeness of the duration of the video and subtitles (allowing for silence during trailing credits). Du8 indicates a high score; when the duration is 25% off or more, the subtitle is credit no duration score.
* `lang-pref: 80` (Ln) -- currently moot since only English is supported; but, if multiple languages are allowed, this score boost for being 1st language specified.

You can change the weights in the  `download-score-params` section of the YAML configuration file.

Here is an example (`subshop -i redos xirtam`) with explanations (btw, the title was altered to avoid search hits on the title):
```
>> OMDb info: The Xirtam (1999) tt0133093 [movie] Poster
>> Filename: The Xirtam 1999 BluRay 720p HEVC AC3 D3FiL3R (1).mkv
>> Duration: 02:16:18
>> Available subtitles:
[1] 132 *2:08:40 "The.Xirtam.1999.BluRay.1080p.x264.DTS-WiKi.ENG.srt" By:Id,Tt,Yr,Hs,Du8
[2] 96 *2:16:13 "The.Xirtam.1999.Bluray.english-sdh.srt" HI By:Id,Tt,Yr,Du8
[3] 96  2:08:40 "The Xirtam 1999 720p BRRip XviD AC3-FLAWL3SS-eng.srt" By:Id,Tt,Yr,Du8
[4] 96  2:08:40 "The Xirtam 1999 720p BRRIP XVID AC3 - 26k.srt" By:Id,Tt,Yr,Du8
[5] 95  2:16:15 "The.Xirtam.1999.REMASTERED.1080p.BluRay.REMUX.AVC...srt" HI By:Id,Tt,Yr,Du8
[6] 95  2:16:16 "The.Xirtam.1999.720p.BrRip.264.YIFY.srt" HI By:Id,Tt,Yr,Du8
[7] 95  2:08:40 "The.Xirtam.1999.720p.BluRay.AC3.x264-AsCo_Track3.srt" By:Id,Tt,Yr,Du8
[8] 95  2:09:30 "The.Xirtam.1999.720p.BluRay.264.YIFY.srt" HI By:Id,Tt,Yr,Du8
[9] 95  2:16:13 "The.Xirtam.1999.1080p.BluRay.x264-CtrlHD.eng-sdh.srt" HI By:Id,Tt,Yr,Du8
[10] 94  2:08:41 "The.Xirtam.1999.REMASTERED.720p.BluRay.X264-AMIABLE.srt" By:Id,Tt,Yr,Du8
[11] 94  2:08:41 "The.Xirtam.1999.REMASTERED.720p.BluRay.X264-AMIABLE.srt" By:Id,Tt,Yr,Du8
[12] 94  2:10:40 "The.Xirtam.1999.HDDVDRip.XviD.AC3.PRoDJi.srt" By:Id,Tt,Yr,Du8
[13] 94  2:08:40 "The.Xirtam.1999.720p.BluRay.264.YIFY.srt" HI By:Id,Tt,Yr,Du8
[14] 93  2:16:16 "The.Xirtam.1999.720p.nHD.x264.AAC.NhaNc3.en.srt" By:Id,Tt,Yr,Du8
[15] 93  2:08:43 "The.Xirtam.1999.720p.BrRip.264.YIFY.srt" HI By:Id,Tt,Yr,Du8
[16] 92  2:08:40 "The.Xirtam.1999.BRRip.XvidHD.720p-NPW.srt" By:Id,Tt,Yr,Du8

 ...Showing choices 1-16 of 61; enter u/d to page up/down
[0] Cancel search
>> Pick (0-61) -OR- <Subt-Srch>/ -OR- <IMDB-Srch>? -OR- ignore!:
```
NOTES:
* For [1], "By:Id,Tt,Yr,HsDu8" means that the score was boosted by matching the IMDB ID / title / year / hash, and matching the duration very well.
    * "132" is the total score.
    * "\*" denotes the subtitle file is already download and in the cache.
* The prompt (i.e, "Pick ...."), allows you to (in this specific case):
    * By entering "0", you cancel the download.
    * By entering "1" to "61", you select a subtitle file to download (notice all are not shown at once),
    * By entering "{phrase}/", you can search for subtitles differently.
    * By entering "{phrase}?", you can search for another IMDB ID match.
    * By entering "8", you can extract the embedded subtitles and sync them.  So, in this case, it was not necessary to download subtitles in the first place (but it was done so as an example.)
    * By entering "d", you can see the next 16 search results. If the results are scoring on several criteria, seeing more than 16 is rarely productive.
    * By entering "u" after entering "d", you can see the previous 16 results.


## Synchronizing Subtitles
The module, `SubFixer.py`, manages the synchronization of subtitles. The steps of synchronizing subtitles at a high level are:

* run `video2srt` or `autosub` to generate "reference" subtitles that are supposedly perfect synced.
* correlate candidate subtitles with the reference subtitles (which is easier said than done because the reference subtitles are typically quite incomplete and error filled).
* run a linear regression on the points of correlated subtitles to determine the offset and slope of the best linear fit, and modify the candidate subtitles appropriately.
* run a segmented linear regression on the correlation points to identify "rifts".  Rifts happen, for example, then the ads are cut differently in the video than the subtitles.  Finding rifts involves finding places in the video where:
    * there is a statistically significant linear fit backward and forwards,
    * where both lines are nearly parallel, and
    * the standard deviation of the sync error is sufficiently improved by fitting two lines rather than fitting one line.
    * then find the most likely discontinuity point in the candidate captions which is difficult because there may be several uncorrelated captions between the two correlation points spanning the rift; errors in picking the caption on each side of the rift are not uncommon but the annoyance is bounded.

Finally, select the "best" choice of subtitles (in order of most preferable to least) from:

* the currently installed subtitles,
* the unadjusted candidate subtitles,
* the linearly adjusted candidate subtitles, and
* the rift adjusted subtitles.

A less preferable choice must be sufficiently better to choose it.
    
# Related and Inspirational Projects
I tried each of the tools below (and many more) before deciding to create yet-another-subtitle too.

## [GitHub - sc0ty/subsync: Subtitle Speech Synchronizer](https://github.com/sc0ty/subsync)
This excellent project is one of the best subtitle synchronizers that I tried; some shortcomings per my experience were:
   * for linux install, requires `snap` which I avoid do its overheads/complications.  Fortunately, there are docker adaptations (e.g.,) [domainvault/subsync - Docker Image | Docker Hub](https://hub.docker.com/r/domainvault/subsync)) which I used successfully w/o installing `snap`.
* it does not cache reference subtitles so every sychronization is costly
* it does not publish fit metrics needed to just judge the quality of the synchronization.
* it only does linear fits (i.e., a single linear regression to find best offset and speed adjustment).

The bottom line is that `subsync` does an admirable job for subtitles that can by synced with a simple linear fit; that meant it was about 90% successful for my video collection.

## [GitHub - kaegi/alass](https://github.com/kaegi/alass)
This excellent project can adjust subtitles with rifts, and it often does a slam-dunk job of doing so.  It is language agnostic which is a huge plus for non-English users. Its shortcomings per my experience:

* when it fails (which was too often), it fails miserably and often messes up the subtitles to an irrepariable state.
* it does not cache reference information so every sychronization is costly
* it does not publish fit metrics needed to just judge the quality of the synchronization; so when it makes subtitles worse, you don't know until you manually check them.

Bottom line is that it works, just not sufficiently well.

## [GitHub - emericg/OpenSubtitlesDownload](https://github.com/emericg/OpenSubtitlesDownload)
This excellent project downloads subtitles from OpenSubtitles.org using the video hash and/or filename to search for subtitles.  Its shortcomings per my experience include:

* both the hash and subtitle search were more unreliable than one might expect; the hash has false positives and many misses; searching for subtitles using the video filename is quite hit-or-miss.
* when problems with OpenSubtitles.org occur (which is very common), there is little indication of exactly why it fail; instead, you are presented with a generic list of possibilities.

Bottom line is that it works, just not sufficiently well. The module, `SubDownloader.py` is a substantially refactored / enhanced version of `OpenSubtitlesDownload`.

## [subnuker · PyPI](https://pypi.org/project/subnuker/)
`subnuker` removes spam and ads from subtitles and generally is very effective.  Its shortcomings per my experience include:

* some the built-in patterns seem oddly specific probably because the "actors" have changed since they were set.
* false positives (i.e., removing "valid" captions) seem to occur mostly in the middle of the video and there is no protection for caption in the middle.

## [GitHub - platelminto/parse-torrent-title](https://github.com/platelminto/parse-torrent-title)
This fine project parses video file names to the "ultimate" finding
every imaginable attribute inferrable from its name.
Its shortcomings per my experience include:
* poor coverage for some fairly common naming conventions including {season}x{episode} tags and various double episode tags.
* very slow due to its overkill for the needs of this project.

## [Super Fast Way to Add SRT Subtitles to Your Movies : PleX](https://www.reddit.com/r/PleX/comments/m8g1km/super_fast_way_to_add_srt_subtitles_to_your_movies/)
Not exactly a project, but the (crude) idea is to combine the steps needed to download, clean, and sync subtitles (with interesting feedback).  Not bad for a few lines of code, but I had greater ambitions.
