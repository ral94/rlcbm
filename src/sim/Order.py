from sim.Product import Product
from sim.CoreObject import CoreObject


class Order(CoreObject):
    """
    Order class which can be used to order a certain amount of products with a certain due date.
    """
    def __init__(self, products_to_order, due_date, system, order_date = None):
        
        # system parameters
        self.system = system
        self.production_system = self.system.production_system
        self.source_store = self.system.source_store
        
        self.id = 'O' + str(len(self.system.orders))
        
        # order specific parameters
        # products_to_order is a dict in the form {product_type: amount}
        self.products_to_order = products_to_order
        if order_date is None:
            self.order_date = self.system.sim_env.now
        else:
            self.order_date = order_date
        self.due_date = due_date
        self.finished = False
        
        # put all products in the source store and keep track of them
        self.products = []
        for product_type in self.products_to_order:
            assert product_type in self.system.production_system.product_types, 'Tried to order a product of unsupported type {}, please define in ProductionSystem.'.format(product_type)
            for _ in range(self.products_to_order[product_type]):
                product = Product(product_type = product_type, production_system = self.production_system, order = self, due_date = self.due_date)
                self.source_store.put(product)
                self.products.append(product)
        # if there were no products ordered, stop simulation
        assert len(self.products) > 0, 'Received an order with 0 products in it.'
        
        # track how many items are finished to save time in is_finished()
        self.finished_products = 0
        
        # save this order in the system
        self.system.orders.append(self)
                
    def is_finished(self):
        """ Returns if this order is finished. Once it is finished, it can not go back into an unfinished state. """
        
        if self.finished:
            return True
        if self.finished_products < len(self.products):
            return False
        else:
            for product in self.products:
                if not product.finished:
                    return False
        self.finished = True
        return True