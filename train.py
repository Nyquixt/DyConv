import torch
import torchvision
import torchvision.transforms as transforms
import torch.nn as nn

import numpy as np
import matplotlib.pyplot as plt
import argparse
import time
from datetime import timedelta

from config import *
from utils import calculate_acc, get_network, get_dataloader, init_params, count_parameters, save_plot

parser = argparse.ArgumentParser(description='Training CNN models')

parser.add_argument('--network', '-n', required=True)
parser.add_argument('--epoch', '-e', type=int, default=90, help='Number of epochs')
parser.add_argument('--batch', '-b', type=int, default=128, help='The batch size')
parser.add_argument('--lr', '-l', type=float, default=0.01, help='Learning rate')
parser.add_argument('--momentum', '-m', type=float, default=0.9, help='Momentum for SGD')
parser.add_argument('--weight-decay', '-d', type=float, default=0.0005, help='Weight decay for SGD optimizer')
parser.add_argument('--step-size', '-s', type=int, default=30, help='Step in learning rate scheduler')
parser.add_argument('--gamma', '-g', type=float, default=0.1, help='Gamma in learning rate scheduler')
parser.add_argument('--dataset', type=str, help='cifar100 or imagenet', default='cifar100')
parser.add_argument('--save', action='store_true')
parser.add_argument('--cuda', action='store_true')
parser.add_argument('--ngpu', type=int, default=1)

args = parser.parse_args()
print(args)

TIME_STAMP = int(round(time.time() * 1000))
LOG_FILE = 'logs/{}-{}-b{}-e{}-{}.txt'.format(args.network, args.dataset, args.batch, args.epoch, TIME_STAMP)

# Dict to keep the final result
stats = {
    'best_acc': 0.0,
    'best_epoch': 0
}

# Device
device = torch.device('cuda' if (torch.cuda.is_available() and args.cuda) else 'cpu')

# Dataloader
trainloader, testloader = get_dataloader(args.dataset, args.batch)

# Define losses lists to plot
train_losses = []
val_losses = []
train_accuracy = []
val_accuracy = []

# Define model
if args.dataset == 'cifar100':
    VAL_LEN = 10000
elif args.dataset == 'imagenet':
    VAL_LEN = 150000

# Get network
net = get_network(args.network, args.dataset, device)

# Handle multi-gpu
if args.cuda and args.ngpu > 1:
    net = nn.DataParallel(net, list(range(args.ngpu)))

# Init parameters
init_params(net)

print('Training {} with {} parameters...'.format(args.network, count_parameters(net)))

net.train()

# Loss and optimizer
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.SGD(net.parameters(), lr=args.lr, momentum=args.momentum, weight_decay=args.weight_decay)

# Learning rate scheduler
scheduler = torch.optim.lr_scheduler.StepLR(optimizer=optimizer, step_size=args.step_size, gamma=args.gamma)

# Log basic hyper-params to log file
with open(LOG_FILE, 'w') as f:
    f.write('Training model {}\n'.format(args.network))
    f.write('Hyper-parameters:\n')
    f.write('Epoch {}; Batch {}; LR {}; SGD Momentum {}; SGD Weight Decay {};\n'.format(str(args.epoch), str(args.batch), str(args.lr), str(args.momentum), str(args.weight_decay)))
    f.write('LR Scheduler Step {}; LR Scheduler Gamma {}; {};\n'.format(str(args.step_size), str(args.gamma), str(args.dataset)))
    f.write('TrainLoss,TrainAcc,ValLoss,ValAcc\n')

# Train the model
start = time.time()
for epoch in range(args.epoch):  # loop over the dataset multiple times

    training_loss = 0.0
    for i, data in enumerate(trainloader):
        # Get the inputs; data is a list of [inputs, labels]
        inputs, labels = data
        inputs = inputs.to(device)
        labels = labels.to(device)
        
        # Zero the parameter gradients
        optimizer.zero_grad()

        # Forward + backward + optimize
        outputs = net(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        training_loss += loss.item()

    # Print statistics
    with torch.no_grad():
        validation_loss = 0.0
        for j, data in enumerate(testloader): # (10,000 / args.batch) batches
            inputs, labels = data
            inputs = inputs.to(device)
            labels = labels.to(device)

            outputs = net(inputs)
            loss = criterion(outputs, labels)
            
            validation_loss += loss.item()
    
    train_losses.append(training_loss / len(trainloader))
    val_losses.append(validation_loss / len(testloader))

    # Calculate training accuracy, top-1
    train_acc = calculate_acc(trainloader, net, device)

    # Calculate validation accuracy
    net.eval()
    val_acc = calculate_acc(testloader, net, device)
    if val_acc > stats['best_acc']:
        stats['best_acc'] = val_acc
        stats['best_epoch'] = epoch + 1
        if args.save:
            # Save the model
            torch.save(net.state_dict(), 'trained_nets/{}-{}-b{}-e{}-{}.pth'.format(args.network, args.dataset, args.batch, args.epoch, TIME_STAMP))
        
    # Switch back to training mode
    net.train()

    train_accuracy.append(train_acc)
    val_accuracy.append(val_acc)

    print('[Epoch: %d] Train Loss: %.3f    Train Acc: %.3f%%    Val Loss: %.3f    Val Acc: %.3f%%' %
            ( epoch + 1, training_loss / len(trainloader), train_acc, validation_loss / len(testloader), val_acc ))
    
    with open(LOG_FILE, 'a+') as f:
        f.write('%d,%.3f,%.3f,%.3f,%.3f\n' % (epoch + 1, training_loss / len(trainloader), train_acc, validation_loss / len(testloader), val_acc))

    # Step the scheduler after every epoch
    scheduler.step()

end = time.time()
print('Total time trained: {}'.format( str(timedelta(seconds=int(end - start)) ) ))

# Test the model
net.eval()
val_acc = calculate_acc(testloader, net, device)
print('Test Accuracy of the network on the {} test images: Epoch {}, {} % '.format(VAL_LEN, stats['best_epoch'], stats['best_acc']))
with open(LOG_FILE, 'a+') as f:
    f.write('Test Accuracy of the network on the {} test images: Epoch {}, {} %'.format(VAL_LEN, stats['best_epoch'], stats['best_acc']))

if args.save:
    # Save plot
    save_plot(train_losses, train_accuracy, val_losses, val_accuracy, args, TIME_STAMP)