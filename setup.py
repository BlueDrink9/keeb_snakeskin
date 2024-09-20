from setuptools import setup, find_packages
import math

setup(
    name='keeb_snakeskin',
    version='0.1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'build123d > 0.7.0',
        'svgpathtools',
        'pygerber',
    ],
    entry_points={
        'console_scripts': [
            'snakeskin=snakeskin:main',
        ],
    },
)
