import numpy as np
import sys 
import os
import os.path
from scipy import io as sio
from keras.utils import np_utils
from src.utils.seq_dataset import load_data
from src.utils.sequence_3d import pad_sequences_3d, extract_feat, create_BP_mask,preprocess_data
from src.models.create_model import create_MP_model
from src.utils.opt_parser import mp_parser, process_params
from src.utils.data_generator import mp_data_generator
from sklearn import svm
from src.utils.bof_utils import compute_bof_hist
#np.random.seed(1337)  # for reproducibility
#sys.setrecursionlimit(50000)


parser = mp_parser()
params = parser.parse_args()
params = vars(params)
data_gen_params = process_params(params)

dataset = params['dataset']
if dataset =='MSR3D' or dataset == 'MSRDaily':
    subset = [1]
elif dataset =='CompAct':
    subset = range(1,15)

# change basedir to the folder where data are saved. 
# It should have same format as the provided data in data folder
basedir = '~/work/Data/'
filename = '/scratch/users/ltao4@jhu.edu/mp_journal/{}/{}/nword{}_lr{}_obj{}_opt{}_decay{}_l1{}_reg{}_layer{}_rs{}_multi{}.mat'.format(dataset,params['exp_name'],params['num_MP'],params['learning_rate'],'hinge', params['opt_method'],params['decay'],params['l1_alpha'],params['reg_weight'],params['tp_layer'],params['rs'],params['multi_ts'])

if os.path.isfile(filename):
    sys.exit("file already exists!")

# load body part config info, generate mask
joint_map={'MSR3D':20,'MSRDaily':20,'CompAct':20,'MHAD':35,'HDM05':31,'CAD120':15}
njoints = joint_map[dataset]
input_dim = 3*njoints*data_gen_params['window_size']*(data_gen_params['compute_vec']+1)
input_dims = input_dim*np.ones(len(data_gen_params['sample_rate_set'])) 
full_BP = np.arange(njoints)+1
W_mask = create_BP_mask(dataset, params['num_MP'], input_dim) 
MP_per_model = W_mask.shape[-1]
if params['use_fb']:
    W_mask = None
    MP_per_model = params['num_MP']
data_gen_params['padding'] = 0
data_generation = True
label_all = []
test_acc_all = []
for sub in subset:
    print("Loading Data...")
    
    X_train, y_train, X_test, y_test = load_data(basedir, dataset, data_gen_params['features'], sub)
    nb_classes = len(np.unique(y_train))
    Y_train = np_utils.to_categorical(y_train, nb_classes)
    Y_test = np_utils.to_categorical(y_test, nb_classes)


    X_BP_train, X_BP_test = preprocess_data(X_train, X_test, data_gen_params)         
    # train a codebook
    hist_train, hist_test = compute_bof_hist(X_BP_train[0], X_BP_test[0],params['num_MP'])
    #hist_train = hist_train.astype('float64')/hist_train.sum(axis=1,keepdims=True)
    #hist_test = hist_test.astype('float64')/hist_test.sum(axis=1,keepdims=True)

    # svm training
    clf = svm.LinearSVC()
    clf.fit(hist_train,y_train)
    label = clf.predict(hist_test)
    test_acc = (label==y_test).mean()
    test_acc_all +=[test_acc]
    label_all +=[label]

sio.savemat(filename,{'test_acc_all':test_acc_all,'label_all':label_all})