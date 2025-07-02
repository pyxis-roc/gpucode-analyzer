#include <cuda_occupancy.h>

cudaOccError myOccSMemAllocationGranularity(int *limit, const cudaOccDeviceProp *properties) {
  return cudaOccSMemAllocationGranularity(limit, properties);
}

int getMaxComputeMajor() {
  struct cudaOccDeviceProp p;
  const int majors[] = {3,5,6,7,8,9,10,12,13,-1};
  int limit;
  int last_working = 0;

  for(int i = 0; majors[i] != -1; i++) {
    /* from examining the source code of cuda_occupancy.h,
       no other field is accessed */

    p.computeMajor = majors[i];
    cudaOccError r = cudaOccRegAllocationMaxPerThread(&limit, &p);

    if(r == CUDA_OCC_ERROR_UNKNOWN_DEVICE) {
      return last_working;
    } else if (r != CUDA_OCC_SUCCESS) {
      return 0;
    }

    last_working = majors[i];
  }

  return last_working;
}
