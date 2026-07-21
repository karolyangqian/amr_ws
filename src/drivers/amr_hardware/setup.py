from setuptools import find_packages, setup

import os
from glob import glob

package_name = 'amr_hardware'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='zulfan',
    maintainer_email='zulfan.andria@gmail.com',
    description='Hardware driver dan teleop untuk AMR (ZLAC8015D)',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'zlac_driver_node         = amr_hardware.base.zlac_driver_node:main',
            'cmd_vel_inverter_node    = amr_hardware.base.cmd_vel_inverter_node:main',
            'battery_monitor_node     = amr_hardware.battery.battery_monitor_node:main',
            'imu_fixer_node           = amr_hardware.imu.imu_fixer_node:main',
            'scan_relay_node          = amr_hardware.lidar.scan_relay_node:main',
        ],
    },
)
