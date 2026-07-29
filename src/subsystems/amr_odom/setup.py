from setuptools import find_packages, setup

package_name = 'amr_odom'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
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
            'zlac_odom_node = amr_odom.zlac_odom_node:main',
            'wheel_travel_odom_node = amr_odom.wheel_travel_odom_node:main',
            'odom_node = amr_odom.odom_node:main',
        ],
    },
)
