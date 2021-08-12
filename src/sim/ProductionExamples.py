import numpy as np
from collections import OrderedDict

from sim.ProductionSystem import ProductionSystem


class ProductionSystem1(ProductionSystem):
    """ 
    A production System with high variation in degradation rate, process time and buffer capacity.
    """
    product_types = ['A']
    tasks_for_product = {'A': ['P0','P1','P2','P3','P4']}

    maintenance_capacity = 1
    
    weekend_on = False
    degradation_on = True

    repair_durations = {'cm': 20, 'cbm': 5}
    machine_types = ({
        'MT00': {'tasks': {'P0': 1}, 'degradation_rate': 0.1, 'repair_durations': repair_durations},
        'MT01': {'tasks': {'P1': 2}, 'degradation_rate': 0.4, 'repair_durations': repair_durations},
        'MT02': {'tasks': {'P2': 2}, 'degradation_rate': 0.25, 'repair_durations': repair_durations},
        'MT03': {'tasks': {'P3': 4}, 'degradation_rate': 0.15, 'repair_durations': repair_durations},
        'MT04': {'tasks': {'P4': 5}, 'degradation_rate': 0.2, 'repair_durations': repair_durations}
    })
    
    job_shop_machine = OrderedDict({
        "M0" : {"id": 'M0', "machine_type": 'MT00', 'output_buffer_capacity': 5},
        "M1" : {"id": 'M1', "machine_type": 'MT01', 'output_buffer_capacity': 4},
        "M2" : {"id": 'M2', "machine_type": 'MT02', 'output_buffer_capacity': 2},
        "M3" : {"id": 'M3', "machine_type": 'MT03', 'output_buffer_capacity': 2},
        "M4" : {"id": 'M4', "machine_type": 'MT04', 'output_buffer_capacity': float('inf')}
    })


class ProductionSystem2(ProductionSystem):
    """
    A production System with no variation in degradation rate, process time and buffer capacity.
    """

    product_types = ['A']
    tasks_for_product = {'A': ['P0','P1','P2','P3','P4']}

    maintenance_capacity = 1
    
    weekend_on = False
    degradation_on = True

    repair_durations = {'cm': 20, 'cbm': 5}
    degradation_rate = 0.25
    machine_types = ({
        'MT00': {'tasks': {'P0': 2}, 'degradation_rate': degradation_rate, 'repair_durations': repair_durations},
        'MT01': {'tasks': {'P1': 2}, 'degradation_rate': degradation_rate, 'repair_durations': repair_durations},
        'MT02': {'tasks': {'P2': 2}, 'degradation_rate': degradation_rate, 'repair_durations': repair_durations},
        'MT03': {'tasks': {'P3': 2}, 'degradation_rate': degradation_rate, 'repair_durations': repair_durations},
        'MT04': {'tasks': {'P4': 2}, 'degradation_rate': degradation_rate, 'repair_durations': repair_durations}
    })
    
    job_shop_machine = OrderedDict({
        "M0" : {"id": 'M0', "machine_type": 'MT00', 'output_buffer_capacity': 2},
        "M1" : {"id": 'M1', "machine_type": 'MT01', 'output_buffer_capacity': 2},
        "M2" : {"id": 'M2', "machine_type": 'MT02', 'output_buffer_capacity': 2},
        "M3" : {"id": 'M3', "machine_type": 'MT03', 'output_buffer_capacity': 2},
        "M4" : {"id": 'M4', "machine_type": 'MT04', 'output_buffer_capacity': float('inf')}
    })