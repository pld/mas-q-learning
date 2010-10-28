class BoardState:
	def __init__(self, predID, pred1, pred2, num_actions):
		if predID == 1:
			self.pred1Shift = pred1
			self.pred2Shift = pred2
		else:
			self.pred1Shift = pred2
			self.pred2Shift = pred1
		self.translate_coordinates(num_actions)
		
	def translate_coordinates(self, num_actions):
		# index actions as ['N', 'S', 'E', 'W', 'None']
		dir_shift = range(num_actions)
		if self.pred1Shift.x < 0 or (self.pred1Shift.x == 0 and self.pred2Shift.x < 0):
			self.pred1Shift.x *= -1
			self.pred2Shift.x *= -1
			# swap d2 and d3
			temp = dir_shift[2]
			dir_shift[2] = dir_shift[3]
			dir_shift[3] = temp
		if self.pred1Shift.y < 0 or (self.pred1Shift.y == 0 and self.pred2Shift.y < 0):
			self.pred1Shift.y *= -1
			self.pred2Shift.y *= -1
			# swap d0 and d1
			temp = dir_shift[0]
			dir_shift[0] = dir_shift[1] 
			dir_shift[1] = temp			
		if self.pred1Shift.x < self.pred1Shift.y or (self.pred1Shift.x == self.pred1Shift.y and self.pred2Shift.x < self.pred2Shift.y):
			# swap x1 and y1
			temp = self.pred1Shift.x  
			self.pred1Shift.x = self.pred1Shift.y 
			self.pred1Shift.y = temp
			# swap x2 and y2
			temp = self.pred2Shift.x
			self.pred2Shift.x = self.pred2Shift.y
			self.pred2Shift.y = temp
			# swap d0 and d2
			temp = dir_shift[0]
			dir_shift[0] = dir_shift[2]
			dir_shift[2] = temp
			# swap d1 and d3
			temp = dir_shift[1] 
			dir_shift[1] = dir_shift[3]
			dir_shift[3] = temp
		self.dir_shift = dir_shift
		
	def get_shifted_best(self, move):
		return self.dir_shift[move]

	def __eq__(self, o):
		if o == None or o.__class__ != self.__class__:
			return False
		p1_eq = self.pred1Shift == o.pred1Shift or (self.pred1Shift != None and self.pred1Shift.__eq__(o.pred1Shift))
		p2_eq = self.pred2Shift == o.pred2Shift or (self.pred2Shift != None and self.pred2Shift.__eq__(o.pred2Shift))
		
		return p1_eq and p2_eq

	def __hash__(self):
		code = 7
		code = 31*code + (0 if self.pred1Shift == None else self.pred1Shift.__hash__())
		code = 31*code + (0 if self.pred2Shift == None else self.pred2Shift.__hash__())
		return code

