#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <assert.h>
#include <stdbool.h>
#include <sys/types.h>
#include "pathtrace.h"

#define DEFAULT_PATH_SIZE 32

void path_trace_dump(struct path_traces *pt) {
  for (uint64_t i = 0; i < pt->ntraces; i++) {
    printf("trace %lu id %lu\n", i, pt->trace[i].trace_id);
    for (uint64_t j = 0; j < pt->trace[i].nentries; j++) {
      printf("\t %lu %lx %lu\n", j,
             pt->trace[i].path[j].branch_id,
	     pt->trace[i].path[j].count);
    }
  }
}

int path_trace_add_entry(struct trace *trace,
                         uint64_t branch_id,
			 uint64_t count) {
  bool new_entry = trace->nentries == 0 ||
                   trace->path[trace->nentries - 1].branch_id != branch_id;

  if (!new_entry) {
    trace->path[trace->nentries - 1].count += count;
  } else {
    if (trace->nentries == trace->nsize) {
      void *p = realloc(trace->path, sizeof(struct trace_entry) * trace->nsize * 2);
      if (p == NULL) {
        // better to lose the trace on failure to expand?
	return 0;
      }
      //printf("resizing to %lu %p\n", trace->nsize, trace->path);
      trace->nsize *= 2;
      trace->path = p;
    }

    trace->path[trace->nentries].branch_id = branch_id;
    trace->path[trace->nentries].count = count;
    trace->nentries++;
  }

  return 1;
}

void path_trace_init(struct path_traces *pt, uint64_t trace, uint64_t trace_id) {
  assert(pt->ntraces > trace);
  pt->trace[trace].trace_id = trace_id;
}

struct path_traces *path_trace_create(uint64_t ntraces) {
  struct path_traces *p;

  p = calloc(1, sizeof(struct path_traces));
  if(p != NULL) {
    p->ntraces = ntraces;
    p->trace = calloc(ntraces, sizeof(struct trace));
    if(p->trace == NULL) {
      free(p);
      return NULL;
    }

    for(int i = 0; i < ntraces; i++) {
      p->trace[i].nentries = 0;
      p->trace[i].nsize = DEFAULT_PATH_SIZE;
      p->trace[i].path = calloc(p->trace[i].nsize, sizeof(struct trace_entry));

      if (p->trace[i].path == NULL) {
        for (int j = 0; j < i; j++) {
          free(p->trace[j].path);
          free(p);
	  return NULL;
	}
      }
    }
  }

  return p;
}


#ifdef PT_TEST
int main(void) {
  struct path_traces *pt;
  pt = path_trace_create(1);
  if (pt == NULL) {
    fprintf(stderr, "Failed to create path trace\n");
    return 1;
  }

  path_trace_init(pt, 0, 1);
  path_trace_add_entry(&pt->trace[0], 2, 3);
  path_trace_add_entry(&pt->trace[0], 3, 1);
  path_trace_add_entry(&pt->trace[0], 2, 2);
  path_trace_add_entry(&pt->trace[0], 2, 4);
  path_trace_add_entry_fast(&pt->trace[0], 2, 5);
  path_trace_add_entry_fast(&pt->trace[0], 1, 5);

  path_trace_dump(pt);
}
#endif
