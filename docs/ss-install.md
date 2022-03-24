# Installation, Configuration, and Preparation

## 1. Obtain the Required Web Credentials
You are expected to obtain:

* an [OpenSubtitles.org](https://www.opensubtitles.org) account and know your username and password; this allows for 200 subtitle downloads per day.
* [The Movie Database API](https://developers.themoviedb.org/3/getting-started/introduction) key;  see the instructions on the linked page.
* (optional) your Plex server URL and token;
    * typically, "http:/localhost:32400" works for PLEX
    * to get the token, see [Finding an authentication token / X-Plex-Token | Plex Support](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)

NOTES:

* OpenSubtitles.org is fairly unreliable (e.g., you might find it down 10% of the day).
    * `subshop` attempts to use its unreliable/stingy resources efficiently;  the cache files are an important part of its strategy.
    * By default, `subshop` tracks your downloads and allows 160 downloads/day for automated downloads which leaves 40/day for manual downloads.
    * Doing most of your downloads as automated, background tasks removes most of the agony of opensubtitles.org's downtime.
* If you paid for an OpenSubtitles.org VIP account, you are allowed 1000 downloads per day.
    * With a quota of 1000, you match wish to tweak settings and options to use more than the 200 that `subshop` assumes if you have a large backlog.
* PLEX is used very narrowly (i.e., for searching); if you have a large collection and/or very limited CPU/RAM resources, you can configure `subshop` to use PLEX for its searches which, for some installs, reduces searches for videos from, say, 10 minutes to nearly instantaneous.

### 2. Install subshop and its Python Dependencies
First, clone the project into, say, your home directory:
```
    $ cd; git clone https://github.com/joedefen/subshop.git
```
Then decide whether to do a non-virtualenv or virtualenv install; prefer virtualenv especially if just kicking the tires. For **non-virtualenv** install:
```
    $ cd subshop; pip3 install . --user 
```
Or for a **virtualenv** install:
```
    $ cd subshop
    $ python3 -m venv .venv
    $ source .venv/bin/activate
    $ pip3 install .
        # run tests and use as described within the virtualenv only
    # deactivate # disable virtualenv
    $ rm -rf .venv # cleanup virtualenv to purge subshop
```

### 3. Install subshop's Non-Python Dependencies
Install the non-python dependencies (e.g., `ffmpeg`, `ffprobe`, and the [VOSK Model](https://alphacephei.com/vosk/models)).
```
    $ subshop-sys-deps
```
NOTE: `subshop-sys-deps` will not work for every Linux variant, and you may need to vvary it logic for your system.  If required, copy `subshop-sys-deps` and modify to suit or manually apply its intent.

### 4. Seed Your Configuration File
As a quick test of your install and to create the default configuration file, run `subshop dirs`; this shows the folders that `subshop` uses to store persistent data and it creates the default configuration file (which always requires adjustment).

### 5. Configure subshop
The configuration is stored in `subshop.yaml`, and, by default, in the `~/.cache/subshop/` folder.

You'll need to edit `subshop.py` and:

* at least, change the `YOUR-{something}` values; use the comments as hints on what is needed.
* review all other values and ensure the defaults seem desirable for you.

>**Tip**: If you use `vim`, you might add this your `.vimrc` for a consistent experience with the default YAML file:
>
>* `autocmd FileType yaml setlocal ts=2 sts=2 sw=2 expandtab`
    
The essential configuration to update within `subshop.py` is:
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

* The plex-url-token is needed if you wish to search for video files using Plex vs the built-in search;  the bigger and slower your disk, the more likely Plex will be faster (and sometimes fantastically faster).  And, the Plex searches are "smarter". Also, configure
    * `search-using-plex` to true if you wish that default.
    * `plex-path-adj` appropriately if plex's view of the file system disagrees with the local view (and you are using Plex for searches).

>**Tip**: Avoid making changes to the YAML file w/o the ability to back out errors quickly can certainly. For example,
>
>* after making/writing only a few changes to `subshop.yaml`, **check** the YAML syntax by staying in the editor and running `subshop run ConfigSubshop` in a subshell or separate terminal window.
>* then iteratively until done, make a few more changes, write, check, and repair.

Beware that your `subshop.yaml` will not load if:

* there are YAML syntax errors, or
* the expected basic type of a parameter is incorrect (e.g., you change a string parameter to a numeric type).

## 6. Verify the Installation
After install, it is advisable to ensure a working setup and make adjustments.  Here are some commands to try.

* `subshop dirs`:  dumps the persistent data folder locations (if the configuration is loadable).
* `subshop parse {video-folder}`:  parses the video filenames in the given folder and reports the those that may be problematic for automation (i.e., TV episodes w/o parsed season/episode numbers and movies w/o a parsed year). Running this w/o arguments (i.e., on your whole collection) might indicate ambiguities worth resolving before creating the cache directories).
* `subshop stat {video-folder}`:  dumps the status of the videos in the given folder. With no arguments, it will run on your entire collection; depending on the size of your collection, the first run may be much slower than later run because `ffprobe` information will be cached for subsequent runs.
* `subshop dos {subless-video-file}`: given a video file w/o internal or external subtitles, tries to download and sync subtitles. This should test that your credentials for OpenSubtitles.org and TheMovieDatabase.com are working, that your voice recognition is working, etc.
* `subshop redos -i {video-file-with-external-subs}`:  interatively, attempts to download and sync replacement subtitles.  You are given a chance to fix a incorrect IMDB identification, select an alternative subtitle to try, and after synchronization, try again on move on.
* `subshop sync {video-file-with-external-subs}`: run the synchronization logid on the given video and its subtitles, make adjustments, and report the goodness of fit.
* `subshop todo`: creates various TODO lists for automating process of getting will fitted subtitles.  Depending on the size of collection, this may take quite a while. Similar to the `subshop stat` trial above, you can pass in a {video-folder} to limit the scope of the TODO lists and cut the time for the initial trial.

---

---

## Optional: Install autosub
If you are running on a system with limited resources for voice recognition, then it may be more practical to use [autosub](https:/github.com/agermanidis/autosub). To to so:

* follow the `autosub` install procedure (note it uses python2/pip2).
* in `subshop.yaml`, change the `reference-tool` to `autosub` (rather than the included `video2srt` script).

Using `video2srt` is the preferred configuration. On a modern, typical desktop/server, voice recognition requires about 1s per minute of video (using, say, 6 threads).  If running signficantly longer than that, then `autosub` is likely preferrable.

## Optional: Automating the Download and Synchronization of Subtitles
You may wish to add a daily cron job defined in the configuration; the default (or current if modified) is shown by running `subshop daily -n`.

The default "daily" job includes these commands:

* `subshop todo`: creates TODO lists for automation; it limits the size of each.
* `subshop dos --todo`: performs download-and-sync on videos w/o subtitles that are on its TODO list.
* `subshop redos --todo`: performs download-and-sync on videos with misfit subtitles that are on its TODO list.
* `subshop ref --todo`: creates "reference" subtitles for videos w/o substitles or reference subtitles.  Having the reference subtitles speeds subsequent manual or automated  subtitle operations.