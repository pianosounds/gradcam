import os

import numpy as np
import tensorflow as tf
from tensorflow.python.framework import ops

from data_utils import prep_image, visualize


@ops.RegisterGradient("GuidedRelu")
def _GuidedReluGrad(op, grad):
    dtype = op.inputs[0].dtype
    return grad * tf.cast(grad > 0., dtype) * tf.cast(op.inputs[0] > 0., dtype)


def GradCam(image_path, meta_path):
    img = prep_image(image_path, (160, 160, 3))
    input_img = (img - 127.5) / 128
    input_img = input_img.astype(np.float32)
    input_img = input_img[np.newaxis, ...]

    ckpt_file = os.path.splitext(meta_path)[0]

    trained_model_graph = tf.Graph()
    with trained_model_graph.as_default():
        with trained_model_graph.gradient_override_map({'Relu': 'GuidedRelu'}):
            sess = tf.Session()
            new_saver = tf.train.import_meta_graph(meta_path)
            new_saver.restore(sess, ckpt_file)

            images_ph = tf.get_default_graph().get_tensor_by_name("image_batch:0")
            labels_ph = tf.get_default_graph().get_tensor_by_name("labels:0")
            phase_train_ph = tf.get_default_graph().get_tensor_by_name("phase_train:0")
            pred_probs = tf.get_default_graph().get_tensor_by_name("prediction:0")
            logits_ph = tf.get_default_graph().get_tensor_by_name("logits/BiasAdd:0")
            target_conv_layer = tf.get_default_graph().get_tensor_by_name("InceptionResnetV1/Mixed_6a/concat:0")

            cost = (-1) * tf.reduce_sum(tf.multiply(labels_ph, tf.log(pred_probs)), axis=1)
            y_c = tf.reduce_sum(tf.multiply(logits_ph, labels_ph), axis=1)

            target_conv_layer_grad = tf.gradients(y_c, target_conv_layer)[0]
            gb_grad = tf.gradients(cost, images_ph)[0]

            prob = sess.run(pred_probs, feed_dict={images_ph: input_img, phase_train_ph: False})

            gb_grad_value, target_conv_layer_value, target_conv_layer_grad_value = sess.run(
                [gb_grad, target_conv_layer, target_conv_layer_grad],
                feed_dict={images_ph: input_img, labels_ph: [[0, 1]], phase_train_ph: False})

            gradBGR = gb_grad_value[0]
            gradRGB = np.dstack((
                gradBGR[:, :, 2],
                gradBGR[:, :, 1],
                gradBGR[:, :, 0],
            ))
            print(prob)
            visualize(img, target_conv_layer_value[0], target_conv_layer_grad_value[0], gradRGB)


if __name__ == '__main__':
    image_path = '/home/eugene/Desktop/test/thispersondoesnotexist_good4.jpeg'
    meta_path = '/home/eugene/git/gender-classifier/checkpoint/model.ckpt-3.meta'

    GradCam(image_path, meta_path)
