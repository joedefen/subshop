# SUBSHOP
Tools to download, remove ads, and synchronize subtitles.

### Purpose
`subshop`, or "Subtitle Workshop", is a set of subtitle tools intended to mostly automate:

* the downloading of subtitles (if needed) for video files,
* synchronizing external subtitles with the audio track, and
* removing ads from the subtitles.

There are some novel features that enhance the user experience including:

* explicitly and intuitively **scoring the subtitle synchronization** so that the user (and tasks) know which subtitles need remediation.
* implementing **both linear and segmented linear adjustments** to subtitles to improve the chances for a good fit.
* **caching "precious" information**, like reference subtitles, so that multiple subtitle sync attempts can be done quickly and efficiently.
* **automation for installing missing or replacing poorly fitting subtitles** at a pace that does not exhaust your subtitle download quota and perseveres through temporary outages.

When necessary and preferred, the tools can be used manually for in-a-hurry situations and/or improving/correcting the automated decisions.

If used in a completely manual mode (or separately automated), you can omit some configuration for searches and automation, specify full video paths to subshop, remove its cached information, etc.  In that case, you simply get the benefit of the download, ad removal, and synchronization features w/o optimizations and automation support.

> NOTE: this was formerly a PyPi.org project also called `subshop`, but for so few users, the maintance was too high.

### Limitations
Current limitations of these tools include:

* only **English** subtitles and audio tracks are supported.
* only **srt** subtitles are supported.
* for best / most automated operation, movies and TV episodes must be organized in a PLEX-like directory structure.
* auxiliary information is stored (mostly) in a "cache" directory, one per video file.
* must run on a modern Linux (or sufficient Linux comparable) operating system.
* Python 3.6 is the bare minimum, but Python 3.8+ is best.
* Python 2.x is required if you choose to use [autosub](https:/github.com/agermanidis/autosub) for voice recognition (rather than the default [VOSK](https://alphacephei.com/vosk/)).

---

---

### Example Run of Downloading and Syncing Subtitles

Here is an annotate example of perhaps the most commonly used `subshop` subcommand. For a video without existing internal or external subtitles, `subshop` is selects and downloads a candidate subtitle file, then checks its fit, and, if needed and possible, adjusts the subtitles for a better fit. *BTW, In this example, the name of show was altered to avoid stray search engine hits.*
```
$ subshop dos gilless girls 1x2

=> Gilless.Girls.S01E02.WEBRip.x264-FGT.mp4 IN /heap/Videos/TV/TryMeTV/Gilless Girls
>> Downloading "Gilless Girls [1x02] -  The Lorelais' First Day at Chilton.srt" [English]

+ video2srt --stream 0:1 -o '/heap/Videos/TV/TryMeTV/Gilless Girls/Gilless.Girls.S01E02.WEBRip.x264-FGT.cache/Gilless.Girls.S01E02.WEBRip.x264-FGT.REFERENCE.srt' '/heap/Videos/TV/TryMeTV/Gilless Girls/Gilless.Girls.S01E02.WEBRip.x264-FGT.mp4'
0....10....20....

------------- OK 

=> Linear fit of unadjusted to REF:  [0:10 to 42:11] y = -2304.0 + -0.00123*x dev: 445 pts: 450
     <<<< Doing linear adjustment ... >>>>
=>                 [0:10 to 42:11] y = -2304.0 + -0.00123*x dev: 445 pts: 450
=> Linear fit of linear-adjusted to REF:  [0:07 to 42:05] y = 0.0 + -0.00000*x dev: 445 pts: 450
     <<<< Looking for rifts ... >>>>
=>                 [0:07 to 11:30] y = -43.0 + 0.00036*x dev: 442 pts: 92
=> 11:36 You're obviously a bright girl, Miss Gilless. <<======= -681ms rift
=>                 [11:37 to 14:55] y = -2515.0 + 0.00293*x dev: 250 pts: 40
=> 14:59 Perfect attendance, 4.0 grade point average. <<======== -412ms rift
=>                 [14:59 to 18:50] y = -2235.0 + 0.00216*x dev: 417 pts: 44
=> 18:53 I already took care of all that, <<==================== 245ms rift
=>                 [18:57 to 22:06] y = 2927.0 + -0.00218*x dev: 387 pts: 53
=> 22:22 They're smaller than the last batch. <<================ -370ms rift
=>                 [22:23 to 27:21] y = -2599.0 + 0.00166*x dev: 403 pts: 66
=> 27:23 "Please come to the desk. Someone needs <<============= -182ms rift
=>                 [27:26 to 42:05] y = -218.0 + 0.00010*x dev: 434 pts: 155
=> Audit rift-adjusted subs
------> Fixing 2 anomalies
err: fix caption overlap: 27:20.823+2.126 Once again, your faithful pooch is here to say: 
    27:22.843+2.625 "Please come to the desk. Someone needs to talk to you."
err: fix caption overlap: 14:57.663+1.332 A Dixie chick. 
    14:58.656+2.026 Perfect attendance, 4.0 grade point average.
=> Linear fit of rift-adjusted to REF:  [0:07 to 42:05] y = -13.0 + 0.00001*x dev: 404 pts: 449
=> PICK linear adjusted subs 445/445/404ms

------------- OK  dev 0.44s pts 450 [PICK linear adjusted subs 445/445/404ms] 

```
Explanation:

* The command, `subshop dos gilless girls 1x2`, means download-and-sync subtitles for Gilless Girls, Season 1, Episode 2.
* `subshop` finds the video file based on the description.
* `subshop` fetches the list of available subtitles from OpenSubtitles.org, picks one that seems to be the best fit, and downloads it.
* `subshop` runs VOSK speech recognition to create a "reference" subtitle file requiring nearly 30s in this case; reference subtitles are too inaccurate to use as "real" subtitles, per se, but reference subtitles are very useful for fix the timing of downloaded, real subtitles.
* `subshop` correlates the reference subtitles to the downloaded subtitles and finds 450 points of where the text seems to agree, and it does a linear fit of the downloaded subs (which results in shifting the subs by about -2304ms and adjusting the speed by 0.123%); after adjustment, the linear fit has an error (i.e., standard deviation or "dev") of 445ms (which is suggested a good fit).
* `subshop` then attempts to find "rifts" (or points of discontinuity probably caused by cutting commercials differently) in the linear fit; it finds 5 rifts (and it fixes overlaps the rift-adjust subs).
* `subshop` determines the error of the rift adjusted subs as 404ms (i.e., a slight improvement).
* `subshop` decides to keep the linear adjusted subs (if rift adjusted subs had been sufficiently better, they would have been chosen), and it places them "next" to the video with a compatible name (not shown).

In this case, the subtitles had a 2.3s error that was corrected with a simple linear adjustment; when rift-adjusted subtitles are selected when they make a big enough improvement to compensate for their sometimes unavoidable, very annoying time adjustment errors at each rift.

After adjustment, these are pretty good fitting subs.  If they were poor fitting subs, you can easily try different ones or (if set up to do so) your automation task would try to improve the fit during its daily runs.

---

---

## Installation
[Installation, Configuration, and Preparation](./docs/ss-install.md) details how to install `subshop` including:

* Obtaining credentials for OpenSubtitles.org and TheMovieDB.org.
* Installing subshop and its python dependencies.
* Installing subshop's non-python dependencies.
* Seeding and updating subshop's YAML configuration file.
* Verifying the installation.
* Optionally, configuring PLEX and creating a daily `cron` job.

## Organizing Your Video Collection

[Video Organization for Subshop](./docs/ss-organization.md) describes in detail the video file tree structure including:

* Your videos files must be organized in a way that is agreeable to PLEX and/or Emby.
* Videos must be named in a way that subshop can parse the name for identification.
* Subshop will "cache" certain files related to subtitles and identification near the videos.


## Using the SUBSHOP Command
`subshop` is a single command with many subcommands.

* [Subshop Common Terms](./docs/ss-common-terms.md) describes in detail the common terms shared by the subcommands including:

    * **subcommand options are consistent**; e.g., "-n" / "--dry-run" means say what would be done rather than doing it.
    * **subcommand targets** are usually either (1) a search phrase for a a video title, OR (2) a set of video files and or folders.
    * **reference subtitles** are very imperfect subtitles created by voice-to-text tools used to synchronize candidate subtitles for use.
    * **subtitle scores** are numbers from 1 (best) to 19 (worst) that judges the accuracy of the the subtitle sync.

* [Subshop Fetching/ Syncing Subs](./docs/ss-fetch-sync-subs.md) describes in detail the commands used to download and synchronize subtitles.  These include:

    * `subshop dos {targets}` -  download-and-sync subtitles for the target videos
    * `subshop redos {target}` - re-download-and-sync subtitles for the target videos presumably to get better synchronization.
    * `subshop sync {target}` - synchronize (yet again) subtitles for the target videos
    * `subshop delay -D{secs} {targets}` - shift the subtitle times for the target videos to effect a manual correction of sync
    * `subshop ref {targets}` - generate the reference subtitles for the target videos
    * `subshop grep {targets}` - find and optional remove subtitles by pattern
    * `subshop imdb {targets}` - view, set, and correct IMDB information for the target videos

* [Subshop Reporting and Status](./docs/ss-status.md) - describes in detail commands show and control the state of subtitles including:

    * `subshop stat {targets}` - show the status of subtitles for the target videos
    * `subshop tvreport` - summarizes the presence/absences of subtitles by TV show and season
    * `subshop anal {targets}` - re-analyzes the goodness of fit of the subtitles for the target videos
    * `subshop ignore {targets}` - put the target videos in an ignore state for getting subs
    * `subshop unignore {targets}` - remove the target videos from the ignore state for getting subs

* [Subshop Maintenance and Support](./docs/ss-support.md) - describe in detail the commands for maintenance and support.

    * `subshop parse {targets}` - checks the parsability of video filenames
    * `subshop search {targets}` - searchs for TV shows and movies
    * `subshop todo {targets}` - creates TODO list for automated maintenance
    * `subshop daily` - performs the daily automation tasks
    * `subshop inst {targets}` - "installs" videos (e.g., in a temporary download area) into its proper place in the video directory tree.
    * `subshop dirs` - show subshop's persistent data directories
    * `subshop tail` - view for the `subshop` log
    * `subshop run {module}` - runner for the exercising the low-level modules.

## Remedies for Poorly Fitting Subtitles
[Remedying Missing/Misfit Subtitles](./docs/ss-remedies.md) provides how to approach the problem of fixing bad and missing subs.

## Theories of Operation

[Theories of Operation](./docs/ss-theory.md) describes how `subshop`

* selects the candidate best subtitles to down
* the strategies used to synchronize subtitles to the video sound track
    
---

---

## Related and Inspirational Projects
We tried each of the tools below (and many more) before deciding to create yet-another-subtitle tool.

## [GitHub - sc0ty/subsync: Subtitle Speech Synchronizer](https://github.com/sc0ty/subsync)
This excellent project is one of the best subtitle synchronizers that I tried; some shortcomings per my experience were:
   * for linux install, requires `snap` which I avoid do its overheads/complications.  Fortunately, there are docker adaptations (e.g.,) [domainvault/subsync - Docker Image | Docker Hub](https://hub.docker.com/r/domainvault/subsync)) which I used successfully w/o installing `snap`.
* it does not cache reference subtitles so every synchronization is costly
* it does not publish fit metrics needed to just judge the quality of the synchronization.
* it only does linear fits (i.e., a single linear regression to find best offset and speed adjustment).

The bottom line is that `subsync` does an admirable job for subtitles that can by synced with a simple linear fit; that meant it was about 90% successful for my video collection.

## [GitHub - kaegi/alass](https://github.com/kaegi/alass)
This excellent project can adjust subtitles with rifts, and it often does a slam-dunk job of doing so.  It is language agnostic which is a huge plus for non-English users. Its shortcomings per my experience:

* when it fails (which was too often), it fails miserably and often messes up the subtitles to an irreparable state.
* it does not cache reference information so every synchronization is costly
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
This fine project parses video file names to the "ultimate" finding every imaginable attribute inferrable from its name.  Its shortcomings, per my experience, include:

* poor coverage for some fairly common naming conventions including {season}x{episode} tags and various double episode tags.
* very slow due to its overkill for the needs of this project.

## [Super Fast Way to Add SRT Subtitles to Your Movies : PleX](https://www.reddit.com/r/PleX/comments/m8g1km/super_fast_way_to_add_srt_subtitles_to_your_movies/)
Not exactly a project, but the (crude) idea is to combine the steps needed to download, clean, and sync subtitles (with interesting feedback).  Not bad for a few lines of code, but I had greater ambitions.