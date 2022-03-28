# SUBSHOP Maintenace and Support Subcommands

### subshop parse {targets} # check parsability of video filenames
Used to check the parsing accuracy of your video files; i.e.,

* for TV episodes, `subshop` should be able to parse the show name, the season and the episode number.
* for movies, `shopshop` should be able to parse the title and year.

*It not necessary that **EVERY** video file is parsable*, but unparseable videos will impair both automated and manual download tasks. Less "fits-the-pattern" episodes (e.g., "special" episodes, double episodes, etc.) are problematic no matter how named.  You can decide to rename parsing exceptions or not.

* `-v/--verbose`: shows how every target is parsed; by default, only likely errors are shown.

### subshop search {targets} # search for TV shows and/or movies
Shows a "search" result meaning:
* tvshow folders, and
* movie video files.

This command requires a search phrase built from the {targets}; for this subcommand {targets} cannot be files/folders and at least one term is required.

If PLEX is required, you may wish to compare/time searches with and without Plex (i.e., `-p` and `-P`).  Also, this command is handy if you wish to know where certain media is stored.

The search results are usually fairly similar **unless `subshop` and PLEX do NOT search the same folders; to use PLEX, ensure they agree.**

Search times will depend on many factors; but, the slower your disk performance, the more likely that PLEX will perform better comparatively.

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
* `-n/--dryrun`: use to verify how many/which subtitles you would remove.

### subshop daily # automation support
Runs a set of commands typically run as `cron` job.  Use the configuration to alter the default command and elaborate the PATH if needed.

Hints:
* Use `subshop daily -n` to verify your commands.
* Use `crontab -e` is set you cronjob to run daily (typically).
* Since the cronjob prevents running manual `subshop` commands and may run for an extened peroid of time, choose a time that will not often interfere with manual use.


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
`subshop` duplicates most of what it prints to its log file(s).
The `tail` sub-command will run `less -F` on the current and previous log file
(there are two files in the "rotation"). NOTE (as a `less -F` quickstart):

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
