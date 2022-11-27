import cv2
import os
import sys
import time
import threading
from glob import glob
from pathlib import Path


# video = cv2.VideoCapture("new/SnapSave1080p.mp4")
# i=0
# while(video.isOpened()):
#     ret, frame = video.read()
#     if ret == False:
#         break
#     cv2.imwrite('images/image'+str(i)+'.jpg',frame)
#     i+=1

# video.release()
# cv2.destroyAllWindows()







##### run on images folder

# files = glob('images/*')
# for file in files:
#     list.append(file.replace('images/',''))
# list.sort(key=lambda x : int((x.replace("image",'').split('.')[0])))


# out2 = cv2.VideoWriter('bottom_right_video.mp4',cv2.VideoWriter_fourcc(*'DIVX'), 60, frameSize)


#####  run on other folders

list = []

files = glob('images/*')
for file in files:
    list.append(file.replace('images/',''))
list.sort(key=lambda x : int((x.replace("image",'').split('.')[0])))


frameSize = (960, 540)
i = 0



for i in list:
    image = cv2.imread(f"images/{i}")
    (h, w) = image.shape[:2]
    (cX, cY) = (w // 2, h // 2)

    topLeft = image[0:cY, 0:cX]
    topRight = image[0:cY, cX:w]
    bottomLeft = image[cY:h, 0:cX]
    bottomRight = image[cY:h, cX:w]


    cv2.imwrite(f"top_left/{i}topLeft.jpg",topLeft)
    cv2.imwrite(f"top_right/{i}topRight.jpg",topRight)
    cv2.imwrite(f"bottom_left/{i}bottomLeft.jpg",bottomLeft)
    cv2.imwrite(f"bottom_right/{i}bottomRight.jpg",bottomRight)
    cv2.waitKey(0)




# def create_video():
#     out1 = cv2.VideoWriter('left_top_video.mp4',cv2.VideoWriter_fourcc(*'DIVX'), 60, frameSize)
#     out2 = cv2.VideoWriter('right_top_video.mp4',cv2.VideoWriter_fourcc(*'DIVX'), 60, frameSize)
#     out3 = cv2.VideoWriter('buttom_left_video.mp4',cv2.VideoWriter_fourcc(*'DIVX'), 60, frameSize)
#     out4 = cv2.VideoWriter('buttom_right_video.mp4',cv2.VideoWriter_fourcc(*'DIVX'), 60, frameSize)

#     for i in list:
#         image = cv2.imread(f"images/{i}")
#         out1.write(image)
#         out2.write(image)
#         out3.write(image)
#         out4.write(image)


#     out1.release()