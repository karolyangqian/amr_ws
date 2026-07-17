import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'amr_discovery'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='karol',
    maintainer_email='karolyangqian14@gmail.com',
    description='UDP broadcast discovery service untuk robot AMR di LAN',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'discovery_node = amr_discovery.discovery_node:main',
        ],
    },
)
