# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import time
import psutil
from hurry.filesize import size, iec
from subprocess import PIPE, Popen
from threading import Thread

import Adafruit_Nokia_LCD as LCD
import Adafruit_GPIO.SPI as SPI
import RPi.GPIO as GPIO

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

# Raspberry Pi hardware SPI config:
# DC = 23
# RST = 24
# SPI_PORT = 0
# SPI_DEVICE = 0

# Raspberry Pi software SPI config:
SCLK = 17
DIN = 18
DC = 27
RST = 23
CS = 22
BOT =21

# Beaglebone Black hardware SPI config:
# DC = 'P9_15'
# RST = 'P9_12'
# SPI_PORT = 1
# SPI_DEVICE = 0

# Beaglebone Black software SPI config:
# DC = 'P9_15'
# RST = 'P9_12'
# SCLK = 'P8_7'
# DIN = 'P8_9'
# CS = 'P8_11'


# Load default font.
#font = ImageFont.load_default()
font = ImageFont.truetype("/root/sysinfo/ProggyTiny.ttf", 16)
big_font = ImageFont.truetype("/root/sysinfo/ProggyTiny.ttf", 32)


# Hardware SPI usage:
# disp = LCD.PCD8544(DC, RST, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE, max_speed_hz=4000000))

# Software SPI usage (defaults to bit-bang SPI interface):
disp = LCD.PCD8544(DC, RST, SCLK, DIN, CS)

# Initialize library.
disp.begin(contrast=52, bias=4)



def get_cpu_temperature():
	process = Popen(['vcgencmd', 'measure_temp'], stdout=PIPE)
	output, _error = process.communicate()
	return float(output[output.index('=') + 1:output.rindex("'")])

def get_con_num():
	process = Popen(['/root/sysinfo/APcon.sh'], stdout=PIPE)
	output, _error = process.communicate()
	return output


net_sp = psutil.net_io_counters(pernic=True)['eth0'] 
tot = (net_sp.bytes_sent, net_sp.bytes_recv)
t1 = time.time()
del net_sp

def draw_system_info(draw):
	global tot, t1
	t0 = t1
	last_tot = tot
	net_sp = psutil.net_io_counters(pernic=True)['eth0']
	t1 = time.time()
	tot = (net_sp.bytes_sent, net_sp.bytes_recv)
	ul, dl = [(now - last) / (t1 - t0) for now, last in zip(tot, last_tot)]
	draw.text((0,0),  'CPU '+str(psutil.cpu_percent(interval=1))+'%', font=font)
	draw.text((0,8),  'RAM '+str(psutil.virtual_memory().percent)+'%', font=font)
	draw.text((0,16), 'CPU TMP '+ str(get_cpu_temperature()) + '\'C', font=font)
	draw.text((0,24), 'UL:'+size(ul, system=iec)+'B/s', font=font)
	draw.text((0,32), 'DL:'+size(dl, system=iec)+'B/s', font=font)
	draw.text((0,40), str(get_con_num()).strip(' \t\n\r') + ' WIFI Con.', font=font)
	return draw

def draw_date(draw):
	t = time
	draw.text((11,8), t.strftime('%Y/%m/%d'), font=font)
	draw.text((17,16), t.strftime('%H:%M:%S'), font=font)
	draw.text((23,24), t.strftime('%a'), font=big_font)
	del t
	return draw

class bgdraw:
	def __init__(self):
		self._running = True

	def terminate(self):
		self._running = False

	BUTTON_PRESS = 1

	def run(self):

		while 1 and self._running:
			# Draw a white filled box to clear the image.
			image = Image.new('1', (LCD.LCDWIDTH, LCD.LCDHEIGHT))
			draw = ImageDraw.Draw(image)
			draw.rectangle((0,0,LCD.LCDWIDTH,LCD.LCDHEIGHT), outline=255, fill=255)
			# Write some text.
			if (self.BUTTON_PRESS % 2):
				draw = draw_system_info(draw)
			else:
				draw = draw_date(draw)
	
			# Display image.
			disp.image(image)
			disp.display()
			time.sleep(0.25)

def main():
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(BOT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	linput_state = 1
	# Clear display.
	disp.clear()
	disp.display()

	# Create blank image for drawing.
	# Make sure to create image with mode '1' for 1-bit color.

	image = Image.new('1', (LCD.LCDWIDTH, LCD.LCDHEIGHT))
	# Get drawing object to draw on image.
	draw = ImageDraw.Draw(image)

	# Draw a white filled box to clear the image.
	draw.rectangle((0,0,LCD.LCDWIDTH,LCD.LCDHEIGHT), outline=255, fill=255)

	bitmap = Image.open('/root/sysinfo/rasp_logo.png')
	image.paste(bitmap, (0, 0)+ bitmap.size)
	disp.image(image)
	disp.display()
	time.sleep(3)
	del bitmap

	d = bgdraw()
	t = Thread(target=d.run)
	t.start()
	BTP = 0

	while 1:
		input_state = GPIO.input(BOT)
		if input_state == 0 and linput_state != input_state:
			linput_state = input_state
			d.terminate()
			t.join()
			d = bgdraw()
			d.BUTTON_PRESS = BTP
			t = Thread(target=d.run)
			t.start()
			BTP = ( BTP + 1 ) % 2
		else:
			if (input_state == 0):
				linput_state = 0
			else:
				linput_state = 1
		time.sleep(0.1)

if __name__ == '__main__':
	main()
