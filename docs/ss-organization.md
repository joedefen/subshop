# Video Organization for Subshop
Herein we describe:

* the expected organization of your video collection.
* naming conventions for video files
* the cached files that subshop creates to support substitles and their maintenance.

## File and Folder Organization Overview
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
    Movies for Mom/ # there can be many movie group folders
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

## Video File Naming Conventions
Video filenames should be "parsable" by SubShop (see `subshop parse` subcommand) meaning:

*  for TV episodes, `subshop` can parse the show name, season number, and episode number, and
*  for movies, `subshop` can parse the title and year.
    * if the year is not present, `subshop` may work well.
    * if the year is wrong, `subshop` likely will not work well.
    
`subshop` uses its own parser, `VideoParser.py` to parse the names. Within the script, you can verify what is likely to work and what is not by looking for:

* `regexes`: examine the regular expressions and comments
* `tests_yaml`: look at the tests (mostly hard cases) and the parsing results; notice that a few cases near the end are "failures".

Anyhow, we advise running `subshop parse` on your entire collection, and, if you wish `subshop` to work well, fix its complaints (although movies w/o the year are more optional than unparsable tv episodes numbers).

## Description/Rationale for the Cached Files
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
