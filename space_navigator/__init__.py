"""
Space Navigator - RL-based Spacecraft Maneuver Optimization

An automated collision avoidance system using reinforcement learning
to calculate optimal maneuvers for satellites facing conjunction risks.
"""

__version__ = "0.1.0"
__author__ = "SAST Hackathon 2026"

from .api.environment import SpaceEnvironment
from .simulator.simulator import Simulator
