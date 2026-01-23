#pragma once

struct trace_entry {
  uint64_t branch_id;
  uint64_t count;
};

struct trace {
  uint64_t trace_id;
  uint64_t nentries;
  uint64_t nsize;

  struct trace_entry *path;
};

struct path_traces {
  uint64_t ntraces;
  struct trace *trace;
};

void path_trace_dump(struct path_traces *pt);
int path_trace_add_entry(struct trace *trace,
                         uint64_t branch_id,
			 uint64_t count);
void path_trace_init(struct path_traces *pt, uint64_t trace, uint64_t trace_id);
struct path_traces *path_trace_create(uint64_t ntraces);

static inline int path_trace_add_entry_fast(struct trace *trace,
                         uint64_t branch_id,
			 uint64_t count) {
  bool new_entry = trace->nentries == 0 ||
                   trace->path[trace->nentries - 1].branch_id != branch_id;

  if (!new_entry) {
    trace->path[trace->nentries - 1].count += count;
    return 1;
  } else {
    return path_trace_add_entry(trace, branch_id, count);
  }
}
