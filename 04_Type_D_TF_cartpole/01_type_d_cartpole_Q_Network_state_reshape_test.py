import tensorflow as tf
import random
import numpy as np
import time, datetime
from collections import deque

import gym
import pylab
import sys
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
from tensorflow.python.framework import ops
ops.reset_default_graph()

env = gym.make('CartPole-v1')

state_size = env.observation_space.shape[0]
action_size = env.action_space.n

game_name =  sys.argv[0][:-3]

model_path = "save_model/" + game_name
graph_path = "save_graph/" + game_name

# Make folder for save data
if not os.path.exists(model_path):
    os.makedirs(model_path)
if not os.path.exists(graph_path):
    os.makedirs(graph_path)

learning_rate = 0.001
discount_factor = 0.99
        
epsilon_max = 1.0
epsilon_min = 0.0001
epsilon_decay = 0.0001

hidden1 = 256
update_cycle = 10

class DQN:

    def __init__(self, session: tf.Session, state_size: int, action_size: int, name: str="main") -> None:
        self.session = session
        self.state_size = state_size
        self.action_size = action_size
        self.net_name = name
        
        self.build_model()

    # approximate Q function using Neural Network
    # state is input and Q Value of each action is output of network
    def build_model(self, H_SIZE_01 = 256, Alpha=0.001) -> None:
        with tf.variable_scope(self.net_name):
            self._X = tf.placeholder(dtype=tf.float32, shape= [None, self.state_size], name="input_X")
            self._Y = tf.placeholder(dtype=tf.float32, shape= [None, self.action_size], name="output_Y")
            net_0 = self._X

            h_fc1 = tf.layers.dense(net_0, H_SIZE_01, activation=tf.nn.relu)
            h_fc2 = tf.layers.dense(h_fc1, H_SIZE_01, activation=tf.nn.relu)
            output = tf.layers.dense(h_fc2, self.action_size)
            self._Qpred = output

            # self.Loss = tf.losses.mean_squared_error(self._Y, self._Qpred)
            self.Loss = tf.reduce_mean(tf.square(self._Y - self._Qpred))

            optimizer = tf.train.AdamOptimizer(learning_rate=Alpha)
            self.train_op = optimizer.minimize(self.Loss)

    def predict(self, state: np.ndarray) -> np.ndarray:
        x = np.reshape(state, [1, self.state_size])
        return self.session.run(self._Qpred, feed_dict={self._X: x})

    def update(self, x_stack: np.ndarray, y_stack: np.ndarray) -> list:
        feed = {
            self._X: x_stack,
            self._Y: y_stack
        }
        return self.session.run([self.Loss, self.train_op], feed)

def train_model(agent: DQN, state, action, reward, next_state, done):

    X_batch = state
    q_value = agent.predict(state)
    q_value_next = agent.predict(next_state)

    # print(q_value)
    y_val = reward + discount_factor * np.max(q_value_next, axis=1) * ~done
    q_value[0][action] = y_val
    
    # print(action)
    # print(y_val)
    # print(q_value)
    # sys.exit()
    X_batch = np.reshape(state, [1, agent.state_size])
    Loss, _ = agent.update(X_batch, q_value)

    return Loss

def main():

    with tf.Session() as sess:
        agent = DQN(sess, state_size, action_size, name="main")
        init = tf.global_variables_initializer()
        saver = tf.train.Saver()
        sess.run(init)

        avg_score = 0
        episode = 0
        episodes, scores = [], []
        epsilon = epsilon_max
        start_time = time.time()

        while time.time() - start_time < 10*60 and avg_score < 490:
            
            state = env.reset()
            score = 0
            done = False
            ep_step = 0
            
            while not done and ep_step < 500 :

                #env.render()
                ep_step += 1
                
                if epsilon > np.random.rand(1):
                    action = env.action_space.sample()
                else:
                    action = np.argmax(agent.predict(state))

                next_state, reward, done, _ = env.step(action)

                if done:
                    reward = -100

                train_model(agent, state, action, reward, next_state, done)

                if epsilon > epsilon_min:
                    epsilon -= epsilon_decay
                else:
                    epsilon = epsilon_min

                state = next_state
                score = ep_step

                if done or ep_step == 500:
                    
                    episode += 1
                    scores.append(score)
                    episodes.append(episode)
                    avg_score = np.mean(scores[-min(30, len(scores)):])

                    print("episode {:>5d} / score:{:>5d} / recent 30 game avg:{:>5.1f} / epsilon :{:>1.5f}"
                              .format(episode, score, avg_score, epsilon))            
                    break

        save_path = saver.save(sess, model_path + "/model.ckpt")
        print("\n Model saved in file: %s" % save_path)

        pylab.plot(episodes, scores, 'b')
        pylab.savefig(graph_path + "/cartpole_NIPS2013.png")

        e = int(time.time() - start_time)
        print(' Elasped time :{:02d}:{:02d}:{:02d}'.format(e // 3600, (e % 3600 // 60), e % 60))

    # Replay the result
        episode = 0
        scores = []
        while episode < 20:
            
            state = env.reset()
            done = False
            ep_step = 0
            
            while not done and ep_step < 500:
                env.render()
                ep_step += 1
                q_value = agent.predict(state)
                action = np.argmax(q_value)
                next_state, reward, done, _ = env.step(action)
                state = next_state
                score = ep_step
                
                if done or ep_step == 500:
                    episode += 1
                    scores.append(score)
                    print("episode : {:>5d} / reward : {:>5d} / avg reward : {:>5.2f}".format(episode, score, np.mean(scores)))

if __name__ == "__main__":
    main()
