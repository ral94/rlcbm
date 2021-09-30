import gym
from typing import Tuple

from sim.System import System
from sim.SSC_IH import SimulationStateConverterIH
from SimEnv import SimEnv

from RewardFunction import RewardR1, RewardR2


class SimEnvIH(SimEnv):
    """ 
    Wrapper for simulation model as gym environment
    """

    def __init__(self, system: System):
        super().__init__(system)

        # action, observation space
        # action: maintenance machine n; n+1: do nothing
        self.num_actions = len(self.system.machines)+1
        self.action_space = gym.spaces.Discrete(self.num_actions)

        self.system_state_converter = SimulationStateConverterIH(self.system)
        self.observation_space = self.system_state_converter.observation_space

        self.logger.debug("SimEnv_IH created \nAction_space: {} \nObservation space: {}"
                          .format(self.action_space, self.observation_space), extra={"simtime": self.system.sim_env.now})

        # if you change the reward function here, make sure to change it in 'reset(self)' as well
        self.reward_function = RewardR2(self.system_state_converter)
        #self.reward_function = RewardR1(self.system_state_converter)

    def reset(self):
        """
        Gym interface method: reset
        Initializes the environment and runs until the first decision point 
        is reached.
        :return initial_observation: np.array, initial state space
        """
        # reset system, simulation state converter and reward function
        self.system.initialize()
        self.system_state_converter = SimulationStateConverterIH(self.system)
        self.reward_function = RewardR2(self.system_state_converter)
        #self.reward_function = RewardR1(self.system_state_converter)

        # reset variables
        self.done = False
        self.sim_counter = 1
        self.maintenance_requested = False
        self.previous_reward = 0

        self.logger.debug("Reset done", extra={
                          "simtime": self.system.sim_env.now})

        # perform first simulation
        self.next_sim_step()
        # update variables for reward calculation
        _ = self._get_reward()

        initial_observation = self._get_observation()

        return initial_observation

    def step(self, action: object) -> Tuple[object, float, bool, dict]:
        """
        Gym interface method: step
        Takes action and executes simulation until next action is needed
        :param action: int, represents maintenance machine n; n+1: do nothing
        """

        # Reset required_maintenance variable
        self.maintenance_requested = False

        # execute action
        self.execute_action(action)

        # run simulation until next decision point
        self.next_sim_step()

        # run model
        done = self._check_if_model_is_done()
        reward = self._get_reward()

        # collect information to return to agent
        observation = self._get_observation()
        info = self._get_info()

        # final output when simulation is done
        if done:
            self._log_summary()

        return (observation, reward, done, info)

    def next_sim_step(self):
        """ Performs a simulation until next decision point is reached """
        # Perform steps until maintenance available and required
        while self.system.available_maintenance <= 0 or self.maintenance_requested == False:
            # Check if simulation time is reached and exit if it is
            self.done = self._check_if_model_is_done()
            if self.done:
                break

            # perform one step
            self.system.sim_env.run(until=self.sim_counter)
            self.sim_counter += 1

            # Check if maintenance is required after this step
            for machine in self.system.machines:
                if machine.request_maintenance:
                    self.maintenance_requested = True

            # calculate reward/costs of this step
            self.reward_function.update()

    def execute_action(self, action):
        """
        Executes the agents action in the factory simulation
        :param action: int,  numerival value of action chosen by the agent
        """

        if action == self.action_space.n-1:
            self.logger.debug("Action Idle chosen", extra={
                              "simtime": self.system.sim_env.now})
            return

        # select machine based on action
        machine = self.system.machines[action]

        self.logger.debug("Action Maintain {} choosen".format(
            machine.id), extra={"simtime": self.system.sim_env.now})

        # Differentiation necessary if interruption due to degrading or CBM
        # Degradation stopped on weekend, this case only appears in work time
        if machine.interrupt_origin == 'from_degrade':
            machine.repair_type = 'cm'
            machine.assigned_maintenance = True
            machine.status = 'under_repair'
            return machine.sim_env.process(machine.maintain())

        else:
            # Parameter to decide from what origin the interruption comes from
            # case for weekend, scheduled maintenace on weekend is possible
            machine.repair_type = 'cbm'
            machine.interrupt_origin = 'from_scheduler'
            machine.assigned_maintenance = True
            machine.process.interrupt(cause="from_scheduler")

        return
