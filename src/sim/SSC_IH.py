import gym
from gym.spaces import utils
import numpy as np

from sim.System import System
from sim.SimulationStateConverter import SimulationStateConverter


class SimulationStateConverterIH(SimulationStateConverter):
    """ 
    SimulationStateConverter for the ih case (maintenance planning), returns machine health and buffer sizes.
    """

    def __init__(self, system: System):
        super().__init__(system)

        self.output_buffer_capacities = []
        # get machine output buffer max sizes
        for machine in self.system.job_shop_machine.keys():
            capacity = self.system.job_shop_machine[machine]['output_buffer_capacity']
            # if maximum size of output buffer is undefined or bigger than production_store capacity, the actual size is limited the to production_store capacity
            if capacity == float('inf') or capacity > self.store_capacity:
                self.output_buffer_capacities.append(self.store_capacity)
            # if it is defined, add it to the list
            else:
                self.output_buffer_capacities.append(capacity)

        self.input_buffer_capacities = [self.sink_store.capacity]
        # get machine output buffer max sizes
        for machine in self.system.job_shop_machine.keys():
            capacity = self.system.job_shop_machine[machine]['output_buffer_capacity']
            # if maximum size of output buffer is undefined or bigger than production_store capacity, the actual size is limited the to production_store capacity
            if capacity == float('inf') or capacity > self.store_capacity:
                self.input_buffer_capacities.append(self.store_capacity)
            # if it is defined, add it to the list
            else:
                self.input_buffer_capacities.append(capacity)
        # remove outputbuffer of last machine (sink_store.capacity)
        self.input_buffer_capacities = self.input_buffer_capacities[:-1]

        # observation contains a list of machine health states and a list of machine output buffer sizes
        spaces = {
            'machine_states': gym.spaces.Box(low=0, high=10, shape=(len(self.machines),), dtype=np.uintc),
            'buffer_sizes': gym.spaces.Box(low=np.zeros(len(self.machines)), high=np.array(self.input_buffer_capacities), shape=(len(self.machines),), dtype=np.uintc),
        }

        self.observation_space = gym.spaces.Dict(spaces)

    def get_observation_dims(self):
        """returns the obervation dims"""
        return utils.flatdim(self.observation_space)

    def system_state_to_observation(self):
        """ Get observation from simpy system"""

        machine_states = []
        buffer_sizes = []
        for machine in self.machines:
            # list all health states
            machine_states.append(machine.health)

            # calculate buffer_sizes
            products_for_machine = 0
            for product in self.production_store.items:
                if machine.can_do_next_task(product):
                    products_for_machine += 1
            buffer_sizes.append(products_for_machine)

        assert(len(machine_states) == len(self.machines))
        assert(len(buffer_sizes) == len(self.machines))

        observation = {
            'machine_states': machine_states,
            'buffer_sizes': buffer_sizes,
        }

        return utils.flatten(self.observation_space, observation)
