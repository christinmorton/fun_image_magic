#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cv2
import numpy as np

#dummy function that does nothing
def dummy(value):
    pass


# define convolution kernels
identity_kernel = np.array([[0,0,0], [0,1,0], [0,0,0]])
sharpen_kernel = np.array([[0,-1,0], [-1,5,-1], [0,-1,0]])
gaussian_kernel1 = cv2.getGaussianKernel(3, 0)
gaussian_kernel2 = cv2.getGaussianKernel(5, 0)
box_kernel = np.array([[1,1,1], [1,1,1], [1,1,1]], np.float32) / 9.0
# (1 + 2 + 3 + 4 + 5) / 5 = 1 * 1/5 + 2 * 1/5 + 3 * 1/5 + 4 * 1/5 + 5 * 1/5 

kernels = [identity_kernel, sharpen_kernel, gaussian_kernel1, gaussian_kernel2, box_kernel]

# read in an image, make a grayscale copy
color_original = cv2.imread('../../resources/test_image.jpg')
gray_original = cv2.cvtColor(color_original, cv2.COLOR_BGR2GRAY)



# create teh UI window (window and trackbars)
cv2.namedWindow('app')

# arguments: TrackbarName, WindowName, value (initial value), count (max value), contrast, onChange event handler 
cv2.createTrackbar('Contrast', 'app', 1, 100, dummy)
cv2.createTrackbar('Brightness', 'app', 50, 100, dummy)
cv2.createTrackbar('Filter', 'app', 0, len(kernels) - 1, dummy) 
cv2.createTrackbar('Greyscale', 'app', 0, 1, dummy) # this becomes a switch because of 0 and 1. Boolean type




# Main UI loop

while True:
    # read all of the trackbar values
    grayscale = cv2.getTrackbarPos('Greyscale', 'app')
    contrast = cv2.getTrackbarPos('Contrast', 'app')
    brightness = cv2.getTrackbarPos('Brightness', 'app')
    kernel_idx = cv2.getTrackbarPos('Filter', 'app')
    
    
    # apply the filters
    color_modified = cv2.filter2D(color_original, -1, kernels[kernel_idx])
    grey_modified = cv2.filter2D(gray_original, -1, kernels[kernel_idx])
    
    
    # apply the brightness and contrast
    color_modified = cv2.addWeighted(color_modified, contrast, np.zeros_like(color_original), 0, brightness - 50)
    grey_modified = cv2.addWeighted(grey_modified, contrast, np.zeros_like(gray_original), 0, brightness - 50)
    
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
        cv2.imshow('app', grey_modified)


# window cleanup
cv2.destroyAllWindows()