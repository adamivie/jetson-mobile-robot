#!/usr/bin/env python3
"""
obstacle_detector.py
Publishes a Bool stop flag based on obstacle distance threshold.
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Bool


class ObstacleDetector(Node):
    def __init__(self):
        super().__init__('obstacle_detector')
        self.declare_parameter('stop_distance_m', 0.6)
        self.sub = self.create_subscription(
            Float32, '/depth_processor/obstacle_distance_m', self.dist_cb, 10)
        self.pub = self.create_publisher(Bool, '~/obstacle_detected', 10)
        self.get_logger().info('ObstacleDetector started')

    def dist_cb(self, msg: Float32):
        stop_dist = self.get_parameter('stop_distance_m').value
        out = Bool()
        out.data = msg.data < stop_dist
        if out.data:
            self.get_logger().warn(f'Obstacle at {msg.data:.2f}m — STOP')
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
