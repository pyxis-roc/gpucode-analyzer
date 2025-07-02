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

cudaOccError myOccAvailableDynamicSMemPerBlock(
  size_t                      *dynamicSmemSize,
  const cudaOccDeviceProp     *properties,
  const cudaOccFuncAttributes *attributes,
  const cudaOccDeviceState    *state,
  int                         numBlocks,
  int                         blockSize) {

  return cudaOccAvailableDynamicSMemPerBlock(dynamicSmemSize,
                                             properties,
                                             attributes,
                                             state,
                                             numBlocks,
                                             blockSize);
}

cudaOccError myOccMaxPotentialOccupancyBlockSize(
    int                         *minGridSize,
    int                         *blockSize,
    const cudaOccDeviceProp     *properties,
    const cudaOccFuncAttributes *attributes,
    const cudaOccDeviceState    *state,
    size_t                     (*blockSizeToDynamicSMemSize)(int),
    size_t                       dynamicSMemSize) {

  return cudaOccMaxPotentialOccupancyBlockSize(
    minGridSize, blockSize, properties, attributes, state,
    blockSizeToDynamicSMemSize, dynamicSMemSize);
}

int getMaxComputeMajor() {
  return __CUDA_OCC_MAJOR__;
}

int getMaxComputeMinor() {
  return __CUDA_OCC_MINOR__;
}
