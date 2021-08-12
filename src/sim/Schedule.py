import logging


class Schedule:
    """
    Uses simulation parameters to set up weekly schedule to provide methods to check for work-time/weekend.
    """
    def __init__(self, sim_env, step_duration, work_start_mon, work_end_sat, weekend_on=True):
        self.sim_env = sim_env
        self.step_duration = step_duration
        self.steps_per_week = int(168 / step_duration)
        self.steps_per_day = int(24 / step_duration)
        
        # parameter to enable/disable weekends
        self.weekend_on = weekend_on
        
        #shift params
        self.work_start_mon = work_start_mon
        self.work_end_sat = work_end_sat
        
        #sunday + saturday + monday
        self.steps_per_weekend = self.steps_per_day + ((24 - self.work_end_sat) + (self.work_start_mon)) / step_duration
        
        self.logger = logging.getLogger("factory_sim")
        
        self.logger.debug("Schedule successfully created.", extra = {"simtime": sim_env.now})
        self.log_time()
    
    def log_time(self):
        """
        log clock, day, week and working true/false
        hour starts with work_start_mon, day and week start with 0 (day 0 = monday)
        """
        current_step = self.sim_env.now
        current_hour = self.work_start_mon + int(current_step * self.step_duration) # +6 because step 0 is set to monday 6 o'clock
        current_minute = int(((current_step * self.step_duration) - int(current_step * self.step_duration)) * 60)
        current_hour_in_day = current_hour % 24
        current_hour_in_week = current_hour % 168
        current_week = int(current_hour / 168)
        current_day = int(current_hour_in_week / 24)
        working = self.is_it_worktime()
        
        self.logger.debug("clock: {}:{}, day: {}, week: {}, working: {}".format(current_hour_in_day,
            current_minute, current_day, current_week, working), extra = {"simtime": self.sim_env.now})
        
    def is_it_worktime(self, steps_for_process=0):
        """
        Checks if now + steps_for_process is time to work (True) or weekend (False). Always returns True if not production_system.weekend_on.
        """
        
        # if weekend are not wanted in simulation, it is always time to work
        if not self.weekend_on:
            return True
    
        current_step = self.sim_env.now + steps_for_process
        current_hour = 6 + current_step * self.step_duration # can lead to float hours
        current_hour_in_day = current_hour % 24
        current_hour_in_week = current_hour % 168
        current_day = int(current_hour_in_week / 24)
        
        #rules to decide whether it is time to work or to have a break
        #sunday
        if current_day == 6:
            return False
        #saturday evening
        elif current_day == 5 and current_hour_in_day >= self.work_end_sat:
            return False
        #monday morning
        elif current_day == 0 and current_hour_in_day < self.work_start_mon:
            return False
        
        return True
    
    def is_action_within_worktime(self, steps_for_process):
        """
        checks if there is weekend between now and end of process (False)
        True if process not interrupted by weekend between now and now + steps_for_process 
        """
        for i in range(0, steps_for_process):
            if not self.is_it_worktime(steps_for_process=i):
                return False
        return True
    
    def get_time_new_week(self):
        """
        returns the time left (in hours) to the start of the next week
        """
        return (self.steps_per_week - (self.sim_env.now  % self.steps_per_week)) * self.step_duration
    
    def get_steps_new_week(self):
        """
        returns the time left (in timesteps) to the start of the next week
        """
        return (self.steps_per_week - (self.sim_env.now  % self.steps_per_week))
        
    def log_time_new_week(self):
        """
        logs the time left (in hours) to the start of the next week
        """
        self.logger.debug("next Week starts in: {}h".format(self.get_time_new_week()), extra = {"simtime": self.sim_env.now})
        