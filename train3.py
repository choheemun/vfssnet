from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import numpy as np
import tensorflow as tf
# libs/datasets/dataset_factory.py
# from libs.visualization.summary_utils import visualize_input
import glob
import time
from tensorflow.python.lib.io.tf_record import TFRecordCompressionType
from tensorflow.python import keras
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Activation
from tensorflow.keras import backend as k
from tensorflow.keras.layers import Dense
from tensorflow.keras.metrics import categorical_accuracy as accuracy
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.layers import Dense, Input, Activation, Conv2D, Conv2DTranspose, Flatten, Dropout, MaxPool2D
from tensorflow.keras.layers import BatchNormalization
from tensorflow.keras.models import Model
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras import optimizers
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.losses import categorical_crossentropy  # tensorflow.keras.objectives는 tf 1.12에는 없는듯




# libs/datasets/dataset_factory.py
def get_dataset(dataset_dir, is_training=False, file_pattern=None, reader=None):  # dataset_dir='./dataset/photo/'
    """"""
    tfrecords = glob.glob(dataset_dir + '/records/' + 'coco_tfrecord')
    image, ih, iw, gt_boxes, gt_masks, num_instances, img_id = read(tfrecords)

    image, gt_boxes, gt_masks = preprocess_image(image, gt_boxes, gt_masks,
                                                 is_training)  # is_training=True (def train 참조)
    # visualize_input(gt_boxes, image, tf.expand_dims(gt_masks, axis=3))

    return image, ih, iw, gt_boxes, gt_masks, num_instances, img_id


def preprocess_image(image, gt_boxes, gt_masks, is_training=False):
    """preprocess image for coco
    1. random flipping
    2. min size resizing
    3. zero mean
    4. ...
    """
    if is_training:
        return preprocess_for_training(image, gt_boxes, gt_masks)
    else:
        return preprocess_for_test(image, gt_boxes, gt_masks)


def preprocess_for_training(image, gt_boxes, gt_masks):
    ih, iw = tf.shape(image)[0], tf.shape(image)[1]
    '''
    ## random flipping

    coin = tf.to_float(tf.random_uniform([1]))[0]
    image, gt_boxes, gt_masks = \
        tf.cond(tf.greater_equal(coin, 0.5),
                lambda: (preprocess_utils.flip_image(image),
                         preprocess_utils.flip_gt_boxes(gt_boxes, ih, iw),
                         preprocess_utils.flip_gt_masks(gt_masks)),
                lambda: (image, gt_boxes, gt_masks))

    ## min size resizing
    new_ih, new_iw = preprocess_utils._smallest_size_at_least(ih, iw, cfg.FLAGS.image_min_size)
    image = tf.expand_dims(image, 0)
    image = tf.image.resize_bilinear(image, [new_ih, new_iw], align_corners=False)
    image = tf.squeeze(image, axis=[0])

    gt_masks = tf.expand_dims(gt_masks, -1)
    gt_masks = tf.cast(gt_masks, tf.float32)
    gt_masks = tf.image.resize_nearest_neighbor(gt_masks, [new_ih, new_iw], align_corners=False)
    gt_masks = tf.cast(gt_masks, tf.int32)
    gt_masks = tf.squeeze(gt_masks, axis=[-1])

    scale_ratio = tf.to_float(new_ih) / tf.to_float(ih)
    gt_boxes = preprocess_utils.resize_gt_boxes(gt_boxes, scale_ratio)
    '''
    ## random flip image
    # val_lr = tf.to_float(tf.random_uniform([1]))[0]
    # image = tf.cond(val_lr > 0.5, lambda: preprocess_utils.flip_image(image), lambda: image)
    # gt_masks = tf.cond(val_lr > 0.5, lambda: preprocess_utils.flip_gt_masks(gt_masks), lambda: gt_masks)
    # gt_boxes = tf.cond(val_lr > 0.5, lambda: preprocess_utils.flip_gt_boxes(gt_boxes, new_ih, new_iw), lambda: gt_boxes)

    ## zero mean image
    image = tf.cast(image, tf.float32)
    image = image / 255.0
    image = (image - 0.5) * 2.0
    image = tf.expand_dims(image, axis=0)

    ## rgb to bgr
    image = tf.reverse(image, axis=[-1])

    return image, gt_boxes, gt_masks


def preprocess_for_test(image, gt_boxes, gt_masks):
    ih, iw = tf.shape(image)[0], tf.shape(image)[1]

    ## min size resizing
    # new_ih, new_iw = preprocess_utils._smallest_size_at_least(ih, iw, cfg.FLAGS.image_min_size)
    # image = tf.expand_dims(image, 0)
    # image = tf.image.resize_bilinear(image, [new_ih, new_iw], align_corners=False)
    # image = tf.squeeze(image, axis=[0])

    # gt_masks = tf.expand_dims(gt_masks, -1)
    # gt_masks = tf.cast(gt_masks, tf.float32)
    # gt_masks = tf.image.resize_nearest_neighbor(gt_masks, [new_ih, new_iw], align_corners=False)
    # gt_masks = tf.cast(gt_masks, tf.int32)
    # gt_masks = tf.squeeze(gt_masks, axis=[-1])

    # scale_ratio = tf.to_float(new_ih) / tf.to_float(ih)
    # gt_boxes = preprocess_utils.resize_gt_boxes(gt_boxes, scale_ratio)

    ## zero mean image
    image = tf.cast(image, tf.float32)
    image = image / 256.0
    image = (image - 0.5) * 2.0
    image = tf.expand_dims(image, axis=0)

    ## rgb to bgr
    image = tf.reverse(image, axis=[-1])

    return image, gt_boxes, gt_masks


def read(tfrecords_filename):
    if not isinstance(tfrecords_filename, list):
        tfrecords_filename = [tfrecords_filename]
    filename_queue = tf.train.string_input_producer(
        tfrecords_filename, num_epochs=100000)

    options = tf.python_io.TFRecordOptions(TFRecordCompressionType.ZLIB)
    reader = tf.TFRecordReader(options=options)
    _, serialized_example = reader.read(filename_queue)
    features = tf.parse_single_example(
        serialized_example,
        features={
            'image/img_id': tf.FixedLenFeature([], tf.int64),
            'image/encoded': tf.FixedLenFeature([], tf.string),
            'image/height': tf.FixedLenFeature([], tf.int64),
            'image/width': tf.FixedLenFeature([], tf.int64),
            'label/num_instances': tf.FixedLenFeature([], tf.int64),
            'label/gt_masks': tf.FixedLenFeature([], tf.string),
            'label/gt_boxes': tf.FixedLenFeature([], tf.string),
            'label/encoded': tf.FixedLenFeature([], tf.string),
        })
    # image = tf.image.decode_jpeg(features['image/encoded'], channels=3)
    img_id = tf.cast(features['image/img_id'], tf.int32)
    ih = tf.cast(features['image/height'], tf.int32)
    iw = tf.cast(features['image/width'], tf.int32)
    num_instances = tf.cast(features['label/num_instances'], tf.int32)
    image = tf.decode_raw(features['image/encoded'], tf.uint8)
    imsize = tf.size(image)
    image = tf.cond(tf.equal(imsize, ih * iw), \
                    lambda: tf.image.grayscale_to_rgb(tf.reshape(image, (ih, iw, 1))), \
                    lambda: tf.reshape(image, (ih, iw, 3)))

    gt_boxes = tf.decode_raw(features['label/gt_boxes'], tf.float32)
    gt_boxes = tf.reshape(gt_boxes, [num_instances, 5])  # of shape (N, 5), (x1, y1, x2, y2, classid)
    gt_masks = tf.decode_raw(features['label/gt_masks'], tf.uint8)
    gt_masks = tf.cast(gt_masks, tf.int32)
    gt_masks = tf.reshape(gt_masks, [num_instances, ih, iw])

    return image, ih, iw, gt_boxes, gt_masks, num_instances, img_id


'''
# mnist dataset 저장할 디렉터리
save_dir = '../data/mnist'     # 상위폴더 안의 data 폴더의 mnist 폴더

# save_dir에 MNIST 데이터 받기
data_sets = mnist.read_data_sets(save_dir,
                                 dtype=tf.uint8,
                                 reshape=False,
                                 validation_size=1000)

data_splits = ['train', 'test', 'validation']
for i, split in enumerate(data_splits):
    print("saving %s" % split)
    data_set = data_sets[i]
'''


def root_mean_squared_error(y_true, y_pred):
    return tf.sqrt(tf.reduce_mean(tf.losses.mean_squared_error(y_true, y_pred)))


def train():
    """The main function that runs training"""

    ## data

    dataset_dir = './dataset/photo'
    image, ih, iw, gt_boxes, gt_masks, num_instances, img_id = \
        get_dataset(dataset_dir, is_training=True)

    data_queue = tf.RandomShuffleQueue(capacity=32, min_after_dequeue=0,
                                       dtypes=(
                                           image.dtype, ih.dtype, iw.dtype,
                                           gt_boxes.dtype, gt_masks.dtype,
                                           num_instances.dtype, img_id.dtype))
    enqueue_op = data_queue.enqueue((image, ih, iw, gt_boxes, gt_masks, num_instances, img_id))
    data_queue_runner = tf.train.QueueRunner(data_queue, [enqueue_op] * 2)
    tf.add_to_collection(tf.GraphKeys.QUEUE_RUNNERS, data_queue_runner)
    (image, ih, iw, gt_boxes, gt_mask, num_instances, img_id) = data_queue.dequeue()  # 여기서 image, gt_mask, img_id만 쓴다
    im_shape = tf.shape(image)
    image = tf.reshape(image, (im_shape[0], im_shape[1], im_shape[2], 3))
    gt_mask = tf.cast(gt_mask, tf.float32)

    gt_boxes = tf.reshape(gt_boxes, (-1, 5))
    gt_box = gt_boxes[:, :4]  # of shape (N, 5), (x1, y1, x2, y2, classid)



    image = tf.image.resize_bilinear(image, [448, 448])
    # gt_mask = tf.expand_dims(gt_mask, axis=3)
    # gt_mask = tf.image.resize_bilinear(gt_mask, [56, 56])










    W = tf.random.uniform([2], 190, 224)
    W = tf.round(W)
    a=W[0]
    b=W[1]
    image=tf.image.resize_bilinear(image, [2*a, 2*b])
    padding=[[0,0],[224-a,224-a],[224-b,224-b],[0,0]]
    image = tf.pad(image, padding,mode="CONSTANT")
    gt_box=gt_box*(2*a/448,2*b/448,2*a/448,2*b/448)
    gt_box=gt_box + (224-a,224-b,224-a,224-b)

    gt_box = gt_box / 200  # w=200, h=200  추후에 변경




    model = ResNet50(input_tensor=image, include_top=False, weights='imagenet', pooling='max')
    model.trainable = False

    selected_model1 = Model(inputs=model.input,
                            outputs=model.get_layer('activation_48').output)  # output=(None, 14, 14, 2048)
    selected_model2 = Model(inputs=model.input,
                            outputs=model.get_layer('activation_39').output)  # output=(None, 28, 28, 1024)
    selected_model3 = Model(inputs=model.input,
                            outputs=model.get_layer('activation_21').output)  # output=(None, 56, 56, 512)
    selected_model4 = Model(inputs=model.input,
                            outputs=model.get_layer('activation_9').output)  # output=(None, 112, 112, 256)
    # selected_model1 ~ 3 으로만 pyramid를 build 하자

    y1 = selected_model1.output
    y2 = selected_model2.output
    y3 = selected_model3.output
    y4 = selected_model4.output

    pyramid_1 = Conv2D(filters=256, strides=(1, 1), kernel_size=(1, 1), activation='relu',
                       kernel_initializer='he_normal', padding='same', name="P1")(y1)  # (None, 14, 14, 256)

    pre_P2_1 = tf.image.resize_bilinear(pyramid_1, [28, 28], name='pre_P2_1')  # (None, 28, 28, 256)
    pre_P2_2 = Conv2D(filters=256, strides=(1, 1), kernel_size=(1, 1), activation='relu',
                      kernel_initializer='he_normal', padding='same', name="pre_p2_2")(y2)  # (None, 28, 28, 256)
    pre_P2_2 = BatchNormalization()(pre_P2_2)
    pre_P2 = tf.add(pre_P2_1, pre_P2_2)  # (None, 28, 28, 256)

    pyramid_2 = Conv2D(filters=256, strides=(1, 1), kernel_size=(3, 3), activation='relu',
                       kernel_initializer='he_normal', padding='same', name="P2")(pre_P2)  # (None, 28, 28, 256)
    pyramid_2 = BatchNormalization()(pyramid_2)

    pre_P3_1 = tf.image.resize_bilinear(pyramid_2, [56, 56], name='pre_P3_1')  # (None, 56, 56, 256)
    pre_P3_2 = Conv2D(filters=256, strides=(1, 1), kernel_size=(1, 1), activation='relu',
                      kernel_initializer='he_normal', padding='same', name="pre_p3_2")(y3)  # (None, 56, 56, 256)
    pre_P3_2 = BatchNormalization()(pre_P3_2)

    pre_P3 = tf.add(pre_P3_1, pre_P3_2)  # (None, 56, 56, 256)
    pyramid_3 = Conv2D(filters=256, strides=(1, 1), kernel_size=(3, 3), activation='relu',
                       kernel_initializer='he_normal', padding='same', name="P3")(pre_P3)  # (None, 56, 56, 256)
    pyramid_3 = BatchNormalization()(pyramid_3)
    m = pyramid_3

    # pre_P4_1= =tf.image.resize_bilinear(pyramid_2, [112,112], name='pre_P4_1')                                                   #(None, 112, 112, 256)
    # pre_P4_2 = Conv2D(filters=256, strides=(1, 1), kernel_size=(1, 1), activation='relu', padding='same', name="pre_p4_2")(y4)   #(None, 112, 112, 256)
    # pre_P4=tf.add(pre_P4_1,pre_P4_2)                                                                                             #(None, 112, 112, 256)
    # pyramid_4=Conv2D(filters=256, strides=(1, 1), kernel_size=(3, 3), activation='relu', padding='same', name="P4")(pre_P4)      #(None, 112, 112, 256)

    for _ in range(3):  # (None, 56, 56, 256)-> (None, 7,7,512)
        for _ in range(3):
            m = Conv2D(filters=512, strides=(1, 1), kernel_size=(3, 3), activation='relu',
                       kernel_initializer='he_normal', padding='same', name="C1")(m)
            m = BatchNormalization()(m)

        m = MaxPool2D(pool_size=(2, 2), strides=(2, 2), padding='valid')(m)

    m = Flatten()(m)  # (None,7,7,512) -> (none, 39424)
    m = Dense(1024, activation='relu', kernel_initializer='he_normal')(m)
    m = BatchNormalization()(m)
    m = m / 100
    m = Dropout(0.3)(m)
    m = Dense(1024, activation='relu', kernel_initializer='he_normal')(m)
    m = BatchNormalization()(m)
    m = m / 100
    m = Dropout(0.3)(m)
    m = Dense(256, activation='relu', kernel_initializer='he_normal')(m)
    m = BatchNormalization()(m)
    m = m / 100
    box = Dense(4, activation='sigmoid', kernel_initializer='glorot_normal')(m)

    global_step = tf.Variable(0, trainable=False, name='global_step')
    loss = root_mean_squared_error(gt_box, box)  # (None, 4)  vs  (None, 4)
    train_step = tf.train.AdamOptimizer(learning_rate=0.000001).minimize(loss, global_step=global_step)

    sess = tf.Session()
    k.set_session(sess)

    with tf.Session() as sess:

        # option 1
        # init = tf.global_variables_initializer()
        # sess.run(init)
        # init = tf.local_variables_initializer()
        # sess.run(init)
        saver = tf.train.Saver(tf.global_variables(), max_to_keep=20)
        ckpt = tf.train.get_checkpoint_state('dataset/checkpoint/checkpoint1')
        if ckpt and tf.train.checkpoint_exists(ckpt.model_checkpoint_path):
            #saver.restore(sess, ckpt.model_checkpoint_path)  # 1.단순히 epoch를 연장하여 학습을 이어가는 경우
            saver.restore(sess, "dataset/checkpoint/checkpoint2/nn.ckpt-3303")              # 2.over fitting 이 확인되어 특정 epoch를 선택하여 학습을 이어가는 경우
            # 1 or 2 중 하나만 실행시키면 된다.
            sess.run(tf.local_variables_initializer())  # string_input_producer 의 epoch 때문...

        else:
            sess.run(tf.global_variables_initializer())
            sess.run(tf.local_variables_initializer())

        coord = tf.train.Coordinator()
        threads = []
        # print (tf.get_collection(tf.GraphKeys.QUEUE_RUNNERS))
        for qr in tf.get_collection(tf.GraphKeys.QUEUE_RUNNERS):
            threads.extend(qr.create_threads(sess, coord=coord, daemon=True,
                                             start=True))

        tf.train.start_queue_runners(sess=sess, coord=coord)

        for step in range(10000):
            sess.run(train_step)  # feed_dict를 쓰지 않는다. input pipeline 이 data를 feed 해준다
            if step % 100 == 0:
                loss_val = sess.run(loss)
                print('Step: {:4d} | Loss: {:.5f}'.format(step, loss_val))
                #print(sess.run([gt_box, box,W]))
                print(sess.run([box]))
                print('-')
                checkpoint_path = os.path.join('dataset/checkpoint/checkpoint1', 'nn.ckpt')
                saver.save(sess, checkpoint_path, global_step=global_step)
            if coord.should_stop():
                coord.request_stop()
                coord.join(threads)


'''
    init_op = tf.global_variables_initializer()
    sess.run(init_op)

    for i in range(10000):
        _, cost = sess.run([train_step, loss])              # feed_dict를 쓰지 않는다. input pipeline 이 data를 feed 해준다
        if i % 100 == 0:
            print(i)
            print(cost)

    sess.close()


    # imshow()
'''

'''
#간단한 NN
W = tf.get_variable('W', [28 * 28, 10])
y_pred = tf.matmul(images_batch, W)

# loss
loss = tf.reduce_mean(
    tf.nn.sparse_softmax_cross_entropy_with_logits(logits=y_pred,
                                                   labels=labels_batch))
# optimizer
train_op = tf.train.AdamOptimizer().minimize(loss)

with tf.Session() as sess:
    init = tf.global_variables_initializer()
    sess.run(init)
    init = tf.local_variables_initializer()
    sess.run(init)

    # coordinator
    coord = tf.train.Coordinator()
    threads = tf.train.start_queue_runners(sess=sess, coord=coord)
    print(threads)
    try:
        step = 0
        while not coord.should_stop():
            step += 1
            sess.run([train_op])  # feed_dict를 쓰지 않는다. input pipeline 이 data를 feed 해준다
            if step % 500 == 0:
                loss_val = sess.run(loss)
                print('Step: {:4d} | Loss: {:.5f}'.format(step, loss_val))
    except tf.errors.OutOfRangeError:
        print('Done training for %d epochs, %d steps.' % (NUM_EPOCHS, step))
    finally:
        # 완료되면 스레드 중지를 요청한다.
        coord.request_stop()

    # 스레드가 완료되길 기다린다.
    coord.join(threads)

    # example -- get image,label
    # img1, lbl1 = sess.run([image, label])

    # example - get random batch
    # labels, images = sess.run([labels_batch, images_batch])

'''

if __name__ == '__main__':
    train()