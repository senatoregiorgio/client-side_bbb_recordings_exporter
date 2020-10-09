import sys
import os

from BBB_recording import BBB_recording

cwd = os.getcwd()
tmp_directory = cwd + '/tmp'
recording = BBB_recording(sys.argv[1], tmp_directory, sys.argv[2])

recording.get_webcam(tmp_directory)
recording.set_duration()
recording.get_presentation(1920, 1340)
recording.export(174, 86, 540, 405)
