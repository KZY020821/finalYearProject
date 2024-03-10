import os
from PIL import Image
import numpy as np

from keras.models import Sequential
from keras.layers import Conv2D
from keras.layers import AveragePooling2D
from keras.layers import Flatten
from keras.layers import Dense
from keras.models import model_from_json
from keras.preprocessing.image import ImageDataGenerator

from imageio import imread
from skimage.transform import resize
from imageio import imsave
from PIL import Image

import os
import sys

# Get the absolute path of the current file
current_file_path = os.path.abspath(__file__)

# Go up two levels to get the base directory
base_path = os.path.dirname(os.path.dirname(current_file_path))

# Add the base path to sys.path
sys.path.append(base_path)


IMG_SIZE = 24  # or the desired size for resizing

def collect():
	train_datagen = ImageDataGenerator(
			rescale=1./255,
			shear_range=0.2,
			horizontal_flip=True, 
		)

	val_datagen = ImageDataGenerator(
			rescale=1./255,
			shear_range=0.2,
			horizontal_flip=True,		)

	train_generator = train_datagen.flow_from_directory(
	    directory="dataset/train",
	    target_size=(IMG_SIZE, IMG_SIZE),
	    color_mode="grayscale",
	    batch_size=32,
	    class_mode="binary",
	    shuffle=True,
	    seed=42
	)

	val_generator = val_datagen.flow_from_directory(
	    directory="dataset/val",
	    target_size=(IMG_SIZE, IMG_SIZE),
	    color_mode="grayscale",
	    batch_size=32,
	    class_mode="binary",
	    shuffle=True,
	    seed=42
	)
	return train_generator, val_generator


def save_model(model):
	model_json = model.to_json()
	with open("model.json", "w") as json_file:
		json_file.write(model_json)
	# serialize weights to HDF5
	model.save_weights("face_rec-master/model.h5")

def load_model():
	json_file = open('face_rec-master/model.json', 'r')
	loaded_model_json = json_file.read()
	json_file.close()
	loaded_model = model_from_json(loaded_model_json)
	# load weights into new model
	loaded_model.load_weights("face_rec-master/model.h5")
	loaded_model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
	return loaded_model

def train(train_generator, val_generator):
	STEP_SIZE_TRAIN=train_generator.n//train_generator.batch_size
	STEP_SIZE_VALID=val_generator.n//val_generator.batch_size

	print('[LOG] Intialize Neural Network')
	
	model = Sequential()

	model.add(Conv2D(filters=6, kernel_size=(3, 3), activation='relu', input_shape=(IMG_SIZE,IMG_SIZE,1)))
	model.add(AveragePooling2D())

	model.add(Conv2D(filters=16, kernel_size=(3, 3), activation='relu'))
	model.add(AveragePooling2D())

	model.add(Flatten())

	model.add(Dense(units=120, activation='relu'))

	model.add(Dense(units=84, activation='relu'))

	model.add(Dense(units=1, activation = 'sigmoid'))


	model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])

	model.fit_generator(generator=train_generator,
	                    steps_per_epoch=STEP_SIZE_TRAIN,
	                    validation_data=val_generator,
	                    validation_steps=STEP_SIZE_VALID,
	                    epochs=20
	)
	save_model(model)

def predict(img, model):
    # Convert the image to a NumPy array if it's not already
    img_array = np.array(img)

    # Resize the image
    img_resized = resize(img_array, (IMG_SIZE, IMG_SIZE)).astype('float32')

    # Convert the resized image to grayscale
    img_gray = Image.fromarray(img_resized, 'RGB').convert('L')

    # Resize the grayscale image
    img_gray_resized = resize(np.array(img_gray), (IMG_SIZE, IMG_SIZE)).astype('float32')

    # Normalize the pixel values
    img_gray_resized /= 255

    # Reshape the image for the model input
    img_reshaped = img_gray_resized.reshape(1, IMG_SIZE, IMG_SIZE, 1)

    # Make the prediction
    prediction = model.predict(img_reshaped)

    # Interpret the prediction
    if prediction < 0.1:
        return 'closed'
    elif prediction > 0.9:
        return 'open'
    else:
        return 'idk'

def evaluate(X_test, y_test):
	model = load_model()
	print('Evaluate model')
	loss, acc = model.evaluate(X_test, y_test, verbose = 0)
	print(acc * 100)

if __name__ == '__main__':	
	train_generator , val_generator = collect()
	train(train_generator,val_generator)
