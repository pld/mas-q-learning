class Player:	
	def __init__(self, x, y, world):
		self.x = x
		self.y = y
		self.relative_dist = abs(x) + abs(y)
		self.world = world
		
	def xOffset(self, offX):
		newX = self.x - offX
		if newX > self.world.columns/2:
			newX -= self.world.columns
		elif newX < self.world.columns/(-2):
			newX += self.world.columns
		return newX
		
	def yOffset(self, offY):
		newY = self.y - offY
		if newY > self.world.rows/2:
			newY -= self.world.rows
		elif newY < self.world.rows/(-2):
			newY += self.world.rows
		return newY

	def relative_distOffset(self, offX, offY):
		return abs(self.xOffset(offX), self.yOffset(offY))
