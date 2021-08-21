import pandas as pd
import numpy as np
import torch 
import torch.nn as nn
from torch.utils.data import DataLoader
from matplotlib import pyplot as plt
import random
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

#list of possible values
bottleneck = 204    #(397, 204, 407)
lr = 0.1            #(0.001, 0.5, 0.1)
m=0.6               #(0.2, 0.6)
r=0.9               #(0.1, 0.5, 0.9)

#create one hot vector from label values
def batch2onehots(labels):
    one_hot = torch.zeros(labels.size()[0], 10)
    for i in range(len(labels)):
        num = labels[i]
        one_hot[i,int(num.detach().cpu().numpy())] = 1
        
    return one_hot

#cross validation
def n_fold(data,labels,n):
    data_len = len(data)
    eval_len = data_len / 5  #the 1/5 is to eval in cv
    eval_len = int(eval_len)
    eval_data = data[n*eval_len: (n+1) * eval_len, :]
    eval_labels = labels[n*eval_len: (n+1) * eval_len]
    #pairnw gia train o,ti yparxei prin kai meta to eval - 4/5
    train_data = np.concatenate((data[(n-1)*eval_len: n*eval_len, :], data[(n+1)*eval_len:,:]),axis=0) 
    train_labels = np.concatenate((labels[(n-1)*eval_len: n*eval_len] ,labels[(n+1)*eval_len:]),axis=0)
    
    return eval_data, eval_labels, train_data, train_labels    

#arxitektonikh nn
class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.fc1 = nn.Linear(784, 397)                  #input
        self.fc2 = nn.Linear(397, bottleneck)
        self.fc3 = nn.Linear(bottleneck, 10)
        #eisodos
        self.relu = nn.LeakyReLU(0.2)                   #hidden layer activation function
        self.softmax = nn.Softmax(dim=1)                #output layer activation function
        
    def forward(self, input):
        x = self.relu(self.fc1(input))                  # hidden layer
        x = self.relu(self.fc2(x))                      # hidden layer
        return self.softmax(self.fc3(x))                # output layer


#create custom dataset function for dataloader
class myDataset(torch.utils.data.Dataset):
    def __init__(self, data, labels):
        self.data = data
        self.labels = labels
    def __len__(self):
        return len(self.data)
    def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()
        data = self.data[idx]        
        labels = self.labels[idx]
        sample = {'data' : data, 'labels' : labels}
        return sample

#read dataset
train = pd.read_csv('./mnist_train.csv')
test = pd.read_csv('./mnist_test.csv')

#from pandas to numpy
x = train.to_numpy()

#separate labels from data
labels = x[:,0]
data = x[:,1:]

#normalization [0, 1]
data = data/255


fold_avg_accuracy = 0  
fold_avg_loss = 0

for fold in range(5):
    print("Fold:",fold)
    train_fold_plot = []
    eval_fold_plot = []
    plt.figure()
    eval_data, eval_labels, train_data, train_labels = n_fold(data, labels, fold) 
    eval_dataset = myDataset(eval_data, eval_labels)
    train_dataset = myDataset(train_data, train_labels)
    
    eval_dataloader = DataLoader(eval_dataset, batch_size=64, num_workers= 2)
    train_dataloader = DataLoader(train_dataset, batch_size=64, num_workers= 2)

    net = Net().double().to(device)
    optimizer = torch.optim.SGD(net.parameters(),lr = lr, momentum = m, weight_decay = r)

    loss_function1 = nn.MSELoss()

    for epoch in range(20):
        epoch_loss = 0
        for j, data1 in enumerate(train_dataloader):
            dedomena = data1['data'].double().to(device)
            etiketes = data1['labels'].double().to(device)
            
            goal = batch2onehots(etiketes).double().to(device)
            output = net(dedomena)
            

            loss_mse = loss_function1(output,goal)
            batch_ce = torch.sum(goal*torch.log(output),dim=1)
            loss_ce = -torch.mean(batch_ce)
            
            #choose loss function (cross entropy better for classification)
            #epoch_loss += loss_ce.item()
            epoch_loss += loss_mse.item()
            loss_mse.backward()
            
            optimizer.step()
            net.zero_grad()
            
        correct = 0
        total = 0
        
        #eval
        with torch.no_grad():
            eval_loss = 0
            for eval_ind, data1 in enumerate(eval_dataloader):
                dedomena = data1['data'].double().to(device)
                etiketes = data1['labels'].double().to(device)
                goal = batch2onehots(etiketes).double().to(device)
                output = net(dedomena)

                loss_mse = loss_function1(output,goal)
                batch_ce = torch.sum(goal*torch.log(output),dim=1)
                loss_ce = -torch.mean(batch_ce)
                
                #same loss function as train
                #eval_loss += loss_ce.item()
                eval_loss += loss_mse.item()                

                #calculate eval accuracy
                for idx, i in enumerate(output):
                   
                    if torch.argmax(i) == etiketes[idx]:
                        correct += 1
                    total += 1
                    
        avg_epochLoss =  epoch_loss/len(train_dataloader)
        avg_evalLoss = eval_loss/len(eval_dataloader)
        train_fold_plot.append(avg_epochLoss)       
        eval_fold_plot.append(avg_evalLoss)       
        print('epoch: %d Train loss = %.4f, Eval loss = %.4f, Eval accuracy = %.3f' % (epoch, avg_epochLoss, avg_evalLoss, (correct/total)))
        plt.plot(train_fold_plot)
        plt.plot(eval_fold_plot)
        plt.title('Fold:'+str(fold))
        plt.legend(['Test Loss','Train Loss'])
    
    fold_avg_accuracy+=(correct/total)
    fold_avg_loss += avg_evalLoss
fold_avg_accuracy = fold_avg_accuracy/5            
fold_avg_loss = fold_avg_loss/5  
