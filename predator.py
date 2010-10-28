#!/usr/bin/python

from socket import *
import string
import random
import bisect
import math
import pickle
import gamestate
import player
import world
import boardstate
import point

# MAIN CLASS
class Predator:
	sock = None
	DEBUG = 1
	Q_hat_file = 'Q_hat.pkl'
	save_Q_hats = 0
	import_game = 0
	# actions as action strings and 0
	actions = ['(move north) ', '(move south) ', '(move east) ', '(move west) ', '(move none) ']
	num_actions = len(actions)
	num_joint_actions = num_actions*num_actions
	k_prob = 1
	predID = None

	def __init__(self):
		random.seed(1)
		self.world = world.World()
		self.prey_list = []
		self.pred_list = []
		self.game_init = False
		if self.import_game > 0:
			self.game_state = self.load_Q_hat(self.import_game)
		else:
			gs = gamestate.GameState()
			gs.last_action = self.num_actions - 1 if self.world.capture == 3 else self.num_joint_actions - 1
			gs.max_explore_episode = 10000.0 if self.world.capture == 3 else 5000.0
			gs.max_learn_episode = 15000.0 if self.world.capture == 3 else 10000.0
			self.game_state = gs

	# processes the incoming visualization messages from the server
	def processVisualInformation(self, msg):
		if string.find( msg, '(see)' ) == 0:
			self.msg = self.determineMovementCommand()
		else:
			# strip the '(see ' and the ')'
			msg = msg[6:-3]
			observations = string.split(msg, ') (')
			for o in observations:
				(obj, x, y) = string.split(o, " ")
				if self.DEBUG > 1:
					print obj + " seen at (" + x + ", " + y + ")"
				x, y = int(x), int(y)
				if obj == "prey":
					self.prey_list.append(player.Player(x, y, self.world))
				elif obj == "predator":
					self.pred_list.append(player.Player(x, y, self.world))

	# determines the next movement command for this agent
	def determineMovementCommand( self ):
		if (len(self.prey_list) == 0):
			return '(move none) '
		prey = self.prey_list[0]
		self.prey_list = []
		if (len(self.pred_list) != 1):
			return '(move none) '
		other_pred = self.pred_list[0]
		self.pred_list = []
		
		me_pred = point.Point(prey.xOffset(0), prey.yOffset(0))
		her_pred = point.Point(prey.xOffset(other_pred.x), prey.yOffset(other_pred.y))
		
		cur_dist = 0
		if self.world.capture == 3:
			cur_dist = abs(me_pred.x) + abs(me_pred.y)
		elif self.world.capture == 4:
			cur_dist = abs(me_pred.x) + abs(me_pred.y) + abs(her_pred.x) + abs(her_pred.y)
		
		if not self.game_init:
			self.game_init = True
			if (me_pred.x > her_pred.x or (me_pred.x == her_pred.x and me_pred.y > her_pred.y)):
				self.predID = 1
			else:
				self.predID = 2
			if self.import_game == 0:
				self.initQ_hat()
			
		cur_state = boardstate.BoardState(self.predID, me_pred, her_pred, self.num_actions)
		Qvals1 = self.get_Q_hat_vals(self.game_state.Q_hat1, cur_state)
		Qvals2 = self.get_Q_hat_vals(self.game_state.Q_hat2, cur_state)
		
		if self.world.capture == 3:
			Q_hat_vals = Qvals1 if self.predID == 1 else Qvals2
			cur_state_val1 = cur_state_val2 = max(Q_hat_vals)
		elif self.world.capture == 4:
			best_joint_action = self.num_joint_actions - 1
			cur_max = Qvals1[best_joint_action] + Qvals2[best_joint_action]
			for i in range(0, len(Qvals1) - 1):
				tmp_sum = Qvals1[i] + Qvals2[i]
				if tmp_sum > cur_max:
					cur_max = tmp_sum
					best_joint_action = i
			cur_state_val1 = Qvals1[best_joint_action]
			cur_state_val2 = Qvals2[best_joint_action]
		
		penalty = self.game_state.last_prey_dist - cur_dist - 1
		self.set_prev_action(1, cur_state_val1, penalty)
		self.set_prev_action(2, cur_state_val2, penalty)
		
		best_move1 = self.get_best_move(1, Qvals1, Qvals2)
		best_move2 = self.get_best_move(2, Qvals1, Qvals2)		
		
		self.game_state.last_state = cur_state
		if self.world.capture == 3:
			self.game_state.last_action = best_move1 if self.predID == 1 else best_move2
		elif self.world.capture == 4:
			self.game_state.last_action = best_move1 * 5 + best_move2
		self.game_state.last_prey_dist = cur_dist
		cur_best_move = cur_state.get_shifted_best(best_move1 if self.predID == 1 else best_move2)
		return self.actions[cur_best_move]

	def get_best_move(self, ID, vals1, vals2):
		Q_hat_vals = vals1 if ID == 1 else vals2
		best_move = self.num_actions - 1
		gs = self.game_state
		if Q_hat_vals != None:
			if gs.episode < gs.max_explore_episode and random.random() <= gs.epsilon_initial * self.explore_prob():
				if gs.use_boltz:
					best_move = self.boltzmann_best(ID, vals1, vals2)
				else:
					num_actions = self.num_actions if self.world.capture == 3 else self.num_joint_actions
					best_move = random.randint(0, num_actions - 1)
			else:
				# not random
				if self.world.capture == 3:
					best_move = Q_hat_vals.index(max(Q_hat_vals))
				elif self.world.capture == 4:
					best_move = 0
					cur_max = vals1[0] + vals2[0]
					for i in range(1, len(vals1)):
						tmp_sum = vals1[i] + vals2[i]
						if tmp_sum > cur_max:
							cur_max = tmp_sum
							best_move = i
		return best_move if self.world.capture == 3 else (best_move / self.num_actions if ID == 1 else best_move % self.num_actions)
		
	def boltzmann_best(self, ID, vals1, vals2):
		Q_hat_vals = vals1 if ID == 1 else vals2
		p_a_given_s = []
		if self.world.capture == 3:
			for a in range(self.num_actions):
				p_a_given_s.append((self.game_state.k_prob+(self.game_state.episode/self.game_state.max_explore_episode))**Q_hat_vals[a])
		elif self.world.capture == 4:
			for a in range(self.num_joint_actions):
				p_a_given_s.append(self.explore_prob()**(vals1[a]+vals2[a]))
		p_a_given_s_sum = float(sum(p_a_given_s))
		p_a_given_s = [x/p_a_given_s_sum for x in p_a_given_s]
		actions = range(self.num_actions) if self.world.capture == 3 else range(self.num_joint_actions)
		return self.weighted_choice_bisect_compile(zip(actions, p_a_given_s), ID)

	# return weighted choice from items
	def weighted_choice_bisect_compile(self, items, ID):
		added_weights = []
		last_sum = 0
		
		for item, weight in items:
			last_sum += weight
			added_weights.append(last_sum)
		if self.DEBUG >= 2:
			print "items: %s"%items
			print "added_weights: %s"%added_weights
		def choice(rnd = random.random, bis = bisect.bisect):
			return items[bis(added_weights, rnd() * last_sum)][0]
		return choice()

	def set_prev_action(self, predID, cur_state_val, penalty):
		gs = self.game_state
		Q_hat = gs.Q_hat1 if predID == 1 else gs.Q_hat2
		if Q_hat != None and gs.last_state in Q_hat:
			prev_action_val = Q_hat[gs.last_state][gs.last_action]
			new_val = prev_action_val * (1 - gs.alpha) + gs.alpha * (penalty + gs.gamma * cur_state_val)
			if predID == 1:
				self.game_state.Q_hat1[gs.last_state][gs.last_action] = new_val
			else:
				self.game_state.Q_hat2[gs.last_state][gs.last_action] = new_val

	def get_Q_hat_vals(self, Q_hat, cur_state):
		if Q_hat != None:
			Q_hat_vals = Q_hat.get(cur_state)
			if Q_hat_vals == None:
				if self.world.capture == 3:
					Q_hat_vals = [0 for x in range(self.num_actions)]
				elif self.world.capture == 4:
					Q_hat_vals = [0 for x in range(self.num_joint_actions)]
				Q_hat[cur_state] = Q_hat_vals
		return Q_hat_vals

	def explore_prob(self):
		gs = self.game_state
		return (gs.max_explore_episode - gs.episode) / gs.max_explore_episode

	def initQ_hat(self):
		if self.world.capture == 3:
			if self.predID == 1:
				self.game_state.Q_hat1 = {}
			else:
				self.game_state.Q_hat2 = {}
		elif self.world.capture == 4:
			self.game_state.Q_hat1 = {}
			self.game_state.Q_hat2 = {}
	
	def dump_Q_hat(self, episode):
		output = open("%s.%i" % (self.Q_hat_file, episode), 'wb')
		pickle.dump(self.game_state, output)
		output.close()
	
	def load_Q_hat(self, episode):
		in_file = open("%s.%i" % (self.Q_hat_file, episode), 'rb')
		self.game_state = pickle.load(in_file)
		in_file.close()

	# determine a communication message
	def determineCommunicationCommand( self ):
		# TODO: Assignment 3
		return ""

	# process the incoming visualization messages from the server
	def processCommunicationInformation( self, str ):
		# TODO: Assignment 3
		pass

	def processEpisodeEnded( self ):
		self.set_capture_action_val(1)
		self.set_capture_action_val(2)
		self.game_state.last_state = None
		self.game_state.last_action = self.num_actions - 1 if self.world.capture == 3 else self.num_joint_actions - 1
		self.game_state.last_prey_dist = 0
		self.game_state.episode += 1
		self.game_state.alpha = self.game_state.alpha_initial * (self.game_state.max_learn_episode - self.game_state.episode) / self.game_state.max_learn_episode if self.game_state.episode < self.game_state.max_learn_episode else 0
		if self.save_Q_hats > 0:
			if self.game_state.episode % self.save_Q_hats == 0:
				self.dump_Q_hat(gs.episode)
	
	def set_capture_action_val(self, predID):
		gs = self.game_state
		Q_hat = gs.Q_hat1 if predID == 1 else gs.Q_hat2
		if Q_hat != None and gs.last_state in Q_hat:
			prev_action_val = Q_hat[gs.last_state][gs.last_action]
			new_val = prev_action_val * (1 - gs.alpha) + gs.alpha * gs.last_prey_dist
			if predID == 1:
				self.game_state.Q_hat1[gs.last_state][gs.last_action] = new_val
			else:
				self.game_state.Q_hat2[gs.last_state][gs.last_action] = new_val

	def processCollision( self ):
		pass
		
	def processPenalize( self ):
		pass

	# BELOW ARE METODS TO CALL APPROPRIATE METHODS; CAN BE KEPT UNCHANGED
	def connect( self, host='', port=4001 ):
		self.sock = socket( AF_INET, SOCK_DGRAM)
		self.sock.bind( ( '', 0 ) )
		self.sock.sendto( "(init predator)" , (host, port ) )
		pass

	def mainLoop( self ):
		msg, addr = self.sock.recvfrom( 1024 )
		self.sock.connect( addr )
		ret = 1
		while ret:
			msg = self.sock.recv( 1024 )
			if string.find( msg, '(quit' ) == 0 :
				# quit message
				ret = 0
			elif string.find( msg, '(hear' ) == 0 :
				# process audio
				self.processCommunicationInformation( msg )
			elif string.find( msg, '(see' ) == 0 :
				# process visual
				self.processVisualInformation( msg )
				msg = self.determineCommunicationCommand( )
				if len(msg) > 0:
					self.sock.send( msg )
			elif string.find( msg, '(send_action' ) == 0 :
				msg = self.determineMovementCommand()
				self.sock.send( msg )
			elif string.find( msg, '(referee episode_ended)' ) == 0:  
				msg = self.processEpisodeEnded( )
			elif string.find( msg, '(referee collision)' ) == 0:  
				msg = self.processCollision( )
			elif string.find( msg, '(referee penalize)' ) == 0:	 
				msg = self.processPenalize( )
			else:
				print "msg not understood " + msg
		self.sock.close()
		pass


if __name__ == "__main__":
	predator = Predator()
	predator.connect()
	predator.mainLoop()
