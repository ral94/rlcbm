import random
import math
from collections import namedtuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F


class DQNModel(nn.Module):
    """
    Deep Q-Network Neural Network
    """
    def __init__(self, n_actions, env_dims, n_hidden1=14, n_hidden2=28):
        """
        Neural Network Architecture, same for model and target_model
        """
        super().__init__()
        # 1 Input Layer, 2 fully connected hidden layers, 1 output layer
        self.fc1 = nn.Linear(in_features = env_dims, 
                             out_features = n_hidden1)
        self.fc2 = nn.Linear(in_features = n_hidden1, 
                             out_features = n_hidden2)
        self.out = nn.Linear(in_features = n_hidden2, 
                             out_features = n_actions)
        
    def forward(self, t):
        """
        Feedforward state through neural network
        """
        # reLu activation functions for both layers, pass state through network
        t = F.relu(self.fc1(t))
        t = F.relu(self.fc2(t))
        t = self.out(t)
        return t


class ReplayMemory():
    """
    Experience Replay to store the experiences of the agent
    """
    def __init__(self, capacity):
        # Capacity of the Experience Replay
        self.capacity = capacity    
        # Initialize Experience Repaly
        self.memory = [None] * self.capacity 
        self.memory_counter = 0
         
    def store(self, experience):
        """
        Save experience to Experience Replay
        """
        self.memory[self.memory_counter % self.capacity] = experience
        self.memory_counter +=1
            
    def sample(self, batch_size):
        """
        Sample experience from Experience Replay
        """
        if self.memory_counter < self.capacity:
            # Sample from memory_counter available experiences
            return random.sample(self.memory[:self.memory_counter], batch_size)
        else:
            # Sample from whole replay memory
            return random.sample(self.memory, batch_size) 
    
    def sample_possible(self, batch_size):
        """
        Check if sampling from memory is possible
        """
        return self.memory_counter >= batch_size


class EpsilonGreedy():
    """
    Epsilon Greedy strategy
    """
    def __init__(self, start, end, decay):
        """
        Initialize Epsilon greedy strategy variables
        """
        self.start = start
        self.end = end
        self.decay = decay
        
    def get_exploration_rate(self, current_step):
        """
        Calculate current exploration rate via exponential decay
        """
        return self.end + (self.start - self.end) * math.exp(-1. * current_step * self.decay)


class DDQNAgent():
    """
    Double-DQN RL Agent
    """
    def __init__(self, env, model, target_model, lr, buffer_sz, epsilon, epsilon_decay, 
    min_epsilon, gamma, target_update_iter, start_learning):
        self.env = env
        self.model = model
        self.target_model = target_model
        self.lr = lr
        self.buffer_sz = buffer_sz
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon
        self.gamma = gamma
        self.target_update_iter = target_update_iter
        self.start_learning = start_learning

        self.optimizer = optim.Adam(params=model.parameters(), lr=self.lr)
        self.strategy = EpsilonGreedy(self.epsilon , self.min_epsilon, self.epsilon_decay)
        self.memory = ReplayMemory(self.buffer_sz)
        # create a experience tuple
        self.experience = namedtuple('Experience', ('state', 'action', 'next_state', 'reward', 'done'))
        self.num_actions = self.env.action_space.n

        # copy weights from model to target_model
        self.target_model.load_state_dict(self.model.state_dict()) 
        # set target_model to evaluation mode. This network will only be used for inference.
        target_model.eval()

        self.current_step = 0

    def train(self, epochs, batch_sz):

        # training loop
        ep_rewards = [0.0]
        ep_steps = [0]

        # tracking of simulation
        produced_parts = []
        ep_rewards_mean = []

        for epoch in range(epochs):

            state = self.env.reset()
            state = torch.FloatTensor([state]) # convert state to tensor

            while True:
                # select action according to e-greedy strategy
                action = self._select_action(state)
                next_state, reward, done, _ = self.env.step(action)

                ep_rewards[-1] += reward
                ep_steps[-1] += 1
                
                # convert to tensors       
                next_state = torch.FloatTensor([next_state])
                reward = torch.FloatTensor([reward])
                action = torch.tensor([action], dtype=torch.int64)
                done = torch.tensor([done], dtype=torch.int32)
                self.memory.store(self.experience(state, action, next_state, reward, done))

                # training of DQN model
                if self.memory.sample_possible(batch_sz):
                    # choose random experience from Replay Memory
                    experiences = self.memory.sample(batch_sz)
                    # separate states, actions, rewards and next_states from the minibatch
                    states, actions, next_states, rewards, dones = zip(*experiences)
                    states = torch.cat(states)
                    actions = torch.cat(actions)
                    rewards = torch.cat(rewards)
                    next_states = torch.cat(next_states)
                    dones = torch.cat(dones)

                    # Input states of minibatch into model --> Get current Q-Value estimation of model
                    index = actions.unsqueeze(-1) # transforms actions tensor into tensor with lists for indexing
                    current_q_values = self.model(states).gather(dim=1, index=index).squeeze() # squeeze to remove 1 axis

                    # DDQN
                    max_next_q_values_model_indices = self.model(next_states).argmax(1).detach()
                    index_ddqn = max_next_q_values_model_indices.unsqueeze(-1)
                    # Gather Q-Values of target_model for corresponding actions
                    next_q_values_from_target_of_model_indices = self.target_model(next_states).gather(dim=1,index=index_ddqn).squeeze() # squeeze to remove 1 axis
                    # Update target Q_values with Q-values of target_model based on max Q-values of model
                    target_q_values = (next_q_values_from_target_of_model_indices*self.gamma)+rewards*(1-dones)
                    
                    # Calculate loss
                    loss = F.mse_loss(current_q_values, target_q_values)

                    # Set the gradients to zero before starting to do backpropragation with loss
                    self.optimizer.zero_grad()
                    loss.backward()
                    # clip the gradients 
                    clip=1
                    nn.utils.clip_grad_norm_(self.model.parameters(),clip)
                    
                    # update params
                    self.optimizer.step()

                state = next_state
                # Logging and update of target_model
                if done:

                    ep_rewards.append(0.0)
                    ep_steps.append(0)
                    produced_parts.append(len(self.env.system.sink_store.items))
                    ep_rewards_mean.append(self._get_mean_reward(ep_rewards))

                    print('epoch:', epoch)
                    break

            # Copy weights from model to target_model every "target_update" setps
            if epoch % self.target_update_iter == 0 and epoch != 0:
                self.target_model.load_state_dict(self.model.state_dict())

        ep_rewards = ep_rewards[:-1]

        return ep_rewards, produced_parts, ep_rewards_mean

    def _select_action(self, state):
        """
        Select action depending on exploration strategie (eps-greedy)
        """  
        self.exploration_rate = self.strategy.get_exploration_rate(self.current_step)
        self.current_step +=1
        
        if self.exploration_rate > random.random():
            action = self.env.action_space.sample()
            return action  # agent explores
        else:
            # Turn off gradient tracking since we’re currently using the model for inference and not training.
            with torch.no_grad():
                action = self.model(state).argmax(dim=1).item()
                return action #  agent exploits

    def _get_mean_reward(self, ep_rewards):
        """ mean reward over 100 episodes"""
        if len(ep_rewards) <= 100:
            return np.mean(ep_rewards[-len(ep_rewards):-1])
        else:
            return np.mean(ep_rewards[-100:-1])