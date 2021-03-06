import numpy as np

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import ShuffleSplit, train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.pipeline import Pipeline

from scipy import stats

import matplotlib.pyplot as plt

import argparse

from helper import calculate_aggregate_metric, write_metrics, compute_param_sum, write_model_params



NUM_SPLITS = 100


def read_data(path):
	with open(path, 'r') as f:
		string = f.readline()

	tags = string.replace('"', '').strip().split(sep=',')
	tags.pop(0)

	data = np.genfromtxt(path, delimiter=',')
	data = data[1:]
	data = np.delete(data, 0, 1)
	data = np.swapaxes(data, 0, 1)

	tag_to_label = {'Cancer':1, 'NonCancer':0}

	labels = []
	for tag in tags:
		labels.append(tag_to_label[tag])
	labels = np.array(labels)

	print('data size', data.shape)
	print('labels size', labels.shape)

	return data, labels	


def evaluate_model(pipe, data, labels, data_name, print_details = False):
	outputs = pipe.predict(data)
	accuracy = accuracy_score(labels, outputs)

	predict_proba = np.array([val[1] for val in pipe.predict_proba(data)])
	auc = roc_auc_score(labels, predict_proba)

	if print_details:
		print('Evaluating on', data_name)
		print("Accuracy : %.3f AUC : %.3f" % (accuracy, auc))

	return accuracy, auc


def execute_logistic(data, labels, penalty, significant_weights = None, random_state = 0):
	if not penalty:
		penalty = 'l2'
	if random_state == 0:
		print('\nLogistic Regression with', penalty, 'penalty ....')
	acc_list = []
	auc_list = []

	if significant_weights is not None:
		if significant_weights[0] == 0:
			significant_weights = np.delete(significant_weights, 0)
		significant_weights -= 1
		data = data[:, significant_weights]
		print(data.shape)

	num_params = data.shape[1] + 1
	all_iter_params = np.zeros((NUM_SPLITS, num_params))

	#creating a separate test set for final evaluation
	training_data, test_data, training_labels, test_labels = train_test_split(data, labels, test_size = 0.2, random_state = random_state)
	data = training_data
	labels = training_labels
	if random_state == 0:
		print('training data size :', data.shape, 'training labels size :', labels.shape)
		print('test data size :', test_data.shape, 'test labels size :', test_labels.shape)

	rs = ShuffleSplit(n_splits = NUM_SPLITS, test_size = 0.2, random_state = 0)
	split_count = 0
	for train_index, validation_index in rs.split(data):
		training_data = data[train_index, :]
		training_labels = labels[train_index]
		validation_data = data[validation_index, :]
		validation_labels = labels[validation_index]

		log_reg_model = LogisticRegression(solver = 'liblinear', penalty = penalty) 

		pipe = Pipeline([('scaler', StandardScaler()), ('logreg', log_reg_model)])
		pipe.fit(training_data, training_labels)

		all_iter_params[split_count, :] = np.append(log_reg_model.intercept_, log_reg_model.coef_)

		evaluate_model(pipe, training_data, training_labels, 'training data')
		acc_tmp, auc_tmp = evaluate_model(pipe, validation_data, validation_labels, 'validation data')	
		acc_list.append(acc_tmp)
		auc_list.append(auc_tmp)

		split_count += 1

	if random_state == 0:	
		write_metrics(acc_list, auc_list, write_to_file = False, show_all = False)	

	#evaluating on the separated out test data set
	log_reg_model = LogisticRegression(solver = 'liblinear', penalty = penalty) 
	pipe = Pipeline([('scaler', StandardScaler()), ('logreg', log_reg_model)])
	pipe.fit(data, labels)
	acc, auc = evaluate_model(pipe, test_data, test_labels, 'test data')

	if significant_weights is not None:
		return significant_weights, data.shape[1], acc, auc

	#calculating z value - method 1
	coeff_mean = np.mean(all_iter_params, axis = 0)
	coeff_se = stats.sem(all_iter_params)

	coeff_z = coeff_mean / coeff_se

	coeff_CI_l = np.percentile(all_iter_params, 2.5, axis = 0)
	coeff_CI_u = np.percentile(all_iter_params, 97.5, axis = 0)

	#calculating z value - method 2
	coeff_se_method2 = (coeff_CI_u - coeff_CI_l) / (2 * 1.96)
	coeff_z_method2 = coeff_mean / coeff_se_method2	

	#for now using method2 since, method2 results for Z look better, with shorter z range
	significant_weights = np.argwhere(np.absolute(coeff_z_method2) > 2).flatten()	

	x = np.array([i for i in range(num_params)])

	#show graphs only for 1st epoch
	if random_state == 0:
		plt.plot(x, coeff_mean)
		plt.xlabel('Intercept and Features')
		plt.ylabel('LogReg Model Mean Weights')
		plt.show()
	
		fig, ax = plt.subplots()
		ax.plot(x, coeff_mean)
		ax.fill_between(x, coeff_CI_l, coeff_CI_u, color='g')
		plt.xlabel('Intercept and Features')
		plt.ylabel('LogReg Model Mean Weights with CI')	
		plt.show()
	
		plt.scatter(x, coeff_z, s=2)
		plt.xlabel('Intercept and Features')
		plt.ylabel('LogReg Model Weights Z values - method 1')
		plt.show()
	
		plt.scatter(x, coeff_z_method2, s=2)
		plt.xlabel('Intercept and Features')
		plt.ylabel('LogReg Model Weights Z values')
		plt.show()
	
		print('Number of significant Weights : ', len(significant_weights))
	
		plt.scatter(significant_weights, coeff_z_method2[significant_weights], s = 2)
		plt.xlabel('Intercept and Features Selected')
		plt.ylabel('LogReg Model Weights Z values')
		plt.show()
	
	return significant_weights, data.shape[1], acc, auc


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--file_path", "-fp", type = str, required = True, help = 'File path including the file name of the data file')
	parser.add_argument("--penalty", "-p", type = str, help = 'penalty used in logistic regression regularization (only supports l1 and l2, default is l2)')
	parser.add_argument("--epochs", "-e", type = int, help = 'Number of train test combinations created to report accuracy and auc (default = 10)' \
		+ 'For each such combination, 100 combinations of train-validation are created to obtain model param distribution')	
	args = parser.parse_args()

	path = args.file_path
	penalty = args.penalty
	epochs = args.epochs
	if epochs is None:
		epochs = 10

	print('Executing the model on', path.split('/')[-1], 'with', epochs, 'epochs')

	data, labels = read_data(path)

	acc_list = []
	auc_list = []
	acc_list_filtered = []
	auc_list_filtered = []
	avg_num_significant_features = 0.0
	for i in range(epochs):
		significant_weights, _, acc, auc = execute_logistic(data, labels, penalty, random_state = i)
		significant_weights, num_significant_features, acc_filt, auc_filt = execute_logistic(data, labels, penalty, significant_weights, random_state = i)
		acc_list.append(acc)
		auc_list.append(auc)
		acc_list_filtered.append(acc_filt)
		auc_list_filtered.append(auc_filt)
		avg_num_significant_features += num_significant_features
	avg_num_significant_features /= epochs

	print('Average number of significant features :', avg_num_significant_features)
	print('\nResults on test data with all features...')	
	write_metrics(acc_list, auc_list, write_to_file = False, show_all = False)		
	print('\nResults on test data with filtered features...')
	write_metrics(acc_list_filtered, auc_list_filtered, write_to_file = False, show_all = False)

if __name__ == '__main__':
	main()