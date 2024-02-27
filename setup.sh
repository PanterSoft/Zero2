#!/bin/bash

#sudo apt-get -y install libbluetooth-dev pkg-config libglib2.0-dev libboost-python-dev libboost-thread-dev build-essential python3-dev
# Install Bluetooth for SSH
cd dependencies/pybluez
#python3 setup.py install
pip3 install -e .[ble]
