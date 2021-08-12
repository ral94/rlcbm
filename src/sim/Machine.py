from numpy.core.numeric import _frombuffer
import simpy
import numpy as np
from sim.CoreObject import CoreObject


class Machine(CoreObject):
    """ Machine as state machine """
    def __init__(self, id, system, machine_type, output_buffer_capacity):
        
        super().__init__(id, system)
        
        # machine properties
        self.output_buffer_capacity = output_buffer_capacity
        self.machine_type = machine_type
        self.tasks = self.production_system.machine_types[self.machine_type]['tasks']
        
        # if necessary, set degradation properties
        if self.system.degradation_on:
            self.repair_durations = self.production_system.machine_types[self.machine_type]['repair_durations']
            self.degradation = self._generate_degradation_matrix(self.production_system.machine_types[self.machine_type]['degradation_rate'])
            self.failed_state = len(self.degradation)-1
            self.request_maintenance = False
        self.interrupt_origin = None

        # set initial machine state
        self.health = 0
        self.failed = False
        self.status = None # current values:'working', 'waiting', 'failed', 'weekend', 'under_repair', 'scheduled_maintenance', 'repair_finished'
        
        self.product = None
        self.assigned_task = None
        self.production_state = 'waiting_for_product_assignment'
        self.starting_machine = False
        
        self.epsilon = self.system.epsilon
        
        # set the production_store as default, for starting_machine decide separately in working()
        self.store = self.system.production_store
        # check if machine can start new products and which tasks can be run on this machine
        # for each product type
        for product_type in self.production_system.product_types:
            # get first task for product type
            first_task = self.production_system.tasks_for_product[product_type][0]
            # if this machine can do the first task of a product type, set it as a starting machine
            if first_task in self.tasks:
                self.starting_machine = True
                self.logger.debug('{} can start products'.format(self.id), extra={"simtime": self.sim_env.now})
                break
                
        # Threshold where machine requests CBM
        self.CBM_threshold=6
        # set maintenance request and repair_type based on initial health
        if self.CBM_threshold <= self.health < 10:
            self.request_maintenance = True
            self.repair_type = 'CBM'
        elif self.health == 10:
            self.request_maintenance = True
            self.repair_type = 'CM'
            self.failed = True
        else:
            self.request_maintenance = False
            self.repair_type = None
       
        # production state
        self.remaining_process_time = 1 # arbitrary value != 0
        self.parts_made = 0
        
        self.process = self.sim_env.process(self.working())
        if self.system.degradation_on:
            self.failing = self.sim_env.process(self.degrade())

    def can_do_next_task(self, product):
        """ checks if this machine can do the next task of a given product """
        if product.next_task in self.tasks:
            return True
        else:
            return False
        
    def needs_task_assignment(self):
        """ checks if this machine currently needs to have a new task assigned """
        # task needs to be assigned if there is no assigned task, no product and machine is ready to work
        if self.product is None and self.assigned_task is None and self.status in ['waiting','working','repair_finished', None]:
            return True
        else:
            return False
        
    def find_minimum_due_date(self, store):
        """ returns the minimal due_date of all products in this store that can be processed by this machine """
        min_due_date = float('inf')
        for product in store.items:
            if product.due_date is not None:
                if self.can_do_next_task(product):
                    if product.due_date < min_due_date:
                        min_due_date = product.due_date
        self.logger.debug('{} found minimum due date: {}'.format(self.id, min_due_date), extra={'simtime': self.sim_env.now})
        return min_due_date
    
    def find_minimum_due_date_task(self, store, task):
        """ returns the minimal due_date of all products in this store which need the given task next """
        min_due_date = float('inf')
        for product in store.items:
            if product.due_date is not None:
                if product.next_task == task:
                    if product.due_date < min_due_date:
                        min_due_date = product.due_date
        self.logger.debug('{} found minimum due date: {}'.format(self.id, min_due_date), extra={'simtime': self.sim_env.now})
        return min_due_date
    
    def calculate_output_buffer_size(self):
        """ returns the current amount of items in the buffer behind this machine (always based on the production store) """
        output_buffer_size = 0
        for product in self.system.production_store.items:
            if product.previous_machine == self.id:
                output_buffer_size += 1
        return output_buffer_size

    def working(self):
        """ Machine processes parts until interrupted by failure. See the documentation for further explanation. """
        while True:
            self.logger.debug("{} Machine.working() started, status: {}".format(self.id, self.status), extra = {"simtime": self.sim_env.now})
            try:
                # if this machine is ready to work on a product
                if self.status in [None, 'working', 'waiting', 'repair_finished']:
                    # first assign a product
                    if self.production_state == 'waiting_for_product_assignment':
                        self.status = 'waiting'
                        
                        if self.use_case == 'ih':
                            # if this machine can start products of a type
                            if self.starting_machine:
                                # if there are items in the production store this machine can use, use production_store, else use source_store
                                if self.find_minimum_due_date(self.system.production_store) != float('inf'):
                                    self.store = self.system.production_store
                                else:
                                    self.store = self.system.source_store
                                    
                            # retrieve item whose next step can be done by this machine
                            # if there is currently an object in the store for which this machine can do the next task, retrieve it
                            due_date = self.find_minimum_due_date(self.store)
                            if due_date != float('inf'):
                                with self.store.get(filter=lambda product: self.can_do_next_task(product) and product.due_date == due_date) as get_request:
                                    self.product = yield get_request
                            # if there is no object in the store for which this machine can do the next step, wait for one
                            else:
                                with self.store.get(filter=lambda product: self.can_do_next_task(product)) as get_request:
                                    self.product = yield get_request
                            
                        # set process time here to not have it begin anew if the machine gets interrupted during processing a part
                        self.remaining_process_time = self.tasks[self.product.next_task]
                        self.logger.debug("{} Part from store assigned, type {}, due_date: {}, task: {}".format(self.id,
                            self.product.product_type, self.product.due_date, self.product.next_task), extra = {"simtime": self.sim_env.now})
                        
                        self.production_state = 'processing_part'
                    
                    # process part
                    if self.production_state == 'processing_part':
                        self.status = 'working'
                        
                        # wait for what is left of the remaining_process_time
                        while self.remaining_process_time:
                            self.logger.debug('{} working on product of type {} and due_date {}, time left : {}'.format(self.id, self.product.product_type, self.product.due_date, self.remaining_process_time), extra = {'simtime': self.sim_env.now})
                            if self.remaining_process_time == self.tasks[self.product.next_task]:
                                yield self.sim_env.timeout(1 - self.epsilon)
                            else:
                                yield self.sim_env.timeout(1)
                            self.remaining_process_time -= 1
                        
                        yield self.sim_env.timeout(self.epsilon)
                        self.logger.debug('{} finished working on product of type {} and due_date {}'.format(self.id, self.product.product_type, self.product.due_date), extra = {'simtime': self.sim_env.now})
                        
                        # 'tell' the product this task was finished
                        self.product.previous_machine = self.id
                        self.product.previous_task = self.product.next_task
                        self.product.finish_current_task()
                        
                        # if the product is finished, put it in the sink_store
                        if self.product.finished:
                            self.production_state = 'putting_product_in_sink_store'
                        # if the product is not finished, wait for space in the output buffer
                        else:
                            self.production_state = 'waiting_for_output_buffer'
                    
                    # wait until there is space in the output buffer
                    if self.production_state == 'waiting_for_output_buffer':
                        self.status = 'waiting'
                        
                        # wait until there is space in the output buffer, only if the output buffer is limited
                        while self.output_buffer_capacity != float('inf') and self.calculate_output_buffer_size() >= self.output_buffer_capacity:
                            self.logger.debug('{} waiting for space in output buffer of capacity {}, product of type {} and due_date {}'.format(self.id,
                                self.output_buffer_capacity, self.product.product_type, self.product.due_date), extra = {'simtime': self.sim_env.now})
                            yield self.sim_env.timeout(1)
                            
                        # if there is space in the output buffer, put the product there
                        self.production_state = 'putting_product_in_output_buffer'
                    
                    # put part in production_store which simulates output buffers
                    # should be guaranteed that there is space in the output_buffer (and production_store) due to previously waiting for space
                    if self.production_state == 'putting_product_in_output_buffer':                        
                        self.status = 'waiting'
                                                
                        # since there is space in the output_buffer, there should be space in the production_store, so just put item there
                        with self.system.production_store.put(self.product) as put_request:
                            self.logger.debug("{} put item in production store, date {}, task {}, inventory {}".format(self.id,
                                self.product.due_date, self.product.next_task, len(self.system.production_store.items)), extra = {"simtime": self.sim_env.now})
                            self.product = None
                            yield put_request
                        
                        self.logger.debug('{} finished putting part in the production_store'.format(self.id), extra = {'simtime': self.sim_env.now})
                        # log the completion of this part
                        self.parts_made += 1
                        # set this to be ready for the next part
                        self.product_arrived = False
                        
                        # go back to the start of the production process
                        self.production_state = 'waiting_for_product_assignment'
                    
                    # put part in sink_store if it is finished
                    if self.production_state == 'putting_product_in_sink_store':
                        self.status = 'waiting'
                        
                        # since there is always space in the sink_store, just put item there
                        with self.system.sink_store.put(self.product) as put_request:
                            # infinite capacity, can delete object before putting it
                            self.logger.debug("{} put item in sink store, date {}, task {}, inventory {}".format(self.id,
                                self.product.due_date, self.product.next_task, len(self.system.sink_store.items)), extra = {"simtime": self.sim_env.now})
                            # update the corresponding order
                            self.product.order.finished_products += 1
                            self.product = None
                            yield put_request
                            
                        # log the completion of this part
                        self.parts_made += 1
                        # set this to be ready for the next part
                        self.product_arrived = False
                        
                        # go back to the start of the production process
                        self.production_state = 'waiting_for_product_assignment'

                elif self.status == 'failed':
                    # self.logger.debug('{} status {}'.format(self.id, self.status), extra = {'simtime': self.sim_env.now})
                    yield self.sim_env.timeout(1)
                
                elif self.status == 'weekend':
                    # self.logger.debug('{} status {}'.format(self.id, self.status), extra = {'simtime': self.sim_env.now})
                    yield self.sim_env.timeout(1)
                
                elif self.status == 'scheduled_maintenance':
                    # self.logger.debug('{} status {}'.format(self.id, self.status), extra = {'simtime': self.sim_env.now})
                    yield self.sim_env.process(self.maintain())
                    # self.logger.debug('{} status {} finished maintenance'.format(self.id, self.status), extra = {'simtime': self.sim_env.now})
                
                elif self.status == 'under_repair':
                    # self.logger.debug('{} status {}'.format(self.id, self.status), extra = {'simtime': self.sim_env.now})
                    yield self.sim_env.timeout(1)
      
            except simpy.Interrupt as interrupt:
                
                self.logger.debug('{} Interrupted while status {} and with cause {}'.format(self.id, self.status, interrupt.cause), extra = {'simtime': self.sim_env.now})
                if interrupt.cause == 'from_degrade':
                    self.status = 'failed'
                    self.logger.debug('{} set status to failed'.format(self.id), extra = {'simtime': self.sim_env.now})
                elif interrupt.cause == 'from_clock':
                    self.status = 'weekend'
                    self.logger.debug('{} set status to weekend'.format(self.id), extra = {'simtime': self.sim_env.now})
                elif interrupt.cause == 'from_scheduler':
                    self.status = 'scheduled_maintenance'
                    self.logger.debug('{} set status to scheduled_maintenance'.format(self.id), extra = {'simtime': self.sim_env.now})

    def maintain(self):
        """ Machine gets maintained. Duration is based on repair_type """

        self.logger.debug("{} Machine.maintain() started".format(self.id), extra = {"simtime": self.sim_env.now})
        
        # break loop once scheduled for maintenance
        self.request_maintenance = False

        # stop degradation during maintenance and occupy maintenance resource
        self.status = 'under_repair' 
        self.system.available_maintenance -= 1

        # set time to repair based on repair_type
        self.time_to_repair = self.repair_durations[self.repair_type]
        
        # wait for repair to finish
        for i in range(self.time_to_repair):
            if i < self.time_to_repair - 1:
                try:
                    self.logger.debug('{} is maintaining, time left: {}'.format(self.id, self.time_to_repair - i), extra={'simtime': self.sim_env.now})
                    yield self.sim_env.timeout(1)
                except simpy.Interrupt:
                    # ignore interruptions, repair time is fixed
                    yield self.sim_env.timeout(1)
            else:
                try:
                    self.logger.debug('{} is maintaining, shorter timeout, time left: {}'.format(self.id, self.time_to_repair - i), extra={'simtime': self.sim_env.now})
                    yield self.sim_env.timeout(1-self.epsilon)
                except simpy.Interrupt:
                    # ignore interruptions, repair time is fixed
                    yield self.sim_env.timeout(1-self.epsilon)
            
        # release maintenance resource before waiting for monday
        self.system.available_maintenance += 1
        self.maintenance_request = None
        
        # declare machine repaired
        self.health = 0
        self.failed = False
        
        # reset interrupt_origin
        self.interrupt_origin = None
        if not self.weekly_schedule.is_it_worktime():
            self.logger.debug("{} maintenace finished -> weekend".format(self.id), extra={"simtime": self.sim_env.now})
            self.status = 'weekend'
        else:
            self.logger.debug("{} maintenace finished -> working".format(self.id), extra={"simtime": self.sim_env.now})
            self.status = 'repair_finished'
        self.logger.debug("{} Machine.maintain() completed".format(self.id), extra = {"simtime": self.sim_env.now})
        yield self.sim_env.timeout(self.epsilon)
         
    def degrade(self):
        """ Machine degrades based on a discrete state Markovian degradation process. """

        while True:
            try:
                yield self.sim_env.timeout(self.epsilon)
                if self.status in [None, 'working']:
                    self.logger.debug("{} Machine.degrade() started with status: {}".format(self.id, self.status), extra = {"simtime": self.sim_env.now})
                    # yield self.sim_env.timeout(1)
                    # sample next health state based on transition matrix
                    states = np.arange(0, self.failed_state+1)
                    self.health = np.random.choice(states, p=self.degradation[self.health])                            
    
                    # machine fails                
                    if ((self.health == self.failed_state) and (not self.failed)):
                        self.failed = True
                        self.request_maintenance = True
                        if self not in self.system.machines_to_repair:
                            self.system.machines_to_repair.append(self)
                        self.logger.debug("{} Worn out. Product is {}".format(self.id, self.product), extra = {"simtime": self.sim_env.now})
                        # variable to decide where the interruption comes from
                        self.interrupt_origin = 'from_degrade'
                        self.repair_type = "CM"
                        self.process.interrupt(cause="from_degrade")
                        
                    elif ((self.health >= self.CBM_threshold)
                        and (not self.failed)
                        and (not self.request_maintenance)):
                        # CBM threshold reached, request repair
                        self.request_maintenance = True
                        if self not in self.system.machines_to_repair:
                            self.system.machines_to_repair.append(self)
                        self.repair_type = "CBM"
                    
                    self.logger.debug("{} Machine.degrade() completed".format(self.id), extra = {"simtime": self.sim_env.now})
                    yield self.sim_env.timeout(1)

                else:
                    #self.logger.debug("{} did not degrade because status is {}".format(self.id, self.status), extra = {"simtime": self.sim_env.now})
                    yield self.sim_env.timeout(1)
            except simpy.Interrupt as interrupt:
                # interruptions to degrade should not happen at all
                self.logger.debug("{} Degradation interrupted by {}".format(self.id, interrupt.cause), extra = {"simtime": self.sim_env.now})
                

    def _generate_degradation_matrix(self, q, dim=10):
        """
        Creates discrete Markovian degradation matrix with given degradation rate 
        :param q: int, degradation rate
        :param dim: int, number of degradation states 
        :return: np.array, degradation matrix
        """
        degradation_matrix = np.eye(dim)
        for i in range(len(degradation_matrix)-1):
            degradation_matrix[i, i] = 1 - q
            degradation_matrix[i, i+1] = q

        return degradation_matrix
    
    def __repr__(self):
        return "%s"  %(self.id)