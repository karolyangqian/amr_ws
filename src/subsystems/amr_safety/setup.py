from setuptools import find_packages, setup

package_name = 'amr_safety'

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
<<<<<<< HEAD
    maintainer='hadynata',
    maintainer_email='bri.hadian@gmail.com',
=======
    maintainer='karol',
    maintainer_email='karolyangqian14@gmail.com',
>>>>>>> origin/refactor/tidy-up
    description='TODO: Package description',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
<<<<<<< HEAD
            'emergency_stop_node = amr_safety.emergency_stop_node:main'
=======
            'emergency_stop_node = amr_safety.emergency_stop_node:main',
>>>>>>> origin/refactor/tidy-up
        ],
    },
)
