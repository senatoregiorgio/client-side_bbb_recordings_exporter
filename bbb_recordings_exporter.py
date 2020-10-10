import os
import sys
import shutil

from BBB_recording import BBB_recording

print('\n--------------------\n')

cwd = os.getcwd()
tmp_directory = cwd + '/tmp'
recording = BBB_recording(sys.argv[1], tmp_directory, sys.argv[2])

recording.get_webcam()
recording.set_duration()
recording.get_presentation(1920, 1310)
recording.export(144, 86, 540, 405, 50, 8)

shutil.rmtree(tmp_directory)

print('\n--------------------\n')
