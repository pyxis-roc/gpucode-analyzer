NVCC:=nvcc

all: cudaocc.so gen_device_prop

cudaocc.so: cudaocc.o
	gcc -shared -o $@ $<

cudaocc.o: cudaocc.c
	$(CC) -I$(CUDA_INSTALL_PATH)/include -fPIC $< -c -o $@

gen_device_prop: gen_device_prop.cu
	$(NVCC) $< -o $@
