import cv2
import os
import sys
import time
import threading
from glob import glob
from pathlib import Path


image = cv2.imread('photo.jpg')
(h, w) = image.shape[:2]
# cv2.imshow('Original', image)
 
# compute the center coordinate of the image
(cX, cY) = (w // 2, h // 2)


topLeft = image[0:cY, 0:cX]
topRight = image[0:cY, cX:w]
bottomLeft = image[cY:h, 0:cX]
bottomRight = image[cY:h, cX:w]

# visualize the cropped regions
# cv2.imshow("Top Left Corner", topLeft)
# cv2.imshow("Top Right Corner", topRight)
# cv2.imshow("Bottom Right Corner", bottomLeft)
# cv2.imshow("Bottom Left Corner", bottomRight)

cv2.waitKey(0)
