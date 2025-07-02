#include <cuda_occupancy.h>

cudaOccError myOccSMemAllocationGranularity(int *limit, const cudaOccDeviceProp *properties) {
  return cudaOccSMemAllocationGranularity(limit, properties);
}

cudaOccError myOccMaxActiveBlocksPerMultiprocessor(
  cudaOccResult               *result,
  const cudaOccDeviceProp     *properties,
  const cudaOccFuncAttributes *attributes,
  const cudaOccDeviceState    *state,
  int                          blockSize,
  size_t                       dynamicSmemSize)
{
  return cudaOccMaxActiveBlocksPerMultiprocessor(result, properties,
                                                 attributes, state,
                                                 blockSize, dynamicSmemSize);
}

int getMaxComputeMajor() {
  return __CUDA_OCC_MAJOR__;
}

int getMaxComputeMinor() {
  return __CUDA_OCC_MINOR__;
}
