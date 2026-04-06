from setuptools import setup
import os
from glob import glob

package_name = 'robot_vision'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'depth_processor = robot_vision.depth_processor:main',
            'obstacle_detector = robot_vision.obstacle_detector:main',
            'px4_bridge = robot_vision.px4_bridge:main',
            'jetson_stats = robot_vision.jetson_stats_node:main',
        ],
    },
)
