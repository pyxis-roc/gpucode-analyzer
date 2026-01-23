all: pathtrace pathtrace.o

pathtrace.o: pathtrace.c
	$(CC) -c -O3 pathtrace.c

pathtrace: pathtrace.c
	$(CC) -O3 -DPT_TEST $< -o $@

.PHONY: clean

clean:
	rm -f pathtrace.o pathtrace
