#!/usr/bin/python

from re import sub
import rospy
import cv2
from sensor_msgs.msg import Image
import numpy as np
import copy
from glob import glob
from cv_bridge import CvBridge

# openpose setup
from src import util
from src.body import Body
from src.hand import Hand

import matplotlib as mpl
import numpy as np

## TODO 4: Add images to the list
images = ['./triangle.jpg', './star.jpg', './quatrefoil.jpg', './heart.jpg','./house0.jpg','./house2.jpg']
##

def color_fader(c1,c2,mix=0): #fade (linear interpolate) from color c1 (at mix=0) to c2 (mix=1)
    c1=np.array(mpl.colors.to_rgb(c1))
    c2=np.array(mpl.colors.to_rgb(c2))
    #return hex_to_bgr(mpl.colors.to_hex((1-mix)*c1 + mix*c2))
    return ((1-mix)*c1 + mix*c2)[::-1]*255

def get_colors(n=100):
    cs = ['#FF0000', '#FFFF00', '#00FF00', '#00FFFF', '#0000FF', '#FF00FF']
    lcs = len(cs)

    colors = []

    for i in range(lcs):
        for x in range(n+1):
            colors.append(color_fader(cs[i], cs[(i+1) % lcs],x/n))

    return colors

def hex_to_bgr(hex):
    return tuple(int(hex[i:i+2], 16) for i in (4, 2, 0))

class OpenPoseTrack:
    def __init__(self):

        rospy.init_node("openpose_tracking_node")

        self.rgb_topic = "/camera/rgb/image_raw"
        self.bridge = CvBridge()

        self.body_estimation = Body('/home/openpose_user/src/openpose/model/body_pose_model.pth')
        self.hand_estimation = Hand('/home/openpose_user/src/openpose/model/hand_pose_model.pth')


        self.b_resize = True
        self.hands = False
        self.body = True
        self.drawing_points = []
        self.max_points = 100
        self.max_dist = 50
        self.color = np.random.rand(3) * 255
        self.colors = get_colors(20)
        self.color_start_index = 0
        self.color_mode = 'wheel' # the other one is rave
        ## TODO 3: Add image selection
        self.image_index=0


        self.rgb_sub = rospy.Subscriber(self.rgb_topic, Image, self.callback, queue_size=1, buff_size=100000000)

        rospy.on_shutdown(self.shutdownhook)



    def process_frame(self, frame, body=True, hands=True):
        canvas_bodypose = copy.deepcopy(frame)
        canvas_real_image_drawing = copy.deepcopy(frame)
        canvas_line_only = np.full(frame.shape, 255, dtype=np.uint8)
        if body:
            candidate, subset = self.body_estimation(frame)
            canvas_bodypose, drawing_joint = util.draw_bodypose(canvas_bodypose, candidate, subset)
            
            if drawing_joint is not None:
                self.drawing_points.append(drawing_joint)
                if len(self.drawing_points) >= self.max_points:
                    self.drawing_points.pop(0)
                    self.color_start_index = (self.color_start_index + 1) % len(self.colors)
            for i in range(len(self.drawing_points)-2):
                coordinate0 = np.array([self.drawing_points[i][0], self.drawing_points[i][1]])
                coordinate1 = np.array([self.drawing_points[i+1][0], self.drawing_points[i+1][1]])
                coordinate2 = np.array([self.drawing_points[i+2][0], self.drawing_points[i+2][1]])
                new_coordinate0 = ((coordinate0 + coordinate1) / 2).round(0).astype(np.int64)
                new_coordinate1 = ((coordinate1 + coordinate2) / 2).round(0).astype(np.int64)
                if cv2.norm(new_coordinate0 - new_coordinate1, cv2.NORM_L2) <= self.max_dist:
                    if self.color_mode == 'rave':
                        diff = (np.random.rand(3) - 0.5) * 0.05 * 255
                        self.color = (self.color + diff).clip(0, 255)
                        color = self.color
                    elif self.color_mode == 'wheel':
                        color = self.colors[(self.color_start_index + i) % len(self.colors)]
                    ## TODO 1: Color mode for single color
                    elif self.color_mode == 'single':
                        color = [255,0,0]
                    ##
                    cv2.line(canvas_real_image_drawing, new_coordinate0, new_coordinate1, color, thickness=4)
                    cv2.line(canvas_line_only, new_coordinate0, new_coordinate1, [0, 0, 0], thickness=4)
        if hands:
            hands_list = util.handDetect(candidate, subset, frame)
            all_hand_peaks = []
            for x, y, w, _ in hands_list:
                peaks = self.hand_estimation(frame[y:y+w, x:x+w, :])
                peaks[:, 0] = np.where(peaks[:, 0]==0, peaks[:, 0], peaks[:, 0]+x)
                peaks[:, 1] = np.where(peaks[:, 1]==0, peaks[:, 1], peaks[:, 1]+y)
                all_hand_peaks.append(peaks)
            canvas_bodypose = util.draw_handpose(canvas_bodypose, all_hand_peaks)
        

        return canvas_bodypose, canvas_real_image_drawing, canvas_line_only

    def limit_drawing_points(self):
        l = min(self.max_points, len(self.drawing_points))
        self.color_start_index = (self.color_start_index + len(self.drawing_points) - l) % len(self.colors)
        self.drawing_points = self.drawing_points[-l:]

    def callback(self, msg):
        image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')        
        if(self.b_resize):
            width = round(image.shape[1] * 0.5)
            height = round(image.shape[0] * 0.5)
            dim = (width, height)
            resized = cv2.flip(cv2.resize(image, dim, interpolation = cv2.INTER_AREA),1)
        else:
            resized = cv2.flip(image)

        bodypose_frame, real_image_drawing_frame, line_only_frame = self.process_frame(resized, body=self.body,
                                    hands=self.hands)

        cv2.namedWindow('Bodypose', cv2.WINDOW_NORMAL)
        cv2.namedWindow('Real image drawing', cv2.WINDOW_NORMAL)
        cv2.namedWindow('Line only', cv2.WINDOW_NORMAL)
        cv2.namedWindow('Template image', cv2.WINDOW_NORMAL)
        cv2.imshow('Bodypose', bodypose_frame)
        cv2.imshow('Real image drawing', real_image_drawing_frame)
        cv2.imshow('Line only', line_only_frame)

        ## TODO 3: Draw selected image
        img =  cv2.imread(images[self.image_index], 1)
        cv2.imshow('Template image', img)
        ##

        ## TODO 7: Check if joint is in the upper right corner and clear the line if it is
        if self.drawing_points[-1][0]>300 and self.drawing_points[-1][1]<20:
            self.color_start_index = (self.color_start_index + len(self.drawing_points)) % len(self.colors)
            self.drawing_points = []

        ##

        key_press = cv2.waitKey(4)        
        if key_press == ord('d'):
            self.color_start_index = (self.color_start_index + len(self.drawing_points)) % len(self.colors)
            self.drawing_points = []
        elif key_press == ord('f'):
            self.max_points = 10
            self.limit_drawing_points()
        elif key_press == ord('s'):
            self.max_points = 100
            self.limit_drawing_points()
        ## TODO 5: Add medium speed mode:
        elif key_press == ord('l'):
            self.max_points = 50
            self.limit_drawing_points()
       
        ##
        ## TODO 6: Increment/decrement speed
        elif key_press == ord('m'):
            self.max_points = 20
            self.limit_drawing_points()
        elif key_press == ord('j'):
            self.max_points = 90
            self.limit_drawing_points()
        ##
        elif key_press == ord('o'):
            self.max_dist += 10
        elif key_press == ord('p'):
            self.max_dist -= 10
        elif key_press == ord('w'):
            self.color_mode = 'wheel'
        elif key_press == ord('r'):
            self.color_mode = 'rave'
        ## TODO 1: Color mode for single color
        elif key_press == ord('c'):
            self.color_mode = 'single'   
        ##
        ## TODO 3: Change image selection
        elif key_press == ord('n'):
            self.image_index+=1 
            self.image_index%=len(images)
        ##


    def shutdownhook(self):
        """
        Destroys all windows on shutdown.
        """
        cv2.destroyAllWindows()


if __name__ == "__main__":
    # get passed arguments from terminal
    # args = default_argument_parser().parse_args()

    # Creates a node to instance segmentation of a video
    node = OpenPoseTrack()

    rospy.spin()
