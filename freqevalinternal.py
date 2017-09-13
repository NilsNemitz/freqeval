#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
internal storage objects for comb count
Created on 2017/09/08
@author: Nils Nemitz
"""

import numpy as np

class ADevData(object):
    """hold combined ADev data for transfer to plotting"""
    def __init__(self, number_of_channels):
        self._channels = number_of_channels # constant
        self._tau = [[] for i in range(number_of_channels)]
        self._dev = [[] for i in range(number_of_channels)]
        self._unc = [[] for i in range(number_of_channels)]
        # log10 values for plotting
        self._log_tau = [[] for i in range(number_of_channels)]
        self._log_dev = [[] for i in range(number_of_channels)]
        self._log_top = [[] for i in range(number_of_channels)]
        self._log_bot = [[] for i in range(number_of_channels)]
        
        # print("initializing new ADev object: ",number_of_channels," channels.")
        # print("tau array: ", self._tau)

    def channels(self):
        """ allow access to number of channels stored """
        return self._channels

    def tau(self, index):
        """ get tau values for selected channel """
        if index < 0 or index >= self._channels:
            return np.zeros(1)
        return self._tau[index]

    def dev(self, index):
        """ get ADev data for selected channel """
        if index < 0 or index >= self._channels:
            return np.zeros(1)
        return self._dev[index]

    def unc(self, index):
        """ get uncertainty data for selected channel """
        if index < 0 or index >= self._channels:
            return np.zeros(1)
        return self._unc[index]

    def log_values(self, index):
        """ get log10 of values for plotting """        
        return(self._log_tau[index], self._log_dev[index], self._log_top[index], self._log_bot[index])

    def add_data(self, index, tau, dev, unc):
        """ store state in object """
        if index < 0 or index >= self._channels:
            return -1
        # print("index: ", index)
        self._tau[index] = tau
        shape = tau.shape
        # print("tau shape: ", tau.shape)
        if shape == dev.shape:
            self._dev[index] = dev
        else:
            print("mismatched array shape for Allan deviation!")
            print("dev shape: ", dev.shape," != ", tau.shape)
            self._dev[index] = np.zeros_like(tau)
        if shape == unc.shape:
            self._unc[index] = unc
        else:
            print("mismatched array shape for uncertainty!")
            print("unc shape: ", unc.shape," != ", tau.shape)
            self._unc[index] = np.zeros_like(tau)
        # pre-calculate log10 values for logarithmic plotting
        self._log_tau[index] = np.log10(self._tau[index])
        # deal with zero errors from missing data
        bool_list = (self._dev[index] == 0)
        self._dev[index][bool_list] = 1E-19 
        self._log_dev[index] = np.log10(self._dev[index])
        # length of top error bar:
        self._log_top[index] = +( 
            np.log10(self._dev[index] + self._unc[index]) 
            - self._log_dev[index])
        # length of bottom error bar:
        self._log_bot[index] = -(
            np.log10(self._dev[index] - self._unc[index]) 
            - self._log_dev[index])
        return 0