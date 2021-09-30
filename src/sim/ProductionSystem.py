import logging
from abc import ABC, abstractmethod


class ProductionSystem(ABC):
    """
    Provides the structure of the factory for simulation.
    """

    @property
    @abstractmethod
    def maintenance_capacity(self):
        # int with maximum number of simultaneous maintenance processes
        pass

    @property
    @abstractmethod
    def product_types(self):
        # list of product_types
        pass

    @property
    @abstractmethod
    def tasks_for_product(self):
        # dict: {product_type: [task1, task2, ...]}
        pass

    @property
    @abstractmethod
    def machine_types(self):
        # nested dict based on machine types and their specifications:
        # {machine_type: {'tasks': {task: duration}, 'degradation_rate': float, 'repair_durations': {'cm': int, 'cbm': int}}}
        pass

    @property
    @abstractmethod
    def job_shop_machine(self):
        # nested OrderedDict with all machines in the simulation:
        # {machine_id: {'id': id, 'machine_type': machine_type, 'output_buffer_capacity': int}}
        pass

    @property
    @abstractmethod
    def weekend_on(self):
        # switch to turn weekends in system on or off (machines do not work on weekends, but may be maintained)
        pass

    @property
    @abstractmethod
    def degradation_on(self):
        # switch to turn degradation in system on or off (only useful for mbs_case)
        pass

    def __init__(self):
        ''' infer all used tasks, check defined system for basic correctness and log its summary '''
        self.infer_tasks()
        self.log_summary()

    def infer_tasks(self):
        ''' infer all used (!) tasks in the system '''
        self.tasks = []
        # find all tasks that are actually used for the defined products
        for product_type in self.tasks_for_product.keys():
            for task in self.tasks_for_product[product_type]:
                if task not in self.tasks:
                    self.tasks.append(task)
        # keep tasks in sorted order to make interpretation of agent output easier
        self.tasks.sort()

    def log_summary(self):
        ''' logs a simple summary of the production system to be simulated '''
        self.logger = logging.getLogger("factory_sim")

        self.logger.info(
            '##############################################', extra={'simtime': 0})
        self.logger.info('System summary:', extra={'simtime': 0})
        if self.degradation_on:
            self.logger.info('Maintenance capacity: {}'.format(
                self.maintenance_capacity), extra={'simtime': 0})
        self.logger.info('tasks used in the factory:', extra={'simtime': 0})
        self.logger.info('{}'.format(self.tasks), extra={'simtime': 0})
        self.logger.info(
            'product types with corresponding tasks:', extra={'simtime': 0})
        for product_type in self.tasks_for_product.keys():
            self.logger.info('{}: {}'.format(
                product_type, self.tasks_for_product[product_type]), extra={'simtime': 0})
        self.logger.info('machines:', extra={'simtime': 0})
        for machine in self.job_shop_machine:
            self.logger.info('{}: {}'.format(
                machine, self.job_shop_machine[machine]), extra={'simtime': 0})

        self.logger.info('work paused on weekends: {}'.format(
            self.weekend_on), extra={'simtime': 0})
        self.logger.info('machines degrade: {}'.format(
            self.degradation_on), extra={'simtime': 0})
        self.logger.info(
            '##############################################', extra={'simtime': 0})
