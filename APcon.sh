#!/bin/sh
#

iw dev wlan0 station dump | grep wlan0 | wc -l
