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

Here is an example (`subshop redos -i xirtam`) with explanations (btw, the title was altered to avoid search hits on the title):
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