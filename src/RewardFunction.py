from abc import ABC, abstractmethod


class RewardFunction(ABC):
    """
    Defines the basic structure of a reward function
    """

    def __init__(self, system_state_converter, initial_reward=0):
        self.reward = initial_reward
        self.system_state_converter = system_state_converter

        self.reward_cases = None

    @classmethod
    @abstractmethod
    def update(self):
        ''' Updates the reward gathered during the simulation. Constructed to be called each simulation step (except for RewardTaskAssignment). '''
        pass


class RewardR1(RewardFunction):
    """ 
    Reward function for policy R1 
    """

    def __init__(self, system_state_converter, initial_reward=0):
        super().__init__(system_state_converter, initial_reward)

    def update(self):
        self.reward = len(self.system_state_converter.sink_store.items)


class RewardR2(RewardFunction):
    """ 
    Reward function for policy R2 
    """

    def __init__(self, system_state_converter, initial_reward=0):

        super().__init__(system_state_converter, initial_reward)

        self.c_cbm = 0.5  # scheduled repair
        self.c_cm = 1.5  # corrective repair
        self.c_pv = 0.1  # loss in each time step during repair

        self.reward_cases = {'idle': 0,
                             'idle_repair_necessary': 0, 'cm': 0, 'cbm': 0}

    def update(self):

        failed, currently_repairing = 0, 0

        for machine in self.system_state_converter.machines:
            if machine.status == 'failed':
                failed += 1
            if machine.status in ['under_repair', 'repair_finished']:
                currently_repairing += 1

        # three cases:
        # case 1: cost for idle if no machine failed
        if failed == 0 and currently_repairing == 0:
            self.reward += 0
            self.reward_cases['idle'] += 1
        # case 2: cost for idle if a machine failed
        elif failed > 0 and currently_repairing == 0:
            self.reward += -(10 * self.c_cbm)  # - 5
            self.reward_cases['idle_repair_necessary'] += 1
        # case 3: cost for repair (predictive cost, corrective cost, loss because of not working machine)
        elif currently_repairing > 0:
            for machine in self.system_state_converter.machines:
                if machine.status in ['under_repair', 'repair_finished'] and machine.repair_type == 'cbm':
                    self.reward += - (self.c_cbm/machine.repair_durations['cbm'] + self.c_pv/(
                        machine.repair_durations['cbm']**2))  # - 0.52
                    self.reward_cases['cbm'] += 1
                elif machine.status in ['under_repair', 'repair_finished'] and machine.repair_type == 'cm':
                    self.reward += - (self.c_cm/machine.repair_durations['cm'] + self.c_pv/(
                        machine.repair_durations['cm']**2))  # - 1.505
                    self.reward_cases['cm'] += 1
                # TODO: cost for repairing a machine that did not request repair?
        else:
            raise Exception(
                'Somehow found an unkown case in the actionbased reward calculation.')
