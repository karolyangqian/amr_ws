from setuptools import find_packages, setup

package_name = 'amr_middleware'

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
    maintainer='hadynata',
    maintainer_email='bri.hadian@gmail.com',
    description='TODO: Package description',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'ramp_system_node  = amr_middleware.ramp_system_node:main',
            'safety_system_node  = amr_middleware.safety_system_node:main'
        ],
    },
)
