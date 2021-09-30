import logging
import matplotlib.pyplot as plt

from SimEnv_IH import SimEnvIH
from sim.System import System
from sim.ProductionExamples import ProductionSystem1, ProductionSystem2
from agent.DDQN import DQNModel, DDQNAgent
from agent.Heuristics import RandomAgent, FIFOAgent


# set DEBUG/INFO
logging.basicConfig(level=logging.INFO, format='%(simtime)6d %(message)s')

if __name__ == "__main__":

    # create environment
    system = System(use_case="ih", production_system=ProductionSystem1())
    env = SimEnvIH(system)

    # Hyperparameters
    n_hidden1 = 14
    n_hidden2 = 28
    start_learning = 97
    batch_sz = 137
    gamma = 0.993
    lr = 0.00036
    target_update_iter = 98
    epsilon_decay = 0.000029
    epsilon = 0.2
    min_epsilon = 0.1
    buffer_sz = 100000

    epochs = 3000


env_dims = env.system_state_converter.get_observation_dims() # input
action_dims = env.action_space.n # output


model = DQNModel(n_actions=action_dims,
                 env_dims=env_dims,
                 n_hidden1=n_hidden1,
                 n_hidden2=n_hidden2)
target_model = DQNModel(n_actions=action_dims,
                        env_dims=env_dims,
                        n_hidden1=n_hidden1,
                        n_hidden2=n_hidden2)

agent = DDQNAgent(env=env,
                  model=model,
                  target_model=target_model,
                  start_learning=start_learning,
                  target_update_iter=target_update_iter,
                  gamma=gamma,
                  buffer_sz=buffer_sz,
                  epsilon_decay=epsilon_decay,
                  epsilon=epsilon,
                  min_epsilon=min_epsilon,
                  lr=lr
                  )

episode_rewards, produced_parts, mean_episode_rewards = agent.train(
    epochs=epochs, batch_sz=batch_sz)
