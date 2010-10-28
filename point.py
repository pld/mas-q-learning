class Point:
	def __init__(self, x, y):
		self.x = x
		self.y = y

	def __key(self):
		return (self.x, self.y)
	
	def __eq__(self, o):
		if o == None or o.__class__ != self.__class__:
			return False
		return self.__key() == o.__key()
	
	def __hash__(self):
		return hash(self.__key())
