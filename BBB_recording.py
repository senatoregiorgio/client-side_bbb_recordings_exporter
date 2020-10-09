import os
import urllib.request
import subprocess
import time

from tqdm import tqdm

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
        except OSError:
            print('Creation of the temporary directory failed')
        else:
            print('Temporary directory created at ' + tmp_directory)

    def get_webcam(self, tmp_directory):
        domain = (self.url.split("/playback/"))[0]
        meeting_id = (self.url.split("?meetingId="))[1]

        extensions_to_try = [".mp4", ".webm"]
        video_exists = False

        for extension in extensions_to_try:
            webcam_url = domain + "/presentation/" + \
                meeting_id + "/video/webcams" + extension
            webcam_request = urllib.request.Request(webcam_url, method='HEAD')
            try:
                urllib.request.urlopen(webcam_request)
            except:
                print("Webcam video was NOT at " + webcam_url)
            else:
                video_exists = True
                urllib.request.urlretrieve(
                    webcam_url, tmp_directory + "/webcam" + extension)
                self.webcam_file = self.tmp_directory + '/webcam' + extension
                print("Webcam video was at " + webcam_url)

        if video_exists == False:
            print("Error while retrieving webcam video")

    def set_duration(self):
        shell_cmd = ['ffprobe', '-i', self.webcam_file,
                     '-show_entries', 'format=duration',
                     '-v', 'quiet',
                     '-of', 'csv=%s'
                     % ("p=0")]
        self.duration = round(float(subprocess.check_output(shell_cmd)))
        print("The recording lasts " + str(self.duration) + ' seconds')

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
        # + ' -e FFMPEG_FRAME_RATE=15' + \
        print(execute_shell_cmd(shell_cmd))

        # Getting Selenium container port
        shell_cmd = "docker inspect" + \
            " --format='{{(index (index .NetworkSettings.Ports \"24444/tcp\") 0).HostPort}}' " + \
            selenium_container_name
        selenium_container_port = (execute_shell_cmd(shell_cmd))[:-1]
        print(selenium_container_port)

        # Starting Selenium container
        shell_cmd = 'docker exec ' + \
            selenium_container_name + \
            ' wait_all_done 30s'
        print(execute_shell_cmd(shell_cmd))

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
        finally:
            print('Trovato pulsante!')
            js_script = '(document.getElementsByClassName(\'webcam\'))[0].remove()'
            driver.execute_script(js_script)
            play_button.click()

            # Timestamp at playback start
            wait_end = time.time()
            self.wait = round(wait_end - wait_start)
            print('The play button appeared after ' +
                  str(self.wait) + ' seconds')

            time.sleep(self.duration + 2)

            # Stop recording
            shell_cmd = 'docker exec ' + \
                selenium_container_name + \
                ' stop-video'
            print(execute_shell_cmd(shell_cmd))

            driver.quit()

        # Copying Selenium recording in tmp directory
        shell_cmd = 'docker cp ' + \
            selenium_container_name + ':/videos/. ' + \
            self.tmp_directory
        print(execute_shell_cmd(shell_cmd))

        # Deleting Selenium container
        shell_cmd = 'docker stop ' + \
            selenium_container_name
        print(execute_shell_cmd(shell_cmd))

        # Getting presentation file path
        shell_cmd = 'ls -1 ' + self.tmp_directory + '/vid*.mp4'
        self.presentation_file = execute_shell_cmd(shell_cmd).replace('\n', '')
        print(self.presentation_file)

    def export(self, upper_margin, lower_margin, webcam_width, webcam_height):
        output_height = self.height - upper_margin - lower_margin
        output_width = self.width

        x = 0
        y = upper_margin

        self.trimmed_presentation_file = self.tmp_directory + '/trimmed_presentation.mp4'

        shell_cmd = ['ffmpeg',
                     '-ss', str(self.wait + 2),
                     '-i', self.presentation_file,
                     '-c', 'copy',
                     self.trimmed_presentation_file]
        print(subprocess.check_output(shell_cmd))

        shell_cmd = ['ffmpeg',
                     '-i', self.webcam_file,
                     '-i', self.trimmed_presentation_file,
                     '-filter_complex',
                     '[1] crop=' + str(output_width) + ':' + str(output_height) + ':' + str(x) + ':' + str(y) + ' [c-p];' +
                     '[0] scale=' + str(webcam_width) + ':' + str(webcam_height) + ' [w];' +
                     '[c-p][w] overlay=main_w-overlay_w-50:main_h-overlay_h-8',
                     self.output_file]
        print(subprocess.check_output(shell_cmd))
