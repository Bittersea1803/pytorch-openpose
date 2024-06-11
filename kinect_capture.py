import freenect
import cv2
import numpy as np

def get_video():
    print("Attempting to get video frame...")
    frame, _ = freenect.sync_get_video()
    if frame is not None:
        print("Frame obtained successfully.")
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    else:
        print("Failed to obtain frame.")
        return None

def save_image(image, filename):
    if image is not None:
        cv2.imwrite(filename, image)
        print(f"Image saved as {filename}")
    else:
        print("No image to save.")

def main():
    rgb_image = get_video()
    if rgb_image is not None:
        save_image(rgb_image, 'kinect_image.png')
        cv2.imshow('Kinect Image', rgb_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("Failed to capture image from Kinect.")

if __name__ == "__main__":
    main()