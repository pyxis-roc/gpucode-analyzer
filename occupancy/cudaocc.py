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

PARTITIONED_GC_OFF = 0 # default
PARTITIONED_GC_ON = 1
PARTITIONED_GC_ON_STRICT = 2

FUNC_SHMEM_LIMIT_DEFAULT = 0
FUNC_SHMEM_LIMIT_OPTIN = 1

MAX_THREADS_PER_BLOCK_UNLIMITED = 2**31 - 1

class cudaOccFuncAttributes(Structure):
    _fields_ = [("maxThreadsPerBlock", c_int),
                ("numRegs", c_int),
                ("sharedSizeBytes", c_size_t),
                ("partitionedGCConfig", c_int),
                ("shmemLimitConfig", c_int),
                ("maxDynamicSharedSizeBytes", c_size_t),
                ("numBlockBarriers", c_int)
                ]

_cudaocc.myOccSMemAllocationGranularity.argtypes = [POINTER(c_int),
                                                    POINTER(cudaOccDeviceProp)]


CUDA_OCC_SUCCESS = 0
CUDA_OCC_ERROR_INVALID_INPUT = 1
CUDA_OCC_ERROR_UNKNOWN_DEVICE = 2

# deprecated on Volta
CACHE_PREFER_NONE = 0x0 # default
CACHE_PREFER_SHARED = 0x01
CACHE_PREFER_L1 = 0x02
CACHE_PREFER_EQUAL = 0x03

# Volta only
SHAREDMEM_CARVEOUT_DEFAULT = -1 # default
SHAREDMEM_CARVEOUT_MAX_SHARED = 100
SHAREDMEM_CARVEOUT_MAX_L1 = 0
SHAREDMEM_CARVEOUT_HALF= 50

class cudaOccDeviceState(Structure):
    _fields_ = [("cacheConfig", c_int),
                ("carveOutConfig", c_int)]

DEFAULT_DEVICE_STATE = cudaOccDeviceState(CACHE_PREFER_NONE,
                                          SHAREDMEM_CARVEOUT_DEFAULT)

OCC_LIMIT_WARPS         = 0x01 # - warps available
OCC_LIMIT_REGISTERS     = 0x02 # - registers available
OCC_LIMIT_SHARED_MEMORY = 0x04 # - shared memory available
OCC_LIMIT_BLOCKS        = 0x08 # - blocks available
OCC_LIMIT_BARRIERS      = 0x10 # - barrier available

class cudaOccResult(Structure):
    _fields_ = [("activeBlocksPerMultiprocessor", c_int),
                ("limitingFactors", c_uint),
                ("blockLimitRegs", c_int),
                ("blockLimitSharedMem", c_int),
                ("blockLimitWarps", c_int),
                ("blockLimitBlock", c_int),
                ("blockLimitBarriers", c_int),
                ("allocatedRegistersPerBlock", c_int),
                ("allocatedSharedMemPerBlock", c_size_t),
                ("partionedGCConfig", c_int)]

_cudaocc.myOccMaxActiveBlocksPerMultiprocessor.argtypes = [POINTER(cudaOccResult), POINTER(cudaOccDeviceProp), POINTER(cudaOccFuncAttributes), POINTER(cudaOccDeviceState), c_int, c_size_t]

# NVIDIA RTX A2000 12GB
SM_86 = cudaOccDeviceProp(computeMajor=8, computeMinor=6, maxThreadsPerBlock=1024, maxThreadsPerMultiprocessor=1536, regsPerBlock=65536, regsPerMultiprocessor=65536, warpSize=32, sharedMemPerBlock=49152, sharedMemPerMultiprocessor=102400, numSms=26, sharedMemPerBlockOptin=101376, reservedSharedMemPerBlock=1024)

def getMaxComputeMajor():
    return _cudaocc.getMaxComputeMajor()

class CUDAOccupancy:
    def __init__(self, deviceProps: cudaOccDeviceProp, deviceState: cudaOccDeviceState):
        self.props = deviceProps
        self.state = deviceState

    # internal function, just for testing
    def SMemAllocationGranularity(self):
        limit = c_int(0)
        ret = _cudaocc.myOccSMemAllocationGranularity(byref(limit), self.props)
        if ret == CUDA_OCC_SUCCESS:
            return limit.value
        elif ret == CUDA_OCC_ERROR_UNKNOWN_DEVICE:
            raise ValueError(f"Unsupported device: {self.props.computeMajor}")
        elif ret == CUDA_OCC_ERROR_INVALID_INPUT:
            raise ValueError(f"Invalid input")
        else:
            raise NotImplementedError

    def MaxActiveBlocksPerMultiprocessor(self, blockSize, dynamicSmemSize, funcattr: cudaOccFuncAttributes, state: cudaOccDeviceState = None):
        state = state or self.state
        res = cudaOccResult()
        ret = _cudaocc.myOccMaxActiveBlocksPerMultiprocessor(byref(res),
                                                             byref(self.props),
                                                             byref(funcattr),
                                                             byref(state),
                                                             blockSize,
                                                             dynamicSmemSize)
        if ret == CUDA_OCC_SUCCESS:
            return res
        elif ret == CUDA_OCC_ERROR_INVALID_INPUT:
            raise ValueError(f"Invalid input")
        elif ret == CUDA_OCC_ERROR_UNKNOWN_DEVICE:
            raise ValueError(f"Unsupported device")
        else:
            raise NotImplementedError

if __name__ == "__main__":
    print("Max compute major supported is", getMaxComputeMajor())
    d = CUDAOccupancy(SM_86, DEFAULT_DEVICE_STATE)

    fn = cudaOccFuncAttributes(MAX_THREADS_PER_BLOCK_UNLIMITED,
                               77,
                               0,
                               PARTITIONED_GC_OFF,
                               FUNC_SHMEM_LIMIT_DEFAULT,
                               0,
                               1)

    res = d.MaxActiveBlocksPerMultiprocessor(256, 0, fn)
    print(res.activeBlocksPerMultiprocessor,
          res.limitingFactors)
    print(res.activeBlocksPerMultiprocessor*256/d.props.maxThreadsPerMultiprocessor)


