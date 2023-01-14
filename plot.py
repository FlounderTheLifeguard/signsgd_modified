import pickle
import matplotlib.pyplot as plt
import numpy as np



#num_local_iter = 10
Aggr1 = 'signsgdforreal'
Rgl1 = 'regularization'
Sync1 = 'sync'
num_local_iter1 = 5
num_iter1 = 1000   # number of iteration


sss1 = Aggr1 + "," + Rgl1 + "," + Sync1 + "," + str(num_local_iter1) + ",调参"
f1 = open('D:/OneDrive/桌面/实验/code/RSA-Byzantine-master/RSA-code/result2/noniid-2-regularization/' + sss1, 'rb')
res1 = pickle.load(f1)


#num_local_iter = 5
Aggr2 = 'signsgdforreal'
Rgl2 = 'regularization'
Sync2 = 'async'
num_local_iter2 = 5
num_iter2 = 1000   # number of iteration

sss2 = Aggr2 + "," + Rgl2 + "," + Sync2 + "," + str(num_local_iter2) + ",调参"
f2 = open('D:/OneDrive/桌面/实验/code/RSA-Byzantine-master/RSA-code/result2/noniid-2-regularization/' + sss2, 'rb')
res2 = pickle.load(f2)



#num_local_iter = 5
Aggr6 = 'signsgdforreal'
Rgl6 = 'regularization'
Sync6 = 'async'
num_local_iter6 = 5
num_iter6 = 1000   # number of iteration

sss6 = Aggr6 + "," + Rgl6 + "," + Sync6 + "," + str(num_local_iter6) + ",调参"
f6 = open('D:/OneDrive/桌面/实验/code/RSA-Byzantine-master/RSA-code/result2/noniid-5/' + sss6, 'rb')
res6 = pickle.load(f6)



#num_local_iter = 1
Aggr3 = 'signsgd'
Rgl3 = 'regularization'
Sync3 = 'sync'
num_local_iter3 = 5
num_iter3 = 1000   # number of iteration

sss3 = Aggr3 + "," + Rgl3 + "," + Sync3 + "," + str(num_local_iter3) + ",调参"
f3 = open('D:/OneDrive/桌面/实验/code/RSA-Byzantine-master/RSA-code/result2/noniid-2-regularization/' + sss3, 'rb')
res3 = pickle.load(f3)



#num_local_iter = 1
Aggr4 = 'signsgd'
Rgl4 = 'regularization'
Sync4 = 'async'
num_local_iter4 = 5
num_iter4 = 1000   # number of iteration

sss4 = Aggr4 + "," + Rgl4 + "," + Sync4 + "," + str(num_local_iter4) + ",调参"
f4 = open('D:/OneDrive/桌面/实验/code/RSA-Byzantine-master/RSA-code/result2/noniid-2-regularization/' + sss4, 'rb')
res4 = pickle.load(f4)



#num_local_iter = 1
Aggr5 = 'signsgd'
Rgl5 = 'regularization'
Sync5 = 'async'
num_local_iter5 = 5
num_iter5 = 1000   # number of iteration

sss5 = Aggr5 + "," + Rgl5 + "," + Sync5 + "," + str(num_local_iter5)+",调参"
f5 = open('D:/OneDrive/桌面/实验/code/RSA-Byzantine-master/RSA-code/result2/noniid-5/' + sss5, 'rb')

res5 = pickle.load(f5)



def fig():





    plt.plot(np.arange(len(res1[0]) )* 10 * num_local_iter1, res1[0],'r')
   # #plt.legend(('10','5',))
    plt.plot(np.arange(len(res2[0])) * 10 * num_local_iter2, res2[0], 'b')
    plt.plot(np.arange(len(res6[0])) * 10 * num_local_iter6, res6[0], 'g')


    plt.plot(np.arange(len(res3[0])) * 10 * num_local_iter3, res3[0], 'r+')


    plt.plot(np.arange(len(res4[0])) * 10 * num_local_iter4, res4[0], 'b+')
    plt.plot(np.arange(len(res5[0])) * 10 * num_local_iter5, res5[0], 'g+')



    #plt.legend((sss1+',sgd',sss2+',sgd+regularization',sss6,sss3+',rsa',sss4+',signsgd',sss5))
    plt.legend((sss1, sss2, sss6+'baseline', sss3 , sss4 , sss5+'baseline'))
    #plt.legend(('signsgd_vote', 'signsgd', 'sgd', 'signsgd_vote', 'signsgd', 'sgd',))

    plt.plot(np.arange(len(res5[0])) * 10 * num_local_iter5, res5[0], 'g')
    plt.plot(np.arange(len(res3[0])) * 10 * num_local_iter3, res3[0], 'r')
    #plt.plot(np.arange(len(res4[0])) * 10 * num_local_iter3, res3[0], 'r')

    plt.xlim((0, 5000))
    plt.ylim = ((0, 1))
    plt.xlabel('iter')
    plt.ylabel('accuracy')
    #plt.title(Aggr + "," + Rgl + "," + Sync + "," + str(num_local_iter))
    plt.title("signsgd + / signsgd_votes -")
    plt.savefig('D:/OneDrive/桌面/实验/code/RSA-Byzantine-master/RSA-code/result2/signsgd与假signsgd.png')
    plt.show()

fig()