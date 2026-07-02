from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'amr_mission'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='zulfan',
    maintainer_email='zulfan.andria@gmail.com',
    description='Mission executor for AMR',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'mission_executor_node  = amr_mission.mission_executor_node:main',
            'station_recorder_node  = amr_mission.station_recorder_node:main',
        ],
    },
)
