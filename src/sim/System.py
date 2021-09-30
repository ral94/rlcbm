import logging
import simpy

from sim.Machine import Machine
from sim.Schedule import Schedule
from sim.Clock import Clock
from sim.OrderGenerator import OrderGenerator


class System():
    """
    Manufacturing system class
    # :param maintenace_plan: list, in form (loc, time, duration)
    # :param maintenance costs: dict,  of costs by job type
    """

    def __init__(self, use_case, production_system):
        ''' Sets up the general system structure. Supposed to be called exactly once at the beginning of training.'''

        self.logger = logging.getLogger("factory_sim")

        # use case: 'ih'
        self.use_case = use_case

        if use_case == 'ih':
            self.logger.info(
                'Using this system for maintenance planning.', extra={'simtime': 0})
            assert production_system.degradation_on, 'Simulating maintenance planning (use_case = {}) without degradation will not do a lot.'.format(
                use_case)
        else:
            assert False, 'Can not generate system with unknown use_case {}.'.format(
                use_case)

        # production_system params
        self.production_system = production_system
        self.tasks = self.production_system.tasks

        # set switches to turn parts of the simulation on or off
        self.weekend_on = self.production_system.weekend_on
        self.degradation_on = self.production_system.degradation_on

        # get machines from production_system
        self.job_shop_machine = self.production_system.job_shop_machine

        self.store_capacity = sum([self.production_system.job_shop_machine[machine]['output_buffer_capacity']
                                  for machine in self.production_system.job_shop_machine.keys()])

        # maximum number of simultaneous maintenance processes
        self.maintenance_capacity = self.production_system.maintenance_capacity

        # simulation parameters
        self.simulation_time = 400

        # part of a timestep which delays or prepones parts of the simulation
        self.epsilon = 0.00001

        # schedule/shift parameters
        # unit here is one hour, initial hour 0 is 6 o'clock on monday
        # hours described by their start -> hour 4 is from (6+4=) 10 to 11
        # in hours, works for anything that divides 8 (8 % stepduration = 0)
        self.step_duration = 1
        self.work_end_sat = 14  # ending time on saturday
        self.work_start_mon = 6  # starting time on monday

        # Order_Generator params
        self.order_type = 'start'
        self.order_list = None
        self.order_probability_step = None
        self.items_per_type = 500

        # initialize system object
        self.initialize()
        self.logger.debug("System successfully initialized",
                          extra={"simtime": self.sim_env.now})

    def initialize(self):
        """ Initializes the system for simulation. New simpy.Environment per simulation is needed.
        This method is supposed to be called in the SimEnv.reset(), every time a new episode starts."""

        self.sim_env = simpy.Environment()

        # initialize weekly Schedule
        self.weekly_schedule = Schedule(
            self.sim_env, self.step_duration, self.work_start_mon, self.work_end_sat, weekend_on=self.weekend_on)

        if self.weekend_on:
            # initialize Clock
            self.clock = Clock('C0', self, self.step_duration)

        # at the start of the simulation, all maintenance resources are available
        self.available_maintenance = self.maintenance_capacity

        # for FIFO list of all machines that want to be repaired
        self.machines_to_repair = []

        # set up filtered stores as source, items in production (output buffers) and sink
        self.source_store = simpy.FilterStore(
            env=self.sim_env, capacity=float('inf'))
        self.production_store = simpy.FilterStore(
            env=self.sim_env, capacity=self.store_capacity)
        self.sink_store = simpy.FilterStore(
            env=self.sim_env, capacity=float('inf'))

        # generate products or process to create products
        self.orders = []
        self.order_generator = OrderGenerator(system=self, order_type=self.order_type,
                                              order_probability_step=self.order_probability_step, order_list=self.order_list, items_per_type=self.items_per_type)

        # infere the jobshop layout
        self.machines = []
        for m in self.job_shop_machine.keys():
            machine = Machine(id=self.job_shop_machine[m]["id"], system=self, machine_type=self.job_shop_machine[m]["machine_type"],
                              output_buffer_capacity=self.job_shop_machine[m]["output_buffer_capacity"])
            self.machines.append(machine)
