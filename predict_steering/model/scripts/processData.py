#!/usr/bin/python
## Date: June, 29,2017
# process the data into keras
# most of this is taken from https://github.com/upul/Behavioral-Cloning/blob/master/helper.py

import errno
import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.misc
from scipy.ndimage import rotate
from scipy.stats import bernoulli

# Some useful constants paths for csv and images
dataPath = '../../dataset/yaml_files/data2.csv'
imPath = '../../dataset/center/'

# constant added for better training, as most of the time steering is 0
# STEERING_CONSTANT = 0.229

# locations of the data in the csv file
steering=1
center=0

def crop(image, top_percent, bottom_percent):
    """
    Crops an image according to the given parameters

    :param image: source image
    :param top_percent:
        The percentage of the original image will be cropped from the top of the image
    :param bottom_percent:
        The percentage of the original image will be cropped from the bottom of the image
    :return:
        The cropped image
    """
    assert 0 <= top_percent < 0.5, 'top_percent should be between 0.0 and 0.5'
    assert 0 <= bottom_percent < 0.5, 'top_percent should be between 0.0 and 0.5'

    top = int(np.ceil(image.shape[0] * top_percent))
    bottom = image.shape[0] - int(np.ceil(image.shape[0] * bottom_percent))

    return image[top:bottom, :]


def resize(image, new_dim):
    """
    Resize a given image according the the new dimension

    :param image:
        Source image
    :param new_dim:
        A tuple which represents the resize dimension
    :return:
        Resize image
    """
    return scipy.misc.imresize(image, new_dim)


def randomFlip(image, steering_angle, flipping_prob=0.5):
    """
    image is flipped with 0,5 probability
    steering angle is negated if image is flipped

    :param image: Source image
    :param steering_angle: Original steering angle
    :return: Both flipped image and new steering angle
    """
    head = bernoulli.rvs(flipping_prob)
    if head:
        return np.fliplr(image), -1 * steering_angle
    else:
        return image, steering_angle


def randomGamma(image):
    """
    Random gamma correction is used as an alternative method changing the brightness of
    training images.
    http://www.pyimagesearch.com/2015/10/05/opencv-gamma-correction/

    :param image:
        Source image

    :return:
        New image generated by applying gamma correction to the source image
    """
    gamma = np.random.uniform(0.4, 1.5)
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255
                      for i in np.arange(0, 256)]).astype("uint8")

    # apply gamma correction using the lookup table
    return cv2.LUT(image, table)


def randomShear(image, steering_angle, shear_range=200):
    """
    Source: https://medium.com/@ksakmann/behavioral-cloning-make-a-car-drive-like-yourself-dc6021152713#.7k8vfppvk

    :param image:
        Source image on which the shear operation will be applied
    :param steering_angle:
        The steering angle of the image
    :param shear_range:
        Random shear between [-shear_range, shear_range + 1] will be applied

    :return:
        The image generated by applying random shear on the source image
    """
    rows, cols, ch = image.shape
    dx = np.random.randint(-shear_range, shear_range + 1)
    random_point = [cols / 2 + dx, rows / 2]
    pts1 = np.float32([[0, rows], [cols, rows], [cols / 2, rows / 2]])
    pts2 = np.float32([[0, rows], [cols, rows], random_point])
    dsteering = dx / (rows / 2) * 360 / (2 * np.pi * 25.0) / 6.0
    M = cv2.getAffineTransform(pts1, pts2)
    image = cv2.warpAffine(image, M, (cols, rows), borderMode=1)
    steering_angle += dsteering

    return image, steering_angle


def randomRotation(image, steering_angle, rotation_amount=15):
    """
    :param image:
    :param steering_angle:
    :param rotation_amount:
    :return:
    """
    angle = np.random.uniform(-rotation_amount, rotation_amount + 1)
    rad = (np.pi / 180.0) * angle
    return rotate(image, angle, reshape=False), steering_angle + (-1) * rad

def processGenerateImageAngle(image, steering_angle, top_crop_percent=0.3, bottom_crop_percent=0.27,
                       resize_dim=(64, 64), do_shear_prob=0.5):

    """
    Applies all the image procssing and returns the steering angle with the image

    :param image:
    :param steering_angle:
    :param top_crop_percent:
    :param bottom_crop_percent:
    :param resize_dim:
    :param do_shear_prob:
    :param shear_range:
    :return:
    """


    # shear image
    if(bernoulli.rvs(do_shear_prob)):
        image, steering_angle = randomShear(image, steering_angle)

    # crop image
    image = crop(image, top_crop_percent, bottom_crop_percent)

    # flip the image
    image, steering_angle = randomFlip(image, steering_angle)

    # random gamma
    # image = randomGamma(image)

    # resize
    image = resize(image, resize_dim)

    return image, steering_angle


def fetchImages(batch_size=128):
    """
    The simulator records three images (left, center, and right)
    we are fetch images for training randomly one of these three images and its steering angle.

    :param batch_size:
        Size of the image batch

    :return:
        An list of selected (image files names, respective steering angles)
    """
    thresh_prob=0.2
    thresh = 0
    data = pd.read_csv(dataPath)
    num_of_img = len(data)
    rnd_indices = np.random.randint(0, num_of_img, batch_size)
    image_files_and_angles = []

    # for index in rnd_indices:
    #     img = data.iloc[index]['center'].strip()
    #     angle = data.iloc[index]['steering']
    #     image_files_and_angles.append((img, angle))

    count=0    
    while(count<batch_size):
        index=np.random.randint(0,num_of_img)
        img = str(data.iloc[index]['center']).strip()
        angle = data.iloc[index]['steering']
        if ( angle ==thresh ):
            if(bernoulli.rvs(thresh_prob)):
                image_files_and_angles.append((img,angle))
                count=count+1
        else:
            image_files_and_angles.append((img,angle))
            count=count+1

    return image_files_and_angles


def genBatch(batch_size=128):
    """
    This is a generator which yields the next training batch

    :param batch_size:
        Number of training images in a single batch

    :return:
        A tuple of features and steering angles as two numpy arrays
    """
    while True:
        X_batch = []
        y_batch = []
        images = fetchImages(batch_size)
        for img_file, angle in images:
            raw_image = plt.imread(imPath + img_file)
            raw_angle = float(angle)
            new_image, new_angle = processGenerateImageAngle(raw_image, raw_angle)
            X_batch.append(new_image)
            y_batch.append(new_angle)

        assert len(X_batch) == batch_size, 'len(X_batch) == batch_size should be True'

        yield np.array(X_batch), np.array(y_batch)
