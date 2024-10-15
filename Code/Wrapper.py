"""
This project involves developing a simplified boundary detection algorithm that combines texture, brightness, and color gradients with classical 
edge detection methods like Sobel and Canny. By using feature-based gradients and chi-square distance calculations with half-disc masks, the algorithm 
captures boundaries across multiple scales and orientations. The final boundary map is generated by fusing these feature gradients with traditional 
edge detection methods for more robust and accurate edge detection.

Project Details: https://rbe549.github.io/spring2024/hw/hw0/

Author : 
Rigved Sanku (rsanku@wpi.edu)
MS at Robotics Engineering Department,
Worcester Polytechnic Institute
"""

from typing import List
from numpy import sqrt, pi, reshape, sin, cos
import matplotlib.pyplot as plt
import numpy as np
import cv2



class FilterBank:
    
	def __init__(self):
		pass
	
 
	def gaussian_filter(self, grid, sigma, elongation=1, elongate ='yes'):
		"""
		Returns a 2D Gaussian filter.
		grid: a tuple containing meshgrid of x and y coordinates.
		sigma: standard deviation for Gaussian.
		elongation: ratio between sigma_x and sigma_y.
		elongate: 'yes' or 'no' to elongate the Gaussian filter.
		"""
		x, y = grid
		sigma_x = sigma
		
		if elongate == 'yes':
			sigma_y = elongation*sigma_x
			
		else:
			sigma_y = sigma_x
			
		numerator = np.exp(-(x**2 / (2*sigma_x**2) + y**2 / (2*sigma_y**2)))
		denominator = 2 * pi * sigma_x * sigma_y
		return numerator / denominator
 

	def derivative_gaussian_filter(self, grid, sigma, elongation, order, elongate = 'yes'):
		"""
		Generate a 2D Gaussian derivative filter (first or second order) or Laplacian.

		Parameters:
		grid (tuple): A tuple containing the x and y meshgrid.
		sigma (float): Standard deviation for the Gaussian.
		elongation (float): Ratio to elongate the Gaussian in the y-direction (anisotropy).
		order (list): Derivative order, e.g., [1, 0] for first derivative in x, [0, 2] for second derivative in y.

		Returns:
		numpy.ndarray: The computed derivative of the 2D Gaussian.
		"""
    
		gaussian = self.gaussian_filter(grid, sigma, elongation, elongate)
		x, y = grid
		sigma_x = sigma
		sigma_y = sigma_x * elongation
		
		# first partial x derivative
		if order == [1, 0]:
			first_derivate_x = (-x / sigma_x**2) * gaussian
			return first_derivate_x
		
		# first partial y derivative
		elif order == [0, 1]:
			first_derivate_y = (-y / sigma_y**2) * gaussian
			return first_derivate_y 
		
		# second partial x derivative
		elif order == [2, 0]:
			second_derivative_x = ((x**2 - sigma_x**2) / sigma_x**4) * gaussian
			return second_derivative_x
		
		# second partial y derivative
		elif order == [0, 2]:
			second_derivative_y = ((y**2 - sigma_y**2) / sigma_y**4) * gaussian
			return second_derivative_y
		
		# Laplacian of Gaussian
		elif order == [2, 2]:
			laplacian = ((x**2  + y**2 - 2* sigma**2) / sigma**4) * gaussian
			return laplacian
    
	def dog_filter_bank(self):
		"""
		Generates a bank of 2D Derivative of Gaussian filters at multiple scales and orientations.
		"""
		scales = [1 , sqrt(2)]
		sobel_x = np.array([[1, 0, -1], [2, 0, -2], [1, 0, -1]]) # Sobel filter in x direction
		size = 7
		angles = 16
		bounds = size // 2
		spread = np.linspace(-bounds, bounds, size)
		x, y = np.meshgrid(spread, spread)
		grid = (x, y)

		derivative_gaussian_filters = []

		for sigma in scales:
			gaussian = self.gaussian_filter(grid, sigma)
			gaussian = gaussian.reshape(size, size)
   
			# Apply Sobel filter to get the Derivative of Gaussian
			dog_x = cv2.filter2D(gaussian, ddepth=-1, kernel=sobel_x)
   			# Generate rotated filters 
			for i in range(angles):
				angle = i * 360 / angles
				rotation_matrix = cv2.getRotationMatrix2D((size//2, size//2), angle, 1)
				dog_x_rot = cv2.warpAffine(dog_x, rotation_matrix, (size, size))
				derivative_gaussian_filters.append(dog_x_rot)
    
		return derivative_gaussian_filters

	def LM(self, type):
		"""
		Generate the Leung-Malik (LM) filter bank.

		Parameters:
		type (str): 'small' for the LM Small filter bank or anything else for LM Large.

		Returns:
		list: A list of filters in the LM filter bank.
		"""
		size = 49
		bound = size // 2
		spread = np.linspace(-bound, bound, size)
		x, y = np.meshgrid(spread, spread)
		grid = (x, y)
		elongation = 3
		orientations = 6
		
		if type =='small':
			scales = [1, sqrt(2), 2, 2*sqrt(2)]

		else:
			scales = [sqrt(2), 2, 2*sqrt(2), 4]
			
		LM_filters = []
		for sigma in scales[:3]: 
			first_derivate_x = self.derivative_gaussian_filter(grid, sigma, elongation, order = [1, 0], elongate = 'yes')
			first_derivative_gaussian = first_derivate_x 
			
			second_derivative_x = self.derivative_gaussian_filter(grid, sigma, elongation, order = [2, 0], elongate = 'yes')
			second_derivative_gaussian = second_derivative_x 
			
			# Generate the first-order derivatives of the 2D Gaussian filter at multiple orientations.
			for i in range(orientations):
				angle = i * 360 / orientations
				rot_matrix = cv2.getRotationMatrix2D((size//2, size//2), angle, 1)
				first_derivative_rotated = cv2.warpAffine(first_derivative_gaussian, rot_matrix, (size, size))
				LM_filters.append(first_derivative_rotated)
    
			# Generate the second-order derivatives of the 2D Gaussian filter at multiple orientations.
			for i in range(orientations):
				angle = i * 360 / orientations
				rot_matrix = cv2.getRotationMatrix2D((size//2, size//2), angle, 1)
				second_derivative_rotated = cv2.warpAffine(second_derivative_gaussian, rot_matrix, (size, size))
				LM_filters.append(second_derivative_rotated)
		
		# Generate Laplacian of Gaussian filters at multiple scales.
		for sigma in scales:
			laplacian = self.derivative_gaussian_filter(grid, sigma, elongation, order = [2, 2], elongate = 'no')
			LM_filters.append(laplacian)
			
		# Generate Laplacian of Gaussian filters at 3 * scales.
		for sigma in scales:
			laplacian = self.derivative_gaussian_filter(grid, sigma*3, elongation, order = [2, 2], elongate = 'no')
			LM_filters.append(laplacian)
		
		# Gaussian Smoothing Filters
		for sigma in scales:
			gaussian = self.gaussian_filter(grid, sigma, elongation, elongate = 'no')
			LM_filters.append(gaussian)
			
		return LM_filters

	def gabor(self, orientation, sigma, gamma, psi):
		size = 49
		bounds = size // 2
		spread = np.linspace(-bounds, bounds, size)
		x, y = np.meshgrid(spread, spread)
		gabor_filters = []
		nlambdas = [2, 5, 10, 15, 20]

		for lambda_ in nlambdas:
			for i in range(orientation):
				theta = i * pi / orientation
				x_theta = x * np.cos(theta) + y * np.sin(theta)
				y_theta = -x * np.sin(theta) + y * np.cos(theta)
				gb = np.exp(-0.5 * (x_theta**2 + (gamma**2 * y_theta**2)) / (sigma**2)) * np.cos((2 * pi * x_theta / lambda_) + psi)       
				gabor_filters.append(gb)

		return gabor_filters
    

def main():

	"""
	Generate Difference of Gaussian Filter Bank: (DoG)
	Display all the filters in this filter bank and save image as DoG.png,
	"""
	filter_bank = FilterBank()
	DOG_filters = filter_bank.dog_filter_bank()
	fig, ax = plt.subplots(2, 16, figsize=(20, 3))
	for i in range(2):
		for j in range(16):
			ax[i, j].imshow(DOG_filters[i*4 + j], cmap='gray')
			ax[i, j].axis('off')
			ax[i, j].set_xticks([])

	plt.savefig('DoG1.png')
	plt.show()
	plt.close()
	
	"""
	Generate Leung-Malik Filter Bank: (LM)
	Display all the filters in this filter bank and save image as LM.png,
	use command "cv2.imwrite(...)"
	"""
	LMs_filter_bank = filter_bank.LM('small')
	fig, axs = plt.subplots(4, 12, figsize=(30, 10))
	for i, filter in enumerate(LMs_filter_bank):
		axs[i//12, i%12].imshow(filter, cmap='gray')
		axs[i//12, i%12].axis('off')
	
	plt.savefig('LMs.png')
	plt.show()
	plt.close()

	LMs_filter_bank = filter_bank.LM('large')
	fig, axs = plt.subplots(4, 12, figsize=(30, 10))
	for i, filter in enumerate(LMs_filter_bank):
		axs[i//12, i%12].imshow(filter, cmap='gray')
		axs[i//12, i%12].axis('off')
  
	plt.savefig('LMl.png')
	plt.show()
	plt.close()

	"""
	Generate Gabor Filter Bank: (Gabor)
	Display all the filters in this filter bank and save image as Gabor.png,
	use command "cv2.imwrite(...)"
	"""
	gabor_filters = filter_bank.gabor(orientation = 8, sigma = 8, gamma = 0.65, psi = 0)
	fig, axs = plt.subplots(5, 8, figsize=(30, 10))
	for i, filter in enumerate(gabor_filters):
		axs[i//8, i%8].imshow(filter, cmap='gray')
		axs[i//8, i%8].axis('off')
  
	plt.savefig('Gabor.png')
	plt.show()
	plt.close()

	"""
	Generate Half-disk masks
	Display all the Half-disk masks and save image as HDMasks.png,
	use command "cv2.imwrite(...)"
	"""



	"""
	Generate Texton Map
	Filter image using oriented gaussian filter bank
	"""


	"""
	Generate texture ID's using K-means clustering
	Display texton map and save image as TextonMap_ImageName.png,
	use command "cv2.imwrite('...)"
	"""


	"""
	Generate Texton Gradient (Tg)
	Perform Chi-square calculation on Texton Map
	Display Tg and save image as Tg_ImageName.png,
	use command "cv2.imwrite(...)"
	"""


	"""
	Generate Brightness Map
	Perform brightness binning 
	"""


	"""
	Generate Brightness Gradient (Bg)
	Perform Chi-square calculation on Brightness Map
	Display Bg and save image as Bg_ImageName.png,
	use command "cv2.imwrite(...)"
	"""


	"""
	Generate Color Map
	Perform color binning or clustering
	"""


	"""
	Generate Color Gradient (Cg)
	Perform Chi-square calculation on Color Map
	Display Cg and save image as Cg_ImageName.png,
	use command "cv2.imwrite(...)"
	"""


	"""
	Read Sobel Baseline
	use command "cv2.imread(...)"
	"""


	"""
	Read Canny Baseline
	use command "cv2.imread(...)"
	"""


	"""
	Combine responses to get pb-lite output
	Display PbLite and save image as PbLite_ImageName.png
	use command "cv2.imwrite(...)"
	"""
    
if __name__ == '__main__':
    main()
 


