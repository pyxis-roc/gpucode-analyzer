#!/usr/bin/env python3

from ctypes import *

_cudaocc = cdll.LoadLibrary("cudaocc.so")

class cudaOccDeviceProp(Structure):
    _fields_ = [("computeMajor", c_int),
                ("computeMinor", c_int),
                ("maxThreadsPerBlock", c_int),
                ("maxThreadsPerMultiprocessor", c_int),
                ("regsPerBlock", c_int),
                ("regsPerMultiprocessor", c_int),
                ("warpSize", c_int),
                ("sharedMemPerBlock", c_size_t),
                ("sharedMemPerMultiprocessor", c_size_t),
                ("numSms", c_int),
                ("sharedMemPerBlockOptin", c_size_t),
                ("reservedSharedMemPerBlock", c_size_t)
                ]

_cudaocc.myOccSMemAllocationGranularity.argtypes = [POINTER(c_int),
                                                      POINTER(cudaOccDeviceProp)]

CUDA_OCC_SUCCESS = 0
CUDA_OCC_ERROR_INVALID_INPUT = 1
CUDA_OCC_ERROR_UNKNOWN_DEVICE = 2


# SM_86 = {
# name: 'NVIDIA RTX A2000 12GB',
# computeMajor: 8,
# computeMinor: 6,
# maxThreadsPerBlock: 1024,
# maxThreadsPerMultiprocessor: 1536,
# regsPerBlock: 65536,
# regsPerMultiprocessor: 65536,
# warpSize: 32,
# sharedMemPerBlock: 49152,
# sharedMemPerMultiprocessor: 102400,
# numSms: 26,
# sharedMemPerBlockOptin: 101376,
# reservedSharedMemPerBlock: 1024
# }


# NVIDIA RTX A2000 12GB
SM_86 = cudaOccDeviceProp(computeMajor=8, computeMinor=6, maxThreadsPerBlock=1024, maxThreadsPerMultiprocessor=1536, regsPerBlock=65536, regsPerMultiprocessor=65536, warpSize=32, sharedMemPerBlock=49152, sharedMemPerMultiprocessor=102400, numSms=26, sharedMemPerBlockOptin=101376, reservedSharedMemPerBlock=1024)

def getMaxComputeMajor():
    return _cudaocc.getMaxComputeMajor()

class CUDAOccupancy:
    def __init__(self, deviceProps: cudaOccDeviceProp):
        self.props = deviceProps

    def SMemAllocationGranularity(self):
        limit = c_int(0)
        ret = _cudaocc.myOccSMemAllocationGranularity(byref(limit), self.props)
        if ret == CUDA_OCC_SUCCESS:
            return limit.value
        elif ret == CUDA_OCC_ERROR_UNKNOWN_DEVICE:
            raise ValueError(f"Unsupported device: {self.props.computeMajor}")
        elif ret == CUDA_OCC_ERROR_INVALID_INPUT:
            raise ValueError(f"Invalid input")


if __name__ == "__main__":
    print("Max compute major supported is", getMaxComputeMajor())
    d = CUDAOccupancy(SM_86)
    print(d.SMemAllocationGranularity())
