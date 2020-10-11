# Client-side BigBlueButton recordings exporter

This Python script allows you to download BigBlueButton recordings as `.mp4` videos, knowning just the URLs through which the recordings are publicly accessible.

The URL of a recording is of the form:
```
https://$DOMAIN/playback/presentation/2.0/playback.html?meetingId=$MEETING_ID
```
Normally, a recording can be viewed in the BigBlueButton Web player at the previous URL.

## Dependencies
This script makes use of UNIX commands. You should be able to run it on Linux or Mac OS.

In order to make use of this script, you will need to have the following dependencies installed on your system:
- [Docker Engine](https://docs.docker.com/get-docker/)
- [Python Programming Language](https://www.python.org/downloads/)
- [FFmpeg](https://ffmpeg.org/download.html)

Make sure your user has the privileges to run the script.

## Using the script
Clone this repository or download its files. Assuming that:
- all files you can find in this repository are placed in the directory `$SCRIPT_DIRECTORY`;
- the URL of the BigBlueButton recording is `$URL`
- you want your exported video to be placed at `$OUTPUT_FILE_PATH`;
> **NOTE:** `$OUTPUT_FILE_PATH` should end with `.mp4`, since this is the format of the output video, otherwise you may not be able to view the exported video.

you just have to run the following command:

```
python3 $SCRIPT_DIRECTORY/bbb_recordings_exporter.py $URL $OUTPUT_FILE_PATH
```

You will have to wait an amount of time at least equal to the recording duration.

At the end of the processing, the exported video, in `.mp4` format, will be available at `$OUTPUT_FILE_PATH`.

## Functioning

This Python script processes the BigBlueButton recording as follows:
1. using [a dockerized version of Selenium WebDriver](https://github.com/elgalu/docker-selenium), it plays the whole video and captures it, ignoring the webcam window (the absence of the webcam ensures good performances while capturing the video);
2. it downloads the webcam video file directly from the BigBlueButton server on which the recording is hosted;
3. it merges the two videos obtained in the previous steps by making use of FFmpeg.

## Special thanks 
I thank [trahay](https://github.com/trahay), whose [bbb-downloader](https://github.com/trahay/bbb-downloader) really inspired me to carry out this project.

> **DISCLAIMER:**
This software uses BigBlueButton and is not endorsed or certified by BigBlueButton Inc. BigBlueButton and the BigBlueButton Logo are trademarks of BigBlueButton Inc.