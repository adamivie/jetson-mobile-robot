#!/usr/bin/env python3
"""
depth_processor.py
Subscribes to RealSense D455 depth image, publishes obstacle distance.
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32
from cv_bridge import CvBridge
import numpy as np


class DepthProcessor(Node):
    def __init__(self):
        super().__init__('depth_processor')
        self.declare_parameter('depth_topic', '/camera/camera/depth/image_rect_raw')
        self.declare_parameter('roi_width_frac', 0.3)
        self.declare_parameter('roi_height_frac', 0.4)
        self.declare_parameter('min_valid_depth_m', 0.3)
        self.declare_parameter('max_valid_depth_m', 6.0)

        depth_topic = self.get_parameter('depth_topic').value
        self.bridge = CvBridge()
        self.sub_depth = self.create_subscription(Image, depth_topic, self.depth_cb, 10)
        self.pub_obstacle_dist = self.create_publisher(Float32, '~/obstacle_distance_m', 10)
        self.get_logger().info(f'DepthProcessor listening on {depth_topic}')

    def depth_cb(self, msg: Image):
        depth_m = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough').astype(np.float32) / 1000.0
        h, w = depth_m.shape
        rw = self.get_parameter('roi_width_frac').value
        rh = self.get_parameter('roi_height_frac').value
        min_d = self.get_parameter('min_valid_depth_m').value
        max_d = self.get_parameter('max_valid_depth_m').value
        x0, x1 = int(w * (0.5 - rw / 2)), int(w * (0.5 + rw / 2))
        y0, y1 = int(h * (0.5 - rh / 2)), int(h * (0.5 + rh / 2))
        roi = depth_m[y0:y1, x0:x1]
        valid = roi[(roi > min_d) & (roi < max_d)]
        if valid.size == 0:
            return
        out = Float32()
        out.data = float(np.percentile(valid, 5))
        self.pub_obstacle_dist.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = DepthProcessor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
