#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cv2
import numpy as np

#dummy function that does nothing
def dummy(value):
    pass

# create teh UI window (window and trackbars)
cv2.namedWindow('app')

# arguments: TrackbarName, WindowName, value (initial value), count (max value), contrast, onChange event handler 
cv2.createTrackbar('Contrast', 'app', 1, 100, dummy)
cv2.createTrackbar('Brightness', 'app', 50, 100, dummy)
cv2.createTrackbar('Filter', 'app', 0, 1, dummy)  # TODO: update max value to number of filters
cv2.createTrackbar('Greyscale', 'app', 0, 1, dummy) # this becomes a switch because of 0 and 1. Boolean type




# Main UI loop






# wait indefinitely, remove this line!
cv2.waitKey(0)

# window cleanup
cv2.destroyAllWindows()