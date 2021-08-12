from typing import Tuple
import logging
import math
import gym
from abc import ABC, abstractmethod

from sim.System import System


class SimEnv(gym.Env, ABC):
    """ 
    Wrapper for simulation model as gym environment
    """
    @classmethod
    @abstractmethod
    def __init__(self, system: System):

        self.system = system
        self.logger = logging.getLogger("factory_sim")
        
        self.sim_counter = 1
        self.done = False
        self.previous_reward = 0

    @classmethod
    @abstractmethod
    def step (self, action: object) -> Tuple[object, float, bool, dict]:  
        """
        Gym interface method: step
        Takes action and executes simulation until next action is needed
        :param action: int, represents maintenance machine n; n+1: do nothing
        """
        pass  

    @classmethod
    @abstractmethod
    def reset(self):
        """
        Gym interface method: reset
        Initializes the environment and runs until the first decision point 
        is reached.
        :return initial_observation: np.array, initial state space
        """ 
        pass
 
    @classmethod
    @abstractmethod
    def next_sim_step(self):
        """ Performs a simulation until next decision point is reached """
        pass
    
    @classmethod
    @abstractmethod
    def execute_action(self, action):
        """
        Executes the agents action in the factory simulation
        :param action: int,  numerival value of action chosen by the agent
        """
        pass

    def _check_if_model_is_done(self) -> bool:
        """ Check if simulation time is reached"""
        return self.system.sim_env.now >= self.system.simulation_time

    def _get_observation(self):
        """ Return state of simpy-model to gym-observation"""
        observation = self.system_state_converter.system_state_to_observation()
        return observation

    def _get_info(self):
        """ Returns empty dict by default"""
        return {}

    def _get_reward(self):
        """
        Calculates the current reward by subtracting the previous reward from the total reward
        :return: int, reward
        """
        reward = self.reward_function.reward - self.previous_reward
        self.previous_reward = self.reward_function.reward
        self.last_reward_calculation = self.system.sim_env.now
        return reward

    def _get_bottleneck(self):
        """ Returns the duration of the longest process for each product type based on the system path for material flow. """
        longest_task = {}
        for product_type in self.system.production_system.product_types:
            min_process_times = []
            # for all processes list the minimal process_durations
            for task in self.system.production_system.tasks_for_product[product_type]:
                duration_task = float('inf')
                # for one task for all machines find the smallest duration of that task
                for machine_type in self.system.production_system.machine_types:
                    if task in self.system.production_system.machine_types[machine_type]['tasks']:
                        if duration_task > self.system.production_system.machine_types[machine_type]['tasks'][task]:
                            duration_task = self.system.production_system.machine_types[machine_type]['tasks'][task]
                min_process_times.append(duration_task)
                assert (duration_task < float('inf')), 'Found a product in the simulation that can not be produced with the given machines.'
            longest_task[product_type] = max(min_process_times)
        return longest_task

    def _log_summary(self):
        """ Log final summary """
        
        # adapt simulation time regarding weekends
        if self.system.weekend_on:
            weekends_per_simulation = int(self.system.simulation_time / self.system.weekly_schedule.steps_per_week)
            active_simulation_time = self.system.simulation_time - (weekends_per_simulation * self.system.weekly_schedule.steps_per_weekend)
        else:
            active_simulation_time = self.system.simulation_time
           
        # Parts produced depend on the amount of products in sink_store
        parts_produced, max_parts_possible, production_rate, lost_parts = {}, {}, {}, {}
        longest_task = self._get_bottleneck()
        self.logger.debug('Here are the longest process durations: {}'.format(longest_task), extra={'simtime': self.system.sim_env.now})
        # count all produced products
        for product_type in self.system.production_system.product_types:
            parts_produced[product_type] = 0
            for product in self.system.sink_store.items:
                    if product.product_type == product_type:
                        parts_produced[product_type] += 1
            max_parts_possible[product_type] = math.floor(active_simulation_time/longest_task[product_type])
            production_rate[product_type] =  round(100*(parts_produced[product_type]/max_parts_possible[product_type]))
            lost_parts[product_type] = max_parts_possible[product_type] - parts_produced[product_type]
        
        if self.reward_function.reward_cases is not None:
            msg = "\n\
            Total Reward: {reward}\n\
            Parts Produced: {ppt} / {mppt}\tProduction Rate: {pr}%\n\
            Lost Parts: {lp}\n\
            reward/cost cases: {cc}"\
                        .format(reward=self.reward_function.reward, ppt=parts_produced, mppt=max_parts_possible,
                                pr=production_rate,
                                lp = lost_parts,
                                cc = self.reward_function.reward_cases)
    
            self.logger.info(msg ,extra = {"simtime": self.system.sim_env.now})
        else:
            msg = "\n\
            Total Reward: {reward}\n\
            Parts Produced: {ppt} / {mppt}\tProduction Rate: {pr}%\n\
            Lost Parts: {lp}"\
                        .format(reward=self.reward_function.reward, ppt=parts_produced, mppt=max_parts_possible,
                                pr=production_rate,
                                lp = lost_parts)
    
            self.logger.info(msg ,extra = {"simtime": self.system.sim_env.now})

