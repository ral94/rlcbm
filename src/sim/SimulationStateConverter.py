from abc import ABC, abstractmethod

from sim.System import System


class SimulationStateConverter(ABC):
    """ 
    Converting system state to an observation matching the defined space.
    """
    def __init__(self, system:System):
        
        self.system = system
        self.production_system = self.system.production_system
        self.machines = self.system.machines
        self.source_store = self.system.source_store
        self.production_store = self.system.production_store
        self.store_capacity = self.system.store_capacity
        self.sink_store = self.system.sink_store
        
        self.tasks = self.system.tasks
        
        # variable to save when the method get_available_tasks() was called for the last time (used to save runtime)
        self.last_called_available_tasks = None

    
    @classmethod
    @abstractmethod
    def system_state_to_observation(self):
        """ Get observation from simpy system"""
        pass

    
    def get_machine_buffers(self):
        ''' returns the output buffers of all machines as a dict '''
        buffer_sizes = {}
        for machine in self.system.machines:
            buffer_sizes[machine.id] = machine.calculate_output_buffer_size()
        return buffer_sizes
    
    def get_due_dates(self):
        ''' returns a list with all product due_dates in the system '''
        
        due_dates = []
        # count all products of all orders (-> also consider products that are currently in machines and not in stores)
        # possible: could adapt this method to not look at products but at orders
        for order in self.system.orders:
            for product in order.products:
                due_dates.append(product.due_date)
        return due_dates
    
    def get_machine_status(self):
        ''' returns dict with status: #machines '''
        status = {None: 0, 'working': 0, 'waiting': 0, 'failed': 0, 'weekend': 0, 'under_repair': 0, 'scheduled_maintenance': 0, 'repair_finished': 0}
        for machine in self.system.machines:
            assert(machine.status in status)
            status[machine.status] += 1
        return status
    
    def get_available_maintenance(self):
        return self.system.available_maintenance
    
    def get_simulation_step(self):
        return self.system.sim_env.now