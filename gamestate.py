class GameState:
	last_state = False
	last_action = None
	last_prey_dist = 0
	# learning parameters
	alpha = 0.15
	alpha_initial = 0.15
	gamma = 1
	epsilon_initial = 0.75
	episode = 0
	k_prob = 1
	max_explore_episode = None
	max_learn_episode = None
	use_boltz = True
	Q_hat1 = {}
	Q_hat2 = {}

