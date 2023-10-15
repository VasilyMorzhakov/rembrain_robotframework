import os
import sys
try:
    import cv2
    has_cv2 = True
except ImportError:
    has_cv2 = False
    
import setuptools

with open("README.md") as f:
    long_description = f.read()

with open(
    os.path.join(os.path.dirname(__file__), "config", "requirements", "base.txt")
) as f:
    requirements = [i.strip() for i in f]
if not has_cv2:
    requirements.append("opencv-python")

    

setuptools.setup(
    name="rembrain_robot_framework",
    version="0.1.18",
    author="Rembrain",
    author_email="info@rembrain.ai",
    description="Rembrain Robot Framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/VasilyMorzhakov/rembrain_robotframework",
    # collect all packages
    packages=setuptools.find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
