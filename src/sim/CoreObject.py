import logging


class CoreObject():
    '''
    Basic object to use in simulation, provides a simple constructor.
    '''

    def __init__(self, id, system):
        self.id = id
        self.system = system
        self.production_system = system.production_system
        self.use_case = system.use_case
        self.sim_env = system.sim_env
        self.weekly_schedule = system.weekly_schedule
        self.logger = logging.getLogger("factory_sim")
