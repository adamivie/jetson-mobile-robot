#!/usr/bin/env python3
"""
px4_bridge.py — Translates PX4 uXRCE-DDS topics to standard ROS2 nav topics.

Frame convention:
  PX4  uses NED  (North-East-Down),   FRD body frame
  ROS2 uses ENU  (East-North-Up),     FLU body frame

Conversions applied:
  position:    (x,y,z)_NED  → (x,y,z)_ENU  =  (y, x, -z)
  velocity:    same swap
  quaternion:  rotate by 90° yaw + flip Z
  angular vel: (p,q,r)_FRD  → (p,q,r)_FLU  =  (p, -q, -r)
  accel:       same as angular vel pattern
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy

import numpy as np
from scipy.spatial.transform import Rotation

from px4_msgs.msg import VehicleOdometry, SensorCombined, VehicleAttitude
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu
from geometry_msgs.msg import TransformStamped
import tf2_ros


def ned_to_enu_pos(x, y, z):
    """NED position → ENU position."""
    return float(y), float(x), float(-z)


def ned_to_enu_vel(vx, vy, vz):
    """NED velocity → ENU velocity."""
    return float(vy), float(vx), float(-vz)


def px4_quat_to_enu(q):
    """
    PX4 quaternion (NED, FRD) → ROS2 quaternion (ENU, FLU).
    PX4 order: [w, x, y, z]
    ROS order: [x, y, z, w]
    Rotation: apply -90° yaw then flip pitch sign.
    """
    # PX4 [w,x,y,z] → scipy [x,y,z,w]
    r_ned = Rotation.from_quat([q[1], q[2], q[3], q[0]])

    # NED→ENU static rotation: Rz(+90°) · Rx(180°)
    r_ned_to_enu = Rotation.from_euler('zx', [90, 180], degrees=True)

    r_enu = r_ned_to_enu * r_ned
    xyzw = r_enu.as_quat()  # [x,y,z,w]
    return xyzw


def frd_to_flu(x, y, z):
    """FRD body-frame vector → FLU body-frame vector."""
    return float(x), float(-y), float(-z)


class PX4Bridge(Node):
    def __init__(self):
        super().__init__('px4_bridge')

        # QoS matching PX4 uXRCE-DDS publisher profile
        px4_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        # Subscribers — PX4 topics
        self.create_subscription(
            VehicleOdometry,
            '/fmu/out/vehicle_odometry',
            self._odom_cb,
            px4_qos,
        )
        self.create_subscription(
            SensorCombined,
            '/fmu/out/sensor_combined',
            self._imu_cb,
            px4_qos,
        )
        self.create_subscription(
            VehicleAttitude,
            '/fmu/out/vehicle_attitude',
            self._attitude_cb,
            px4_qos,
        )

        # Publishers — standard ROS2 topics
        self._odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self._imu_pub = self.create_publisher(Imu, '/imu/data', 10)

        # TF broadcaster — map → odom → base_link
        self._tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        # Cache latest attitude quaternion for IMU msg
        self._latest_q_xyzw = [0.0, 0.0, 0.0, 1.0]

        self.get_logger().info('PX4 bridge running — NED/FRD → ENU/FLU')

    # ------------------------------------------------------------------ #
    def _odom_cb(self, msg: VehicleOdometry):
        now = self.get_clock().now().to_msg()

        ex, ey, ez = ned_to_enu_pos(msg.position[0], msg.position[1], msg.position[2])
        evx, evy, evz = ned_to_enu_vel(msg.velocity[0], msg.velocity[1], msg.velocity[2])
        q = px4_quat_to_enu(msg.q)          # [x,y,z,w]
        self._latest_q_xyzw = q

        # Odometry message
        odom = Odometry()
        odom.header.stamp = now
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'

        odom.pose.pose.position.x = ex
        odom.pose.pose.position.y = ey
        odom.pose.pose.position.z = ez
        odom.pose.pose.orientation.x = q[0]
        odom.pose.pose.orientation.y = q[1]
        odom.pose.pose.orientation.z = q[2]
        odom.pose.pose.orientation.w = q[3]

        odom.twist.twist.linear.x = evx
        odom.twist.twist.linear.y = evy
        odom.twist.twist.linear.z = evz

        # PX4 angular velocity is in FRD — convert to FLU
        avx, avy, avz = frd_to_flu(
            msg.angular_velocity[0],
            msg.angular_velocity[1],
            msg.angular_velocity[2],
        )
        odom.twist.twist.angular.x = avx
        odom.twist.twist.angular.y = avy
        odom.twist.twist.angular.z = avz

        self._odom_pub.publish(odom)

        # Broadcast odom → base_link TF
        tf = TransformStamped()
        tf.header.stamp = now
        tf.header.frame_id = 'odom'
        tf.child_frame_id = 'base_link'
        tf.transform.translation.x = ex
        tf.transform.translation.y = ey
        tf.transform.translation.z = ez
        tf.transform.rotation.x = q[0]
        tf.transform.rotation.y = q[1]
        tf.transform.rotation.z = q[2]
        tf.transform.rotation.w = q[3]
        self._tf_broadcaster.sendTransform(tf)

    # ------------------------------------------------------------------ #
    def _imu_cb(self, msg: SensorCombined):
        now = self.get_clock().now().to_msg()

        # Gyro FRD → FLU
        gx, gy, gz = frd_to_flu(
            msg.gyro_rad[0], msg.gyro_rad[1], msg.gyro_rad[2]
        )
        # Accel FRD → FLU (also flip sign of y and z)
        ax, ay, az = frd_to_flu(
            msg.accelerometer_m_s2[0],
            msg.accelerometer_m_s2[1],
            msg.accelerometer_m_s2[2],
        )

        imu = Imu()
        imu.header.stamp = now
        imu.header.frame_id = 'base_link'

        imu.orientation.x = self._latest_q_xyzw[0]
        imu.orientation.y = self._latest_q_xyzw[1]
        imu.orientation.z = self._latest_q_xyzw[2]
        imu.orientation.w = self._latest_q_xyzw[3]
        imu.orientation_covariance[0] = 0.01   # ~5.7° std dev
        imu.orientation_covariance[4] = 0.01
        imu.orientation_covariance[8] = 0.01

        imu.angular_velocity.x = gx
        imu.angular_velocity.y = gy
        imu.angular_velocity.z = gz
        imu.angular_velocity_covariance[0] = 1e-4
        imu.angular_velocity_covariance[4] = 1e-4
        imu.angular_velocity_covariance[8] = 1e-4

        imu.linear_acceleration.x = ax
        imu.linear_acceleration.y = ay
        imu.linear_acceleration.z = az
        imu.linear_acceleration_covariance[0] = 0.01
        imu.linear_acceleration_covariance[4] = 0.01
        imu.linear_acceleration_covariance[8] = 0.01

        self._imu_pub.publish(imu)

    # ------------------------------------------------------------------ #
    def _attitude_cb(self, msg: VehicleAttitude):
        self._latest_q_xyzw = px4_quat_to_enu(msg.q)


def main(args=None):
    rclpy.init(args=args)
    node = PX4Bridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
