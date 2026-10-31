#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cv2
import numpy as np

#dummy function that does nothing
def dummy(value):
    pass


# read in an image, make a grayscale copy
color_original = cv2.imread('../../resources/test_image.jpg')
gray_original = cv2.cvtColor(color_original, cv2.COLOR_BGR2GRAY)



# create teh UI window (window and trackbars)
cv2.namedWindow('app')

# arguments: TrackbarName, WindowName, value (initial value), count (max value), contrast, onChange event handler 
cv2.createTrackbar('Contrast', 'app', 1, 100, dummy)
cv2.createTrackbar('Brightness', 'app', 50, 100, dummy)
cv2.createTrackbar('Filter', 'app', 0, 1, dummy)  # TODO: update max value to number of filters
cv2.createTrackbar('Greyscale', 'app', 0, 1, dummy) # this becomes a switch because of 0 and 1. Boolean type




# Main UI loop

while True:
    #TODO read all of the trackbar values
    
    grayscale = cv2.getTrackbarPos('Greyscale', 'app')
    contrast = cv2.getTrackbarPos('Contrast', 'app')
    brightness = cv2.getTrackbarPos('Brightness', 'app')
    #TODO: apply the filters
    #TODO: apply the brightness and contrast
    
    color_modified = cv2.addWeighted(color_original, contrast, np.zeros_like(color_original), 0, brightness - 50)
    gray_modified = cv2.addWeighted(gray_original, contrast, np.zeros_like(gray_original), 0, brightness - 50)
    
    # wait for key press (100 milliseconds)
    key = cv2.waitKey(100)
    
    # if key equals 'q' would be ideal but instead I need integer
    if key == ord('q'):
        break
    elif key == ord('s'):
        #TODO: save image
        pass
    
    # Show the image
    if grayscale == 0:
        
        cv2.imshow('app', color_modified)
    else:
        cv2.imshow('app', gray_modified)


# window cleanup
cv2.destroyAllWindows()