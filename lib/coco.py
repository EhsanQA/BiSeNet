#!/usr/bin/python
# -*- encoding: utf-8 -*-

import os
import os.path as osp
import json

import torch
from torch.utils.data import Dataset, DataLoader
import torch.distributed as dist
import cv2
import numpy as np

import lib.transform_cv2 as T
from lib.sampler import RepeatedDistSampler
from lib.base_dataset import BaseDataset, TransformationTrain, TransformationVal

'''
91 + 91 = 182 classes, label proportions are:
    [0.0901445377, 0.00157896236, 0.00611962763, 0.00494526505, 0.00335260064, 0.00765355955, 0.00772972804, 0.00631509744,
     0.00270457286, 0.000697793344, 0.00114085574, 0.0, 0.00114084131, 0.000705729068, 0.00359758029, 0.00162208938, 0.00598373796,
     0.00440213609, 0.00362085441, 0.00193052224, 0.00271001196, 0.00492864603, 0.00186985393, 0.00332902228, 0.00334420294, 0.0,
     0.000922751106, 0.00298028204, 0.0, 0.0, 0.0010437561, 0.000285608411, 0.00318569535, 0.000314216755, 0.000313060076, 0.000364755975,
     0.000135920434, 0.000678980469, 0.000145436185, 0.000187677684, 0.000640885889, 0.00121345742, 0.000586313048, 0.00160106929, 0.0,
     0.000887093272, 0.00252332669, 0.000283407598, 0.000423017189, 0.000247005886, 0.00607086751, 0.002264644, 0.00108296684, 0.00299262899,
     0.0013542901, 0.0018255991, 0.000719220519, 0.00127748254, 0.00743539745, 0.0018222117, 0.00368625641, 0.00644224839, 0.00576837542,
     0.00234158491, 0.0102560197, 0.0, 0.0310601945, 0.0, 0.0, 0.00321417022, 0.0, 0.00343909654, 0.00366968441, 0.000223077284,
     0.000549851977, 0.00142833996, 0.000976368198, 0.000932849475, 0.00367802183, 6.33631941e-05, 0.00179415878, 0.00384408865, 0.0,
     0.00178728429, 0.00131955324, 0.00172710316, 0.000355333114, 0.00323052075, 3.45024606e-05, 0.000159319051, 0.0, 0.00233498927,
     0.00115535012, 0.00216354199, 0.00122636929, 0.0297802789, 0.00599919161, 0.00792527951, 0.00446247753, 0.00229155615,
     0.00481623284, 0.00928416394, 0.000292110971, 0.00100709844, 0.0036950065, 0.0238653594, 0.00318962423, 0.000957967243, 0.00491549702,
     0.00305316147, 0.0142686986, 0.00667806178, 0.00940045853, 0.000994700392, 0.00697502858, 0.00163056828, 0.00655119369, 0.00599044442,
     0.00200317424, 0.00546109479, 0.00496814246, 0.00128356119, 0.00893122042, 0.0423373213, 0.00275267517, 0.00730936505, 0.00231434982,
     0.00435102045, 0.00276966794, 0.00141028174, 0.000251683147, 0.00878006131, 0.00357672108, 0.000183633027, 0.00514584856,
     0.000848967739, 0.000662099529, 0.00186883821, 0.00417270686, 0.0224302911, 0.000551947753, 0.00799009014, 0.00379765772,
     0.00226731642, 0.0181341982, 0.000835227067, 0.00287355753, 0.00546769461, 0.0242787139, 0.00318951861, 0.00147349686,
     0.00167046288, 0.000520877717, 0.0101631583, 0.0234788756, 0.00283978366, 0.0624405778, 0.00258472693, 0.0204314774, 0.000550128266,
     0.00112924659, 0.001457768, 0.00190406757, 0.00173232644, 0.0116980759, 0.000850599027, 0.00565381261, 0.000787379463, 0.0577763754,
     0.00214883711, 0.00553984356, 0.0443605019, 0.0218570174, 0.0027310644, 0.00225446528, 0.00903008323, 0.00644298871, 0.00442167269,
     0.000129279566, 0.00176047379, 0.0101637834, 0.00255549522]
11 classes has no annos, proportions are 0
'''



class CocoStuff(BaseDataset):

    def __init__(self, dataroot, annpath, trans_func=None, mode='train'):
        super(CocoStuff, self).__init__(dataroot, annpath, trans_func, mode)
        self.n_cats = 182 # 91 stuff, 91 thing, 11 of thing have no annos
        self.lb_ignore = 255
        self.lb_map = None

        self.to_tensor = T.ToTensor(
            mean=(0.46962251, 0.4464104,  0.40718787), # coco, rgb
            std=(0.27469736, 0.27012361, 0.28515933),
        )


