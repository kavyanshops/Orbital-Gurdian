"""
Space Navigator - Setup file for pip installation
"""

from setuptools import setup, find_packages

setup(
    name="space_navigator",
    version="0.1.0",
    author="SAST Hackathon 2026",
    description="RL-based spacecraft maneuver optimization for collision avoidance",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.21.0",
        "scipy>=1.7.0",
        "matplotlib>=3.5.0",
        "tqdm>=4.60.0",
    ],
    extras_require={
        "torch": ["torch>=2.0.0"],
        "all": ["torch>=2.0.0"],
    },
    entry_points={
        "console_scripts": [
            "space-nav-generate=generation.generate_collision:main",
            "space-nav-train-ce=training.CE.train_ce:main",
            "space-nav-train-es=training.ES.train_es:main",
            "space-nav-simulate=examples.collision:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Astronomy",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
