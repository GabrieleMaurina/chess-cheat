import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
import numpy as np
from finder import find_grayscale_tiles
from utils import shorten_fen, unflip_fen, get_castling_status

def load_graph(frozen_graph_filepath):
	with tf.io.gfile.GFile(frozen_graph_filepath, "rb") as f:
		graph_def = tf.compat.v1.GraphDef()
		graph_def.ParseFromString(f.read())
	with tf.Graph().as_default() as graph:
		tf.import_graph_def(graph_def, name="tcb")
	return graph

class Board():
	def __init__(self, frozen_graph_path='model.pb'):
		graph = load_graph(frozen_graph_path)
		self.sess = tf.compat.v1.Session(graph=graph)
		self.x = graph.get_tensor_by_name('tcb/Input:0')
		self.keep_prob = graph.get_tensor_by_name('tcb/KeepProb:0')
		self.prediction = graph.get_tensor_by_name('tcb/prediction:0')
		self.probabilities = graph.get_tensor_by_name('tcb/probabilities:0')

	def fen(self, img, active):
		tiles, corners = find_grayscale_tiles(img)
		if tiles is None or len(tiles) == 0: return None, None
		validation_set = np.swapaxes(np.reshape(tiles, [32*32, 64]),0,1)

		guess_prob, guessed = self.sess.run(
		[self.probabilities, self.prediction], 
		feed_dict={self.x: validation_set, self.keep_prob: 1.0})

		labelIndex2Name = lambda label_index: ' KQRBNPkqrbnp'[label_index]
		pieceNames = list(map(lambda k: '1' if k == 0 else labelIndex2Name(k), guessed))
		fen = '/'.join([''.join(pieceNames[i*8:(i+1)*8]) for i in reversed(range(8))])
		
		castling = get_castling_status(fen)
		if active == 'b':
			fen = unflip_fen(fen)
		fen = shorten_fen(fen)

		fen = '{} {} {} - 0 1'.format(fen, active, castling)
		return fen, list(corners)

	def close(self):
		self.sess.close()