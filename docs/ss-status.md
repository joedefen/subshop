# Subshop Reporting and Status Subcommands

Herein, we describe commands to show and evaluate the current status of subtitle aquisition and synchronization, and controls on it automation.

### subshop stat {targets}  # get basic subtitle status
Shows the summary subtitle information of the targets.

* `-v/--verbose`: shows much detail including all cached information
* `-m/--min-score`: process only subtitles with at least the given minimum score
* `-M/--max-score`: process only subtitles with no more than given maximum score

### subshop tvreport # summarize missing subtitles for TV shows
Create a summary report for TV shows of episodes w/o subtitles.  It may look like:
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

### subshop anal {targets} # analyze the quality of subtitles
Re-analyzes the subtitles. If tuning parameters have changed, you might get
different results.

* `-m/--min-score`: process only subtitles with at least the given minimum score
* `-M/--max-score`: process only subtitles with no more than given maximum score


### subshop ignore {targets} # disable subtitle actions
Sets the state to IGNORE for the video; this will inhibit most sub-command actions on the target except for 'unignore'.

### subshop unignore {targets} # re-enable subtitle actions
Clears the IGNORE state for the video; this enables most sub-command actions on the target.

### subshop zap {targets} # remove external subtitles
Remove external subtitles for the {targets}. Obviously, use with caution since you can easily remove all your subtitles.