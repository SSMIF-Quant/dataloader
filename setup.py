"""Setup script for packaging and distributing the project."""

from setuptools import setup, find_packages

with open('requirements.txt') as f: # pylint: disable=W1514
    requirements = f.read().splitlines()

setup(
    name="dataloader",
    version="0.1",
    include_package_data=True,
    python_requires='>=3.13',
    packages=find_packages(),
    setup_requires=['setuptools-git-versioning'],
    install_requires=requirements,
    author="SSMIF",
    author_email="ssmif@stevens.edu",
    description="A thread-safe data loader for ClickHouse.",
    long_description=open('README.md').read(), # pylint: disable=W1514
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    version_config={
       "dirty_template": "{tag}",
    }
)