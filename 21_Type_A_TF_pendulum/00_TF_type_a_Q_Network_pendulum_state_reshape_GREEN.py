import random
import numpy as np
import time, datetime
import gym
import pylab
import sys
import pickle
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
from tensorflow.python.framework import ops
ops.reset_default_graph()
import tensorflow as tf

# In case of CartPole-v1, maximum length of episode is 500
env = gym.make('Pendulum-v0')
env.seed(1)     # reproducible, general Policy gradient has high variance
# env = env.unwrapped

# get size of state and action from environment
state_size = env.observation_space.shape[0]
action_size = 25

game_name =  sys.argv[0][:-3]

model_path = "save_model/" + game_name
graph_path = "save_graph/" + game_name

# Make folder for save data
if not os.path.exists(model_path):
    os.makedirs(model_path)
if not os.path.exists(graph_path):
    os.makedirs(graph_path)

# this is Q_net Agent for the GridWorld
# Utilize Neural Network as q function approximator
class DeepSARSAgent:
    def __init__(self):
        # if you want to see Cartpole learning, then change to True
        self.render = False
        # get size of state and action
        self.state_size = state_size
        self.action_size = action_size
        
        # train time define
        self.training_time = 5*60
        
        # These are hyper parameters for the DQN
        self.learning_rate = 0.001
        self.discount_factor = 0.99
        
        self.epsilon_max = 1.0
        # final value of epsilon
        self.epsilon_min = 0.0001
        self.epsilon_decay = 0.0005
        self.epsilon = self.epsilon_max
        
        self.step = 0
        self.score = 0
        self.episode = 0
        
        self.hidden1, self.hidden2 = 64, 64
        
        self.ep_trial_step = 200
        
        # Initialize Network
        self.input, self.output = self.build_model('network')
        self.train_step, self.y_tgt, self.Loss = self.loss_and_train()
        
    # approximate Q function using Neural Network
    # state is input and Q Value of each action is output of network
    def build_model(self, network_name):
        # input layer
        x_input = tf.placeholder(tf.float32, shape = [None, self.state_size])
        # network weights
        with tf.variable_scope(network_name):
            model = tf.layers.dense(x_input, self.hidden1, activation=tf.nn.relu)
            model = tf.layers.dense(model, self.hidden2, activation=tf.nn.relu)
            output = tf.layers.dense(model, self.action_size, activation=None)
        return x_input, output

    def loss_and_train(self):
        # Loss function and Train
        y_tgt = tf.placeholder(tf.float32, shape = [None, self.action_size])
        
        Loss = tf.reduce_mean(tf.square(y_tgt - self.output))
        train_step = tf.train.AdamOptimizer(learning_rate = self.learning_rate, epsilon = 1e-02).minimize(Loss)
        
        return train_step, y_tgt, Loss

    # For Q-net or sarsa there is only one batch
    def train_model(self, state, action, reward, next_state, done):
        
        # Get target values
        
        y_array = self.output.eval(feed_dict = {self.input:[state]})
        # Selecting action_arr
        q_value_next = self.output.eval(feed_dict = {self.input: [next_state]})
        
        if done:
            target = reward
        else:
            target = reward + self.discount_factor * np.max(q_value_next)
        
        y_array[0][action] = target
        
        # Decrease epsilon while training
        if self.epsilon > self.epsilon_min:
            self.epsilon -= self.epsilon_decay
        else :
            self.epsilon = self.epsilon_min
            
        state = np.reshape(state,[1,state_size])    
        # Training!! 
        feed_dict = {self.y_tgt: y_array, self.input: state}
        _, self.loss = self.sess.run([self.train_step, self.Loss], feed_dict = feed_dict)

    # get action from model using epsilon-greedy policy
    def get_action(self, state):
        # choose an action_arr epsilon greedily
        action_arr = np.zeros(self.action_size)
        action = 0
        
        if random.random() < self.epsilon:
            # print("----------Random action_arr----------")
            action = random.randrange(self.action_size)
            action_arr[action] = 1
        else:
            # Predict the reward value based on the given state
            Q_value = self.output.eval(feed_dict= {self.input:[state]})[0]
            action = np.argmax(Q_value)
            action_arr[action] = 1
            
        return action_arr, action

    def save_model(self):
        # Save the variables to disk.
        save_path = self.saver.save(self.sess, model_path + "/model.ckpt")
        save_object = (self.epsilon, self.episode, self.step)
        with open(model_path + '/epsilon_episode.pickle', 'wb') as ggg:
            pickle.dump(save_object, ggg)

        print("\n Model saved in file: %s" % model_path)

def main():
    
    agent = DeepSARSAgent()
    
    # Initialize variables
    # Load the file if the saved file exists
    agent.sess = tf.InteractiveSession()
    init = tf.global_variables_initializer()
    agent.saver = tf.train.Saver()
    ckpt = tf.train.get_checkpoint_state(model_path)

    if ckpt and tf.train.checkpoint_exists(ckpt.model_checkpoint_path):
        agent.saver.restore(agent.sess, ckpt.model_checkpoint_path)
        if os.path.isfile(model_path + '/epsilon_episode.pickle'):
            
            with open(model_path + '/epsilon_episode.pickle', 'rb') as ggg:
                agent.epsilon, agent.episode, agent.step = pickle.load(ggg)
            
        print('\n\n Variables are restored!')

    else:
        agent.sess.run(init)
        print('\n\n Variables are initialized!')
        agent.epsilon = agent.epsilon_max
    
    avg_score = -120
    episodes, scores = [], []
    
    # start training    
    # Step 3.2: run the game
    display_time = datetime.datetime.now()
    print("\n\n",game_name, "-game start at :",display_time,"\n")
    start_time = time.time()
    
    while time.time() - start_time < agent.training_time and avg_score < -30:

        state = env.reset()
        done = False
        agent.score = -120
        ep_step = 0
        rewards = 0
        while not done and ep_step < agent.ep_trial_step:
            # fresh env
            ep_step += 1
            agent.step += 1
            
            if agent.render:
                env.render()
                
            action_arr, action = agent.get_action(state)
            
            # run the selected action_arr and observe next state and reward
            f_action = (action-(action_size-1)/2)/((action_size-1)/4)
            next_state, reward, done, _ = env.step(np.array([f_action]))
            
            
            
            reward /= 10
            rewards += reward
            agent.train_model(state, action, reward, next_state, done)
                    
            # update the old values
            state = next_state
                    
            agent.score = rewards

            if done or ep_step == agent.ep_trial_step:
                agent.episode += 1

                scores.append(agent.score)
                episodes.append(agent.episode)
                avg_score = np.mean(scores[-min(30, len(scores)):])
                print('episode :{:>6,d}'.format(agent.episode),'/ Rewards :{:> 4f}'.format(rewards), \
                      '/ time step :{:>7,d}'.format(agent.step), \
                      '/ epsilon :{:>1.4f}'.format(agent.epsilon),'/ last 30 avg :{:> 4.1f}'.format(avg_score) )
                break
    # Save model
    agent.save_model()
    
    pylab.plot(episodes, scores, 'b')
    pylab.savefig("./save_graph/pendulum_Q_network_.png")

    e = int(time.time() - start_time)
    print(' Elasped time :{:02d}:{:02d}:{:02d}'.format(e // 3600, (e % 3600 // 60), e % 60))
    sys.exit()

if __name__ == "__main__":
    main()