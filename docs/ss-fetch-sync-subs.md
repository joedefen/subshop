# SUBSHOP Subcommands for Featching and Syncing Subtitles

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
Re-do the sync of subtitles for the targets (w/o a download) for whatever reason (e.g., changed sync parameters or replaced reference subtitles or reexamine details of the synchronization). The reference subtitles will be regenerated if necessary. Requires (1) an English audio stream, (2) not in IGNORE state, (3) has internal or externals subs.

* `-m/--min-score`: process only subtitles with at least the given minimum score
* `-M/--max-score`: process only subtitles with no more than given maximum score
* `-v/--verbose`: shows the correlated reference/non-reference subtitles and timing differences; if there are many non-trivial text matches, then the video and subtitles are very likely to belong to the same movie or episode; if the timing differences have large discontinuities, there are huge rifts in the video relative to the subtitles.

### subshop delay -D{secs} {targets}  # manually shift subtitle times
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

## subshop ref {targets} # generate reference subtitles
Generates reference subtitles for the given targets ONLY if (1) the target has no reference subtitles, and (2) the target has external subtitles OR has no internal subtitles, (3) there is an English audio stream, and (4) the video is in the "IGNORE" state.

* `-n/--dryrun`: use to verify how many/which reference subtitles you generate.
* `--random`: randomize the targets
* `-q/--quota`: cut off target after the limit
* `--todo`: work down the TODO list (see "todo" subcommand) rather than {targets}
* `-d/--days`: only process videos newer than a given number of days

Note, generating reference subtitles is usually a byproduct of `subshop dos`, but that might be limited by quota or outages and pre-generating the reference subtitles can speed the eventual download-and-sync operation whether done manually or in the backgrond.

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


### subshop imdb {targets} # verify/update IMDB info for videos
Views, sets, and corrects the IMDB information for the TV show or movie. For downloading the correct subtitles automatically, having a correct IMDB association reduces error considerably.

* `-i/--interactive`: shows the IMDB information and gives you opportunity to update it.
* `-n/--dryrun`: use to see whether the IMDB is cached or not.

To generate a list of TV shows / movies w/o cached IMDB info, run:

* `subshop imdb -n | grep -B1 create`

Here is an example of setting IMDB info:
```
<svr binsb> subshop imdb -i spirited away

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