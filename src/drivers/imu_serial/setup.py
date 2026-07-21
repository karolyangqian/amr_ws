from setuptools import find_packages, setup

package_name = 'imu_serial'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/imu.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='zulfan',
    maintainer_email='zulfan.andria@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'imu_serial_node = imu_serial.imu_serial_node:main',
        ],
    },
)

