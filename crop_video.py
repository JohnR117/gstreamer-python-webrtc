import cv2
import os
import sys
import time
import threading
from glob import glob
from pathlib import Path

def add_level(root, folder_name):
    new_level = os.path.join(root, folder_name) 
    if not os.path.exists(new_level):
        os.mkdir(new_level)
    return new_level


list = []

files = glob('photos/*')
for file in files:
    list.append(file.replace('photos/',''))
list.sort(key=lambda x : int((x.replace("frame",'').split('.')[0])))



frameSize = (1920, 1080)
b = 0


### Split image to 8 peaces

for ii in list:
    image = cv2.imread(f"photos/{ii}")
    if '/' in ii:
        img_name = ii.rsplit('/', 1)[1].split('.')[0]
    else:
        img_name = ii.split('.')[0]


    (h, w) = image.shape[:2]
    (qX, qY) = (w // 4, h // 2)
    indexX, indexY = 0,0
    stopX, stopY = qX, qY
    rows = 2
    cols = 4
    outputs_folder = add_level('./', 'outputs')
    # img_folder = add_level(outputs_folder, img_name)
    for i, row in enumerate(range(rows)):
        indexX = 0
        stopX = qX
        for j, col in enumerate(range(cols)):

            temp = add_level(outputs_folder, f'{i}{j}')
            print(i,j,': ', indexX, indexY, ':', stopX, stopY)
            slice = image[indexY:stopY, indexX:stopX, :]
            cv2.imwrite(f"{temp}/{img_name}.png",slice)
            indexX += qX
            stopX+=qX
            # print(row*cols + col)
        print('*')
        indexY += qY
        stopY += qY


### Split image to 4 peaces

# cv2.imshow('img', image)
# cv2.waitKey(0)
# print(list)
# for i in list:
#     image = cv2.imread(f"photos/{i}")
#     (h, w) = image.shape[:2]
#     (cX, cY) = (w // 2, h // 2)
#     b += 1
    # topLeft = image[0:cY, 0:cX]
    # topRight = image[0:cY, cX:w]
    # bottomLeft = image[cY:h, 0:cX]
    # bottomRight = image[cY:h, cX:w]


#     cv2.imwrite(f"top_left/topLeft{b}.png",topLeft)
#     cv2.imwrite(f"top_right/topRight{b}.png",topRight)
#     cv2.imwrite(f"bottom_left/bottomLeft{b}.png",bottomLeft)
#     cv2.imwrite(f"bottom_right/bottomRight{b}.png",bottomRight)
# cv2.waitKey(0)




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
