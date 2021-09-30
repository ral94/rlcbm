import random
from sim.Order import Order


class OrderGenerator:
    """ 
    provides methods to either fill the source_store with items at the start of a simulation or create a process
    that fills the given store during the simulation
    """

    def __init__(self, system, order_type, order_list=None, order_probability_step=None, items_per_type=100):
        self.system = system

        if order_type == 'start':
            if order_list is None:
                self.generate_starting_order_alternating(items_per_type)
            else:
                self.generate_starting_order_by_list(order_list)
        elif order_type == 'process':
            assert not (
                order_list is None and order_probability_step is None), 'Tried to generate order_process, did not get order_list or order_probability_step.'
            assert not (
                order_list is not None and order_probability_step is not None), 'Tried to generate order_process, did get order_list AND order_probability_step.'
            if order_list is not None:
                self.system.sim_env.process(
                    self.generate_order_process_list(order_list))
            if order_probability_step is not None:
                self.system.sim_env.process(
                    self.generate_order_process_probability(order_probability_step))
        else:
            assert False, 'The given order type is not supported.'

    def generate_starting_order_by_list(self, order_list):
        """ fills the source_store with all the products given in the order_list while ignoring the put_date """
        # order_list is a list of triples (put_date, due_date, dict{product_type: amount})
        for tup in order_list:
            Order(products_to_order=tup[2], due_date=tup[1],
                  system=self.system, order_date=0)

    def generate_starting_order_alternating(self, items_per_type):
        """ fills the source_store with items_per_type items in alternating order with random due_dates """
        for product_type in self.system.production_system.product_types:
            for _ in range(0, items_per_type):
                Order({product_type: 1}, due_date=random.randint(
                    10, self.system.simulation_time), system=self.system, order_date=0)

    def generate_order_process_probability(self, order_probability_step):
        """creates a process that runs during the simulation that puts items in the source_store at random
        (with order_probability_step {product_type: chance to be ordered in each step})"""
        while True:
            products_to_order = {}
            order_something = False
            # TODO: change this filler process to own random process of receiving orders
            # amount = random.randint(1,10)
            # if chance hits, put a product in the source_store
            for product_type in self.system.production_system.product_types:
                assert product_type in order_probability_step, 'Found a product type in the system without a probability of being ordered.'
                # TODO: could integrate putting more than one item per product_type in each step
                rand = random.random()
                if rand < order_probability_step[product_type]:
                    products_to_order[product_type] = 1
                    order_something = True
            if order_something:
                due_date = random.randint(
                    self.system.sim_env.now, self.system.simulation_time)
                Order(products_to_order=products_to_order, due_date=due_date,
                      system=self.system, order_date=self.system.sim_env.now)
            yield self.system.sim_env.timeout(1)

    def generate_order_process_list(self, order_list):
        """ creates a process that runs during the simulation that puts items in the source_store
        based on a given list of triples (put_date, due_date, {product_type: amount}) """
        # put products in order_list in the source_store at their put_date
        while True:
            self.system.logger.debug('Order_list: {}'.format(order_list), extra={
                                     'simtime': self.system.sim_env.now})
            for tup in order_list:
                if tup[0] == self.system.sim_env.now:
                    Order(products_to_order=tup[2], due_date=tup[1],
                          system=self.system, order_date=self.system.sim_env.now)
                    #self.store.put(Product(product_type=tup[2], production_system=self.system.production_system, due_date=tup[1]))
                    self.system.logger.debug('Put order {} with due_date {}'.format(
                        tup[2], tup[1]), extra={'simtime': self.system.sim_env.now})
                    # order_list.remove(tup)
            yield self.system.sim_env.timeout(1)
