class Product:
    """
     Product to be produced during the simulation
    """
    def __init__(self, product_type, production_system, order, due_date=None, previous_task=None, previous_machine=None):
        
        self.product_type = product_type
        self.production_system = production_system
        self.order = order
        
        self.finished = False
        self.previous_machine = previous_machine
        self.previous_task = previous_task
        self.finish_current_task()
        
        self.due_date = due_date
        
    def finish_current_task(self):
        """ Moves the product one task ahead in its production process."""
        # for instatiating the product
        if self.previous_task == None:
            self.next_task = self.production_system.tasks_for_product[self.product_type][0]
            #return self.next_task
        else:
            number_of_tasks = len(self.production_system.tasks_for_product[self.product_type])
            for i in range(0,number_of_tasks):
                # when previous_task is task at i-th step, set i+1-th task as next_task
                if self.previous_task == self.production_system.tasks_for_product[self.product_type][i]:
                    #if previous_task was last task, set product as finished, next_task as None
                    if i == number_of_tasks - 1:
                        self.next_task = None
                        self.finished = True
                        #return self.next_task
                    else:
                        self.next_task = self.production_system.tasks_for_product[self.product_type][i+1]
                        #return self.next_task