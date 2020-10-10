import os
import subprocess
import logging
import urllib.request
import time
import datetime

from tqdm import trange

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def execute_shell_cmd(shell_cmd):
    shell_stream = os.popen(shell_cmd)
    return shell_stream.read()


class BBB_recording:
    url = None
    tmp_directory = None
    output_file = None

    webcam_file = None
    presentation_file = None
    trimmed_presentation_file = None

    duration = None
    wait = None

    width = None
    height = None

    def __init__(self, url, tmp_directory, output_file):
        self.url = url
        self.tmp_directory = tmp_directory
        self.output_file = output_file

        try:
            os.mkdir(tmp_directory)
        except OSError as mkdir_exception:
            raise mkdir_exception

    def get_webcam(self):
        domain = (self.url.split("/playback/"))[0]
        meeting_id = (self.url.split("?meetingId="))[1]
        extensions_to_try = [".mp4", ".webm"]

        for extension in extensions_to_try:
            webcam_url = domain + "/presentation/" + \
                meeting_id + "/video/webcams" + extension
            webcam_request = urllib.request.Request(webcam_url, method='HEAD')

            try:
                urllib.request.urlopen(webcam_request)
            except:
                logging.info("Webcam video was not at " + webcam_url)
            else:
                logging.info("Webcam video was at " + webcam_url)
                self.webcam_file = self.tmp_directory + '/webcam' + extension
                urllib.request.urlretrieve(webcam_url, self.webcam_file)
                return
        raise Exception("Error while retrieving webcam video")

    def set_duration(self):
        shell_cmd = ['ffprobe',
                     '-i', self.webcam_file,
                     '-show_entries', 'format=duration',
                     '-v', 'quiet',
                     '-of', 'csv=%s' % ("p=0")]
        self.duration = round(float(subprocess.check_output(shell_cmd)))
        print("The playback lasts " +
              str(datetime.timedelta(seconds=self.duration)))

    def get_presentation(self, width, height):
        self.width = width
        self.height = height

        # Creating Selenium container
        selenium_container_name = 'selenium_bbb_recording_' + str(time.time())

        shell_cmd = 'docker run --rm -d' + \
            ' --name=' + selenium_container_name + \
            ' -P --expose 24444' + \
            ' --shm-size=4g -e VNC_PASSWORD=hola' + \
            ' -e VIDEO=true' + \
            ' -e SCREEN_WIDTH=' + str(width) + ' -e SCREEN_HEIGHT=' + str(height) + \
            ' -e FFMPEG_DRAW_MOUSE=0' + \
            ' elgalu/selenium'
        execute_shell_cmd(shell_cmd)
        print('Selenium Docker container created')

        # Getting Selenium container port
        shell_cmd = "docker inspect" + \
            " --format='{{(index (index .NetworkSettings.Ports \"24444/tcp\") 0).HostPort}}' " + \
            selenium_container_name
        selenium_container_port = execute_shell_cmd(
            shell_cmd).replace('\n', '')

        # Starting Selenium container
        shell_cmd = 'docker exec ' + \
            selenium_container_name + \
            ' wait_all_done 30s'
        execute_shell_cmd(shell_cmd)
        print('Selenium Docker container started')

        # Timestamp at recording start
        wait_start = time.time()

        # Recording
        driver = webdriver.Remote(
            command_executor='http://localhost:' + selenium_container_port + '/wd/hub',
            desired_capabilities=DesiredCapabilities.FIREFOX)
        driver.maximize_window()
        driver.get(self.url)

        try:
            play_button = WebDriverWait(driver, 60).until(
                EC.visibility_of_element_located(
                    (By.CLASS_NAME, 'acorn-play-button'))
            )
        except:
            raise Exception('Failed to start the playback')
        finally:
            js_script = '(document.getElementsByClassName(\'webcam\'))[0].remove()'
            driver.execute_script(js_script)
            play_button.click()

            # Wait 2 seconds for the start of the playback
            time.sleep(2)

            # Timestamp at playback start
            wait_end = time.time()

            # Seconds between the start of the recording and the start of the playback
            self.wait = round(wait_end - wait_start)
            print('The playback started ' + str(self.wait) +
                  ' seconds after the beginning of the recording')

            # Wait until the end of the playback
            # time.sleep(self.duration)
            print('\nRecording the playback...')
            for i in trange(self.duration):
                time.sleep(1)

            print('\nSaving the recording...')

            # Stopping the recording
            shell_cmd = 'docker exec ' + \
                selenium_container_name + \
                ' stop-video'
            execute_shell_cmd(shell_cmd)
            driver.quit()

        # Copying Selenium recording in the tmp directory
        shell_cmd = 'docker cp ' + \
            selenium_container_name + ':/videos/. ' + \
            self.tmp_directory
        execute_shell_cmd(shell_cmd)
        print('Recording saved')

        # Deleting Selenium container
        shell_cmd = 'docker stop ' + \
            selenium_container_name
        execute_shell_cmd(shell_cmd)
        print('Selenium Docker container deleted')

        # Getting presentation file path
        shell_cmd = 'ls -1 ' + self.tmp_directory + '/vid*.mp4'
        self.presentation_file = execute_shell_cmd(shell_cmd).replace('\n', '')

    def export(self,
               upper_margin, lower_margin,
               webcam_width, webcam_height,
               webcam_right_margin, webcam_lower_margin):
        output_height = self.height - upper_margin - lower_margin
        output_width = self.width

        x = 0
        y = upper_margin

        self.trimmed_presentation_file = self.tmp_directory + '/trimmed_presentation.mp4'

        shell_cmd = ['ffmpeg',
                     '-ss', str(self.wait),
                     '-i', self.presentation_file,
                     '-c', 'copy',
                     '-loglevel', 'warning',
                     self.trimmed_presentation_file]
        subprocess.call(shell_cmd)

        shell_cmd = ['ffmpeg',
                     '-i', self.webcam_file,
                     '-i', self.trimmed_presentation_file,
                     '-filter_complex',
                     '[1] crop=' + str(output_width) + ':' + str(output_height) + ':' + str(x) + ':' + str(y) + '[c-p];' +
                     '[0] scale=' + str(webcam_width) + ':' + str(webcam_height) + '[w];' +
                     '[c-p][w] overlay=main_w-overlay_w-' +
                     str(webcam_right_margin) + ':main_h-overlay_h-' +
                     str(webcam_lower_margin),
                     '-loglevel', 'warning',
                     '-stats',
                     self.output_file]
        print('\nExporting the recording...')
        print(subprocess.check_output(shell_cmd).decode('utf-8'))
        print('Recording export completed.\nThe video is available at ' + self.output_file)
