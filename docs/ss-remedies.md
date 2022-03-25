# Remedying Missing/Misfit Subtitles
If the sync is lousy or the summary results are concerning, here are some possible actions.

## A. When You Need Better Fitting Subtitles
It is not uncommon to need better fitting subtitles. You can try:

* `subshop redos -i {target}` to redress particular video files.
* `subshop defer-redos -T` to redress the deferred problem cases.

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

If still more clues are needed, especially if the point count is low, re-run the sync in verbose mode: `subshop sync -v {target}`. This shows the correlations between the installed and reference subtitles.

* If the correlated phrases have "non-trite" agreement, you have the properly matched video and subtitles, and otherwise not and you may need to replace the video file
* Notice the deltas; if there are huge "rifts" where the delta jumps by 10s or 100s of seconds, the video or subtitles may be flawed and need replacment.
   
## D. When Internal Subtitles Fit Poorly
If the video has poorly fit internal subs (which does happens), run `subshop dos -fi {target}` and choose 'EMBEDDED' from the list; the internal subtitles will be extracted and synced (now as external subtitles).

Adjusted internal subtitles often are good enough; but if not, now you can use `subshop redos -i` to replace those.

## E. When 'subshop' Falls Back to Less Desired Subtitles
If subshop falls back to "undesired" subtitles when trying to replace them, then remove the existing subtitles with: `subshop zap {target}`.
* With the current subtitles out of the way, run whatever command will install the desired subtitles; often that is `subshop redos -i`.
* Note that `subshop` will keep existing subtitles (which it calls the "fallback") if the new subs do not score sufficiently better than the existing.

## F. When Subtitles Need a Manual Time Shift
For subtitle/language cases that `subshop` does not handle, (e.g., foreign audio with English subs), then many players allow shifting (i.e., delaying or advancing the subtitles by a constant shift). Using the best shift value that you can determine, apply that value for a permanent fix with `subshopt delay`.  See the `subshop delay` subcommand for details.

## G. When There are too Many Annoying Ads
If your ad filters are failing to remove annoying ads, then:

* run `subshop grep -g '{get-rid-of-me-pattern}'` and ensure there are few or no false positives.
* edit `subshop.yaml` and add the pattern to either the

    * `limited-regexes` section if matches only occurs in the first or last two minutes.
    * `global-regexes` section if matches are not restrict the the first and last two minutes.

* run `subshop grep -G` to test your configuration, ensuring there are few or no false positives.
* run `subshop grep -fG` to purge the newly detected subtitles.