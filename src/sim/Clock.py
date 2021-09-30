from sim.CoreObject import CoreObject


class Clock(CoreObject):
    '''
    Simple clock, ticks each hour, stops the machines on weekend, no interaction with maintenance
    '''

    def __init__(self, id, system, step_duration):

        super().__init__(id, system)

        self.step_duration = step_duration
        self.steps_per_hour = 1 / self.step_duration

        # start clock as soon as it is initialized
        self.action = self.sim_env.process(self.run())

    def run(self):
        '''
        runs the clock, ticks each hour, stops work (but not maintenance) on weekend if weekend_on = true
        '''
        # run as long as simulation
        while True:
            # self.weekly_schedule.log_time()
            # if it is weekend
            if not self.weekly_schedule.is_it_worktime():
                # shut down all machines that are not under repair
                for machine in self.system.machines:
                    self.logger.debug('{} found machine, with status: {}'.format(machine.id,
                                                                                 machine.status), extra={'simtime': self.sim_env.now})
                    if machine.status == 'working' or machine.status == 'waiting' or machine.status == 'repair_finished':
                        # machine.status = 'weekend'
                        machine.interrupt_origin = 'from_clock'
                        machine.process.interrupt(cause='from_clock')

                # wait until work_start_mon - 1h
                while not self.weekly_schedule.is_it_worktime(steps_for_process=self.steps_per_hour):
                    yield self.sim_env.timeout(self.steps_per_hour)
                # reset machine interrupts after weekend
                for machine in self.system.machines:
                    # only if the interrupt_origin given by the clock
                    if machine.status == 'weekend' and machine.failed == False:
                        machine.interrupt_origin = None
                        machine.status = 'working'
                        self.logger.debug('{} reset interrupt_origin'.format(machine.id),
                                          extra={'simtime': self.sim_env.now})

                # wait until work_start_mon
                yield self.sim_env.timeout(self.steps_per_hour)
            else:
                # wait one hour
                yield self.sim_env.timeout(self.steps_per_hour)
                # for machine in self.system.machines:
                #    self.logger.debug('{} status: {}'.format(machine.id, machine.status), extra = {'simtime': self.sim_env.now})
