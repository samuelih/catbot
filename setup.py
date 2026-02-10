"""CatToy package setup for development installation."""

from setuptools import setup, find_packages

setup(
    name="cattoy",
    version="0.1.0",
    description="Autonomous cat toy robot for Waveshare JetBot 2GB AI Kit",
    packages=find_packages(),
    python_requires=">=3.6",
    install_requires=[
        "smbus2",
        "numpy",
    ],
    extras_require={
        "dev": [
            "pytest",
            "opencv-python",
        ],
        "gamepad": [
            "evdev",
        ],
    },
    entry_points={
        "console_scripts": [
            "cattoy=src.main:main",
        ],
    },
)
