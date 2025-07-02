/* -*- mode: c++ -*- */
#include <cuda.h>
#include <cuda_occupancy.h>
#include <cstdio>

#define dump_field(var, field) printf("%s=%d", #field, var.field)

void dumpOccDeviceProp(const cudaOccDeviceProp &prop) {
  printf("cudaOccDeviceProp(");
  dump_field(prop, computeMajor); printf(", ");
  dump_field(prop, computeMinor); printf(", ");
  dump_field(prop, maxThreadsPerBlock); printf(", ");
  dump_field(prop, maxThreadsPerMultiprocessor); printf(", ");
  dump_field(prop, regsPerBlock); printf(", ");
  dump_field(prop, regsPerMultiprocessor); printf(", ");
  dump_field(prop, warpSize); printf(", ");
  dump_field(prop, sharedMemPerBlock); printf(", ");
  dump_field(prop, sharedMemPerMultiprocessor); printf(", ");
  dump_field(prop, numSms); printf(", ");
  dump_field(prop, sharedMemPerBlockOptin); printf(", ");
  dump_field(prop, reservedSharedMemPerBlock);
  printf(")\n");
}

int main() {
  cudaDeviceProp prop;
  int dev = 0;

  if(cudaGetDeviceProperties(&prop, dev) == cudaSuccess) {
    cudaOccDeviceProp occProp = prop;
    printf("# %s\n", prop.name);
    dumpOccDeviceProp(occProp);
  } else {
    fprintf(stderr, "ERROR: Device %d is invalid.", dev);
    exit(1);
  }
}
