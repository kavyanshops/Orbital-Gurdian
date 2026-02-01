"""
Monte Carlo Tree Search Agent

Tree search over maneuver sequences with UCB1 exploration.
"""

import numpy as np
from typing import List, Optional, Dict, Any
from tqdm import tqdm
import copy
import math

from ...agent.base_agent import BaseAgent
from ...api.environment import SpaceEnvironment, Maneuver
from ...simulator.simulator import Simulator


class MCTSNode:
    """Node in the MCTS tree."""
    
    def __init__(
        self,
        state: Dict,
        parent: Optional['MCTSNode'] = None,
        action: Optional[Maneuver] = None
    ):
        self.state = state
        self.parent = parent
        self.action = action  # Action that led to this state
        self.children: List['MCTSNode'] = []
        self.visits = 0
        self.value = 0.0
        self.untried_actions: List[Maneuver] = []
        
    def is_fully_expanded(self) -> bool:
        return len(self.untried_actions) == 0
    
    def is_terminal(self) -> bool:
        return self.state.get('time_remaining', 1) <= 0
    
    def ucb1(self, c: float = 1.41) -> float:
        """Upper Confidence Bound for Trees."""
        if self.visits == 0:
            return float('inf')
        
        exploitation = self.value / self.visits
        exploration = c * math.sqrt(math.log(self.parent.visits) / self.visits)
        
        return exploitation + exploration
    
    def best_child(self, c: float = 1.41) -> 'MCTSNode':
        """Select child with highest UCB1 value."""
        return max(self.children, key=lambda node: node.ucb1(c))


class MCTSAgent(BaseAgent):
    """
    Monte Carlo Tree Search agent for maneuver optimization.
    """
    
    def __init__(
        self,
        environment: SpaceEnvironment,
        n_simulations: int = 1000,
        max_actions_per_node: int = 5,
        exploration_constant: float = 1.41,
        max_delta_v: float = 3.0,
        rollout_depth: int = 10
    ):
        """
        Initialize MCTS agent.
        
        Args:
            environment: Space environment
            n_simulations: Number of MCTS simulations
            max_actions_per_node: Max actions to try from each node
            exploration_constant: UCB1 exploration constant
            max_delta_v: Max delta-V per maneuver
            rollout_depth: Max rollout steps
        """
        super().__init__(environment, name="MCTSAgent")
        
        self.n_simulations = n_simulations
        self.max_actions = max_actions_per_node
        self.c = exploration_constant
        self.max_delta_v = max_delta_v
        self.rollout_depth = rollout_depth
        
    def _generate_actions(self, state: Dict) -> List[Optional[Maneuver]]:
        """Generate possible actions from current state."""
        actions = [None]  # No maneuver is always an option
        
        current_epoch = state['epoch']
        fuel = state['satellite']['fuel_remaining']
        
        if fuel < 0.1:
            return actions
        
        # Generate a few maneuver options
        for mag in [0.5, 1.0, 2.0]:
            if mag > fuel:
                continue
            
            for direction in [[1, 0, 0], [0, 1, 0], [0, 0, 1],
                            [-1, 0, 0], [0, -1, 0], [0, 0, -1]]:
                delta_v = np.array(direction) * min(mag, self.max_delta_v)
                actions.append(Maneuver(epoch=current_epoch, delta_v=delta_v))
        
        # Limit to max actions
        if len(actions) > self.max_actions:
            indices = [0] + list(np.random.choice(
                len(actions) - 1, self.max_actions - 1, replace=False
            ) + 1)
            actions = [actions[i] for i in indices]
        
        return actions
    
    def _simulate_step(
        self,
        env: SpaceEnvironment,
        action: Optional[Maneuver]
    ) -> Tuple[Dict, float]:
        """Simulate one step."""
        state, reward, done, info = env.step(action)
        return state, reward
    
    def _rollout(self, env: SpaceEnvironment, state: Dict) -> float:
        """Random rollout from current state."""
        total_reward = 0.0
        env_copy = copy.deepcopy(env)
        
        for _ in range(self.rollout_depth):
            if env_copy.current_epoch >= env_copy.end_epoch:
                break
            
            # Random action (mostly no-op)
            if np.random.random() < 0.1:
                actions = self._generate_actions(state)
                action = np.random.choice(actions) if actions else None
            else:
                action = None
            
            state, reward = self._simulate_step(env_copy, action)
            total_reward += reward
        
        return total_reward
    
    def _select(self, node: MCTSNode) -> MCTSNode:
        """Select node to expand using UCB1."""
        while not node.is_terminal():
            if not node.is_fully_expanded():
                return node
            node = node.best_child(self.c)
        return node
    
    def _expand(self, node: MCTSNode, env: SpaceEnvironment) -> MCTSNode:
        """Expand node with new action."""
        if not node.untried_actions:
            return node
        
        action = node.untried_actions.pop()
        
        env_copy = copy.deepcopy(env)
        env_copy.current_epoch = node.state['epoch']
        
        new_state, _ = self._simulate_step(env_copy, action)
        
        child = MCTSNode(state=new_state, parent=node, action=action)
        child.untried_actions = self._generate_actions(new_state)
        node.children.append(child)
        
        return child
    
    def _backpropagate(self, node: MCTSNode, value: float):
        """Backpropagate value up the tree."""
        while node is not None:
            node.visits += 1
            node.value += value
            node = node.parent
    
    def optimize(
        self,
        verbose: bool = True,
        **kwargs
    ) -> List[Maneuver]:
        """
        Run MCTS optimization.
        
        Returns:
            Best maneuver sequence found
        """
        # Initialize root
        env_copy = copy.deepcopy(self.env)
        initial_state = env_copy.get_state()
        
        root = MCTSNode(state=initial_state)
        root.untried_actions = self._generate_actions(initial_state)
        
        iterator = tqdm(range(self.n_simulations), desc="MCTS") if verbose else range(self.n_simulations)
        
        for sim in iterator:
            # Reset environment
            env_copy = copy.deepcopy(self.env)
            
            # Selection
            node = self._select(root)
            
            # Expansion
            if not node.is_terminal():
                node = self._expand(node, env_copy)
            
            # Rollout
            value = self._rollout(env_copy, node.state)
            
            # Backpropagation
            self._backpropagate(node, value)
        
        # Extract best path
        self.maneuvers = []
        node = root
        
        while node.children:
            best_child = max(node.children, key=lambda n: n.visits)
            if best_child.action:
                self.maneuvers.append(best_child.action)
            node = best_child
        
        self.training_history.append({
            'simulations': self.n_simulations,
            'tree_depth': len(self.maneuvers)
        })
        
        return self.maneuvers
    
    def get_action(self, state: Dict[str, Any]) -> Optional[Maneuver]:
        """Get next scheduled maneuver."""
        current_epoch = state['epoch']
        
        for m in self.maneuvers:
            if abs(m.epoch - current_epoch) < self.env.time_step_days:
                return m
        
        return None


# Missing import
from typing import Tuple
