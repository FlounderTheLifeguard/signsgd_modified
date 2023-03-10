'''
这个文件本来是要写100个client选择部分来做聚合的代码，但是遇到了两个问题所以先搁置了，
1.代码的问题在于，记录每轮本地梯度的list长度定死在100了，意味着每轮每个用户的本地参数都要有更新，但是事实上只有30个有更新
2.异步情况下似乎很不适合这种选择部分节点来更新的方案，这样的话每个client之间的模型差更远，但不知道影响大不大
因此暂时搁置这部分代码，先去调sgd的参数了
'''




import numpy as np
import random
import matplotlib.pyplot as plt
import time
import sys


import dirichlet_distribution as dd

import pickle

np.set_printoptions(threshold=sys.maxsize)

num_class = 10  # number of classes
num_feature = 28 * 28  # number of features
num_train = 60000  # number of train samples
num_test = 10000  # number of test samples
num_machines = 100  # number of workers
num_sampled_worker = 30  # sampled from all worker
class_per_worker = 2  # classes of worker
batch_size = 32

exit_byzantine = False

num_local_iter = 5
num_iter = 1000  # number of iteration
#alpha2 = 1.0



#num_local_iter = 1
Aggr = 'signsgd'
Rgl = 'regularization'
Sync = 'async'

num_byz = 4  # number of Byzantine workers


def cal_total_grad(X, Y, theta, weight_lambda):
    """
    :param X: shape(num_samples, features + 1)
    :param Y: labels' one_hot array, shape(num_samples, num_classes)
    :param theta: shape (num_classes, feature+1)
    :param weight_lambda: scalar
    :return: grad, shape(num_classes, feature+1)
    """
    m = X.shape[0]
    t = np.dot(theta, X.T)  # (num_classes, num_samples)
    t = t - np.max(t, axis=0)
    pro = np.exp(t) / np.sum(np.exp(t), axis=0)
    total_grad = -np.dot((Y.T - pro), X) / m  # + weight_lambda * theta
    return total_grad


def cal_loss(X, Y, theta, weight_lambda):
    m = X.shape[0]
    t1 = np.dot(theta, X.T)
    #print(type(theta))
    t1 = t1 - np.max(t1, axis=0)
    t = np.exp(t1)
    tmp = t / np.sum(t, axis=0)
    loss = -np.sum(Y.T * np.log(tmp)) // m + weight_lambda * np.sum(theta ** 2) // 2
    return loss


def cal_acc(test_x, test_y, theta):
    num = 0
    m = test_x.shape[0]
    for i in range(m):
        t1 = np.dot(theta, test_x[i])
        t1 = t1 - np.max(t1, axis=0)
        pro = np.exp(t1) / np.sum(np.exp(t1), axis=0)
        index = np.argmax(pro)
        if index == test_y[i]:
            num += 1
    acc = float(num) / m
    return acc


def cal_max_norm_grad(theta):
    if np.all(theta == 0):
        return theta
    tmp = np.abs(theta)
    re = np.where(tmp == np.max(tmp))
    row = re[0][0]
    col = re[1][0]
    max_val = tmp[row, col]
    tmp_theta = np.zeros_like(theta)
    n = len(re[0])
    theta[tmp != np.max(tmp)] = 0
    theta[theta == -max_val] = -1.0 / n
    theta[theta == max_val] = 1.0 / n
    return theta


def cal_var(theta):
    mean_theta = np.mean(theta, axis=0)
    mean_arr = np.tile(mean_theta, (theta.shape[0], 1))
    tmp = theta - mean_arr
    var = np.trace(np.dot(tmp, tmp.T))
    return var


def huber_loss_grad(e, d):
    t = (np.abs(e) <= d) * e
    e[np.abs(e) <= d] = 0
    grad = t + d * np.sign(e)
    return grad


class Machine:
    def __init__(self, data_x, data_y, machine_id):
        """Initializes the machine with the data
        Accepts data, a numpy array of shape :(num_samples/num_machines, dimension)
        data_x : a numpy array has shape :num_samples/num_machines, dimension)
        data_y: a list of length 'num_samples/num_machine', the label of the data_x"""

        self.data_x = data_x
        self.data_y = data_y
        self.machine_id = machine_id

    def attach_data(self, data_x, data_y, machine_id):
        self.data_x = np.concatenate((self.data_x, data_x),axis=0)
        self.data_y = np.concatenate((self.data_y, data_y),axis=0)

    def update(self, theta0, theta0_last, theta, alpha, l1_lambda, weight_lambda, delta):
        """Calculates gradient with a randomly selected sample, given the current theta
         Accepts theta, a np array with shape of (dimension,)
         Returns the calculated gradient"""
        m = self.data_x.shape[0]
        id = random.randint(0, m - batch_size)

        # grad_f = cal_total_grad(self.data_x[id:(id + batch_size)], self.data_y[id:(id + batch_size)], theta0,
        #                        weight_lambda)
        #原始loss的梯度
        if Sync == 'sync':
            grad_f = cal_total_grad(self.data_x[id:(id + batch_size)], self.data_y[id:(id + batch_size)], theta0,
                                weight_lambda)
            g_norm = l1_lambda * np.sign(theta0 - theta0_last)
        if Sync == 'async':
            grad_f = cal_total_grad(self.data_x[id:(id + batch_size)], self.data_y[id:(id + batch_size)], theta,
                                    weight_lambda)
            g_norm = l1_lambda * np.sign(theta - theta0)
        # L1 norm的梯度

        ##去正则项，且改为从theta0更新
        #grad = grad_f / num_machines + l1_lambda * np.sign(theta - theta0)
        if Rgl == 'regularization':
            grad = grad_f + g_norm #+ l1_lambda * np.sign(theta - theta0)
        if Rgl == 'non-regularization':
            grad = grad_f
        # 改为从theta0更新
        if Sync == 'sync':
            new_theta = theta0 - alpha * grad
        if Sync == 'async':
            new_theta = theta - alpha * grad

        #return new_theta
        return new_theta

#client_idcs = [[] for _ in range(num_machines)]

class Parameter_server:
    def __init__(self):
        fen = num_machines * class_per_worker // 10
        """Initializes all machines"""
        self.theta0_li = []
        self.theta_li = []   # list that stores each theta, grows by one iteration
        #self.acc_li = []
        self.grad_li = []
        self.grad_norm = []
        self.theta0_star_norm = []
        self.acc_li = []
        self.loss_li = []
        self.theta_li_diff = []
        self.theta0_li_diff = []
        self.time_li = []
        self.var_li = []

        train_img = np.load('../data/mnist/train_img.npy')  # shape(60000, 784)
        train_lbl = np.load('../data/mnist/train_lbl.npy')  # shape(60000,)
        one_train_lbl = np.load('../data/mnist/one_train_lbl.npy')  # shape(60000, 10)
        test_img = np.load('../data/mnist/test_img.npy')  # shape(10000, 784)
        test_lbl = np.load('../data/mnist/test_lbl.npy')  # shape(10000,)

        bias_train = np.ones(num_train)
        train_img_bias = np.column_stack((train_img, bias_train))

        bias_test = np.ones(num_test)
        test_img_bias = np.column_stack((test_img, bias_test))

        self.test_img_bias = test_img_bias
        self.test_lbl = test_lbl
        self.train_img_bias = train_img_bias
        self.one_train_lbl = one_train_lbl
        self.train_lbl = train_lbl

        #samples_per_machine = num_train // num_machines
        self.machines = []



        #for i in range(num_machines):
           # new_machine = Machine(train_img_bias[i * samples_per_machine:(i + 1) * samples_per_machine, :],
                      #            one_train_lbl[i * samples_per_machine:(i + 1) * samples_per_machine, :], i)
         #   self.machines.append(new_machine)

        '''
        client_idcs = dd.dirichlet_split_noniid(train_lbl, 1.0, num_machines)
        print(client_idcs)
        '''

        ##############   every 2 machine share the same digit image (non i.i.d. case)
        machine_data_li = []
        machine_label_li = []
        for i in range(num_machines):
            machine_data_li.append([])
            machine_label_li.append([])
        for i in range(num_class):
            s1 = '../data/mnist/2/train_img' + str(i) + '.npy'
            s2 = '../data/mnist/2/one_train_lbl' + str(i) + '.npy'
            train = np.load(s1)
            label = np.load(s2)
            size = train.shape[0]

            #client_idcs = dd.dirichlet_split_noniid(label, 1.0, num_machines)
            ## num1 = size/2
            '''the number of samples of class i  per machine'''
            num1 = size // fen

            tmp_bias = np.ones(size)
            train_bias = np.column_stack((train, tmp_bias))
            for j in range(fen):
                machine_data_li[(i * fen + j) % num_machines].append(train_bias[j * num1 : (j + 1) * num1, :])
                machine_label_li[(i * fen + j) % num_machines].append(label[0 + j * num1 : (j + 1) * num1, :])
                # print("j:",j)
                # print(fen*i+j)
        #machine_data_array = np.array(machine_data_li)
        # print(len(machine_data_li))
        #print(len(machine_data_li[i]))
        #machine_label_array = np.array(machine_label_li)
        for i in range(len(machine_data_li)):
            machine_data_i = machine_data_li[i]
            machine_label_i = machine_label_li[i]
            machine = Machine(machine_data_i[0], machine_label_i[0], i)
            #data_array = np.concatenate((machine_data_i[0], machine_data_i[1]), axis=0)
            for j in range(1,class_per_worker):
                machine.attach_data(machine_data_i[j], machine_label_i[j], i)
            #print(machine.data_x.shape)
            self.machines.append(machine)



    def broadcast(self, theta0, theta0_last, theta_li, alpha, l1_lambda, weight_lambda, delta, machines_sampled):
    #def broadcast(self, theta0, theta_li, alpha, l1_lambda, weight_lambda, delta):
        """Broadcast theta
        Accepts theta, a numpy array of shape:(dimension,)
        Return a list of length 'num_machines' containing the updated theta of each machine"""

        new_theta_li = []
        grad_li = []

        #print(len(theta_li))
        #random.seed(10)
        #slice = random.samplsamplese(self.machines, 50)

        #print(type(machines_sampled))
        for i,k in zip(machines_sampled, range(num_sampled_worker)):
            #print(i)
            #print(ind)

            new_theta = theta_li[k]


            for j in range(num_local_iter):
                #print(j)

                #new_theta_li.append(mac.update(theta0, theta_li[i], alpha, l1_lambda, weight_lambda, delta))
                #asyc
                new_theta = self.machines[i].update(theta0, theta0_last, new_theta , alpha, l1_lambda, weight_lambda, delta)

                #print(type(new_theta))

                #new_theta_li.append(mac.update(theta0, theta0_last, theta_li[i], alpha, l1_lambda, weight_lambda, delta))
            new_theta_li[k].append(new_theta)

            #grad_li.append(mac.update(theta0, theta0_last, theta_li[i], alpha, l1_lambda, weight_lambda, delta))
            #new_theta_li.append(theta0 - alpha * grad_li[i])
        tmp = np.zeros_like(theta0)
        print(len(new_theta_li))

        #print("length of theta_li:", len(theta_li))
        #print("length of new_theta_li:", len(new_theta_li))
        for i in range(num_sampled_worker):
            #print(len(theta_li))
            #print(len(new_theta_li))
            # L1 norm
            if exit_byzantine == False:
                if Aggr == 'signsgd':
                    tmp += np.sign(theta0 - new_theta_li[i])
                if Aggr == 'sgd':
                    tmp += theta0 - new_theta_li[i]



                #new_theta_li.append(theta0 - alpha * grad_li[i])
            else:
                if i < num_machines - num_byz:
                    #tmp += np.sign(theta0 - new_theta_li[i])
                    tmp += grad_li[i]
                else:
                    #tmp += np.sign(theta0 + new_theta_li[i])  # transmit attack
                    tmp += grad_li[0]
                    # tmp += np.sign(theta0 - new_theta_li[0]) # transmit attack
                    print("byz")
                #new_theta_li.append(theta0 - alpha * grad_li[i])

        #tmp = tmp // 20
        #new_theta0 = theta0 - alpha * (l1_lambda * tmp + weight_lambda * theta0)
        if Aggr == 'signsgd':
            new_theta0 = theta0 - alpha * (tmp  + weight_lambda * theta0)
        if Aggr == 'sgd':
            new_theta0 = theta0 - (tmp - weight_lambda * theta0 * alpha)
        #new_theta0 = theta0 - tmp * l1_lambda * alpha - weight_lambda * theta0 * alpha
        #new_theta0 = theta0 - tmp + weight_lambda * theta0 * alpha
        # qx 改的，传上来聚合的梯度取方向
        # new_theta0 = theta0 - alpha * (l1_lambda * np.sign(tmp) + weight_lambda * theta0)
        return new_theta0, new_theta_li
        #return new_theta0

    def train(self, init_theta0, init_theta, alpha, l1_lambda, weight_lambda):
        """Peforms num_iter rounds of update, appends each new theta to theta_li
        Accepts the initialed theta, a numpy array has shape:(dimension,)"""


        self.theta0_li.append(0.0)
        self.theta0_li.append(init_theta0)
        #self.theta_li
        self.theta_li.append(init_theta)

        k = 0
        delta = 0.1
        d = 0.0005
        start = time.perf_counter()
        for i in range(num_iter):
            alpha = d / np.sqrt(i + 1) * 0.05
            machines_sampled = random.sample(range(num_machines), num_sampled_worker)

            sampled_li = []
            print("",len(self.theta_li))

            for k in machines_sampled:
                tmp= self.theta_li[i][k]
                sampled_li.append(tmp)

            rec_theta0, rec_theta = self.broadcast(self.theta0_li[-1], self.theta0_li[-2], sampled_li, alpha, l1_lambda,
                                                   weight_lambda, delta, machines_sampled)
            #rec_theta0, rec_theta = self.broadcast(self.theta0_li[-1], self.theta_li[-1], alpha, l1_lambda, weight_lambda, delta)

            for k, j in zip(machines_sampled,range(num_sampled_worker)):
                self.theta_li[k].append(rec_theta[j])

            # if (i + 1) % 1000 == 0:
            #     self.theta_li = []
            #     self.theta0_li = []
            self.theta0_li.append(rec_theta0)
            self.theta_li.append(rec_theta)

            # total_grad = cal_total_grad(self.train_img_bias, self.one_train_lbl, rec_theta0, weight_lambda) + weight_lambda * rec_theta0
            # # total_grad = cal_total_grad(self.train_img_bias, self.one_train_lbl, rec_theta[0][0],weight_lambda) + weight_lambda * rec_theta[0][0]
            # self.grad_norm.append(np.linalg.norm(total_grad))
            if (i + 1) % 10 == 0:
                iter_time = time.perf_counter()
                self.time_li.append(iter_time - start)
                acc = cal_acc(self.test_img_bias, self.test_lbl, rec_theta0)
                self.acc_li.append(acc)
                if Rgl == 'non-regularization':
                    loss = cal_loss(self.test_img_bias, self.test_lbl, rec_theta0, weight_lambda)
                if (Rgl == 'regularization') & (Sync == 'sync'):
                    loss = cal_loss(self.test_img_bias, self.test_lbl, rec_theta0, weight_lambda) + l1_lambda * np.sum(
                        np.maximum(self.theta0_li[-1]-self.theta0_li[-2], self.theta0_li[-2]-self.theta0_li[-1]))
                if (Rgl == 'regularization')& (Sync == 'async'):
                    loss = cal_loss(self.test_img_bias, self.test_lbl, rec_theta0, weight_lambda)
                self.loss_li.append(loss)

                print("step:", i, " acc:", acc, "loss:", loss)

            theta_tmp = []
            for k in range(num_sampled_worker):
                print(k)
                theta_tmp.append(rec_theta[k])
            # theta_tmp = np.array(rec_theta)
            print(len(rec_theta))
            theta_tmp = theta_tmp.reshape(num_sampled_worker, 10 * 785)
            rec_theta0 = rec_theta0.reshape(1, 10 * 785)
            var_theta = np.row_stack((theta_tmp, rec_theta0))
            self.var_li.append(cal_var(var_theta))

        print("train end!")

    def plot_curve(self):
        """plot the loss curve and the acc curve
        save the learned theta to a numpy array and a txt file"""

        # s1 = 'L2/gaussian/q8'
        # np.save('./result/RSGD/fault/' + s1 + '/acc.npy', self.acc_li)
        # # np.save('./result/RSGD/no_fault/same_digit/' + s1 + '/grad_norm.npy', self.grad_norm)
        # np.save('./result/RSGD/fault/' + s1 + '/var_li.npy', self.var_li)

        #plt.subplot(1, 2, 1)
        plt.plot(np.arange(len(self.acc_li)) * 10 * num_local_iter, self.acc_li)
        plt.xlim((0, 5000))
        plt.ylim = ((0, 1))
        plt.xlabel('iter')
        plt.ylabel('accuracy')
        plt.title(Aggr +","+ Rgl +"," + Sync + ","+ str(num_local_iter))

        sss = Aggr + "," + Rgl + "," + Sync + "," + str(num_local_iter)+"users"+str(num_sampled_worker)
        f = open('D:/OneDrive/桌面/实验/code/RSA-Byzantine-master/RSA-code/result2/' + sss,'wb')
        pickle.dump([self.acc_li,
                     self.loss_li,
                     self.var_li],f)
        f.close()

        # plt.savefig('./result/RSGD/fault/' + s1 + '/acc.png')
        plt.savefig('D:/OneDrive/桌面/实验/code/RSA-Byzantine-master/RSA-code/result2/acc/' + sss + ',acc.png')

        plt.show()


        #plt.subplot(1, 2, 2)
        plt.plot(np.arange(len(self.loss_li)) * 10, self.loss_li)
        plt.xlabel('iter')
        plt.ylabel('loss')
        plt.title(Aggr + "," + Rgl + "," + Sync + "," + str(num_local_iter))
        plt.savefig('D:/OneDrive/桌面/实验/code/RSA-Byzantine-master/RSA-code/result2/loss/' + sss + ',loss.png')



        plt.show()

        # plt.semilogy(np.arange(num_iter), self.grad_norm)
        # plt.xlabel('iter')
        # plt.ylabel('log||grad||')
        # # plt.title(s1)
        # plt.savefig('./result/RSGD/no_fault/same_digit/' + s1 + '/grad_norm.png')
        # plt.show()
        #plt.subplot(1, 2, 2)
        plt.semilogy(np.arange(num_iter), self.var_li)
        plt.xlabel('iter')
        plt.ylabel('log||var||')
        # plt.savefig('./result/RSGD/fault/' + s1 + '/var.png')
        plt.show()


def init():
    server = Parameter_server()
    return server


def main():
    server = init()
    init_theta0 = np.zeros((num_class, num_feature + 1))
    init_theta = []
    for i in range(num_machines):
        init_theta.append(np.zeros((num_class, num_feature + 1)))
    print("initial theta:",len(init_theta))
    alpha = 0.001 * 0.0
    # l1_lambda = 0.5
    # qx 改的，为了测试正则项的作用
    l1_lambda = 10
    weight_lambda = 0.0
    #weight_lambda = 0.01
    server.train(init_theta0, init_theta, alpha, l1_lambda, weight_lambda)
    server.plot_curve()


if __name__ == "__main__":
    main()