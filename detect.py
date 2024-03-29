import argparse
import sys
import time

import cv2
from tflite_support.task import core
from tflite_support.task import processor
from tflite_support.task import vision
import utils

from picamera2 import Picamera2


def run(model: str, camera_id: int, width: int, height: int, num_threads: int,
        enable_edgetpu: bool) -> None:
  """Continuously run inference on images acquired from the camera.

  Args:
    model: Name of the TFLite object detection model.
    camera_id: The camera id to be passed to OpenCV.
    width: The width of the frame captured from the camera.
    height: The height of the frame captured from the camera.
    num_threads: The number of CPU threads to run the model.
    enable_edgetpu: True/False whether the model is a EdgeTPU model.
  """

  # Variables to calculate FPS
  counter, fps = 0, 0
  start_time = time.time()

  # Start capturing video input from the camera
  picam2 = Picamera2()
  normalSize = (640, 480)
  lowresSize = (320, 240)
  config = picam2.create_preview_configuration(main={"size": normalSize},
                                               lores={"size": lowresSize, "format": "YUV420"})
  picam2.configure(config)
  stride = picam2.stream_configuration("lores")["stride"]
  picam2.start()

  # Visualization parameters
  row_size = 20  # pixels
  left_margin = 24  # pixels
  text_color = (0, 0, 255)  # red
  font_size = 1
  font_thickness = 1
  fps_avg_frame_count = 10

  # Initialize the object detection model
  base_options = core.BaseOptions(
      file_name=model, use_coral=enable_edgetpu, num_threads=num_threads)
  detection_options = processor.DetectionOptions(
      max_results=3, score_threshold=0.7)
  options = vision.ObjectDetectorOptions(
      base_options=base_options, detection_options=detection_options)
  detector = vision.ObjectDetector.create_from_options(options)

  img_list = []
  # Continuously capture images from the camera and run inference
  while True:
    buffer = picam2.capture_buffer("lores")
    image = buffer[:stride * lowresSize[1]].reshape((lowresSize[1], stride))
 
    counter += 1

    # Convert the image from gray to RGB as required by the TFLite model.
    rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

    # Create a TensorImage object from the RGB image.
    input_tensor = vision.TensorImage.create_from_array(rgb_image)

    img_list.append(rgb_image)
    if (len(img_list)>1):
      mse = get_mse(img_list[0], img_list[1])
      img_list.pop(0)

    if mse!=0:
      # Run object detection estimation using the model.
      detection_result = detector.detect(input_tensor)

      # Draw keypoints and edges on input image
      # image = utils.visualize(image, detection_result)

      # Calculate the FPS
      if counter % fps_avg_frame_count == 0:
        end_time = time.time()
        fps = fps_avg_frame_count / (end_time - start_time)
        start_time = time.time()

      # Show the FPS
      # fps_text = 'FPS = {:.1f}'.format(fps)
      # text_location = (left_margin, row_size)
      # cv2.putText(image, fps_text, text_location, cv2.FONT_HERSHEY_PLAIN,
      #            font_size, text_color, font_thickness)

      # Stop the program if the ESC key is pressed.
      # if cv2.waitKey(1) == 27:
      #   break
      #cv2.imshow('object_detector', image)
      utils.print_data(detection_result, fps)



def main():
  parser = argparse.ArgumentParser(
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument(
      '--model',
      help='Path of the object detection model.',
      required=False,
      default='efficientdet_lite0.tflite')
  parser.add_argument(
      '--cameraId', help='Id of camera.', required=False, type=int, default=0)
  parser.add_argument(
      '--frameWidth',
      help='Width of frame to capture from camera.',
      required=False,
      type=int,
      default=640)
  parser.add_argument(
      '--frameHeight',
      help='Height of frame to capture from camera.',
      required=False,
      type=int,
      default=480)
  parser.add_argument(
      '--numThreads',
      help='Number of CPU threads to run the model.',
      required=False,
      type=int,
      default=4)
  parser.add_argument(
      '--enableEdgeTPU',
      help='Whether to run the model on EdgeTPU.',
      action='store_true',
      required=False,
      default=False)
  args = parser.parse_args()

  run(args.model, int(args.cameraId), args.frameWidth, args.frameHeight,
      int(args.numThreads), bool(args.enableEdgeTPU))


def get_mse(img1, img2):
  h, w = img1.shape
  diff = cv2.subtract(img1, img2)
  err = np.sum(diff**2)
  mse = err/(float(h*w))
  return mse


if __name__ == '__main__':
  main()
