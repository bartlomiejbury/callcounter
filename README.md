# Call Counter

A lightweight function call profiler using GCC's `-finstrument-functions` feature to track function call counts per thread.

## Overview

This tool instruments your C/C++ code to count how many times each function is called, with per-thread tracking. It uses compiler instrumentation to automatically intercept function entry points without modifying your source code.

## Components

- **callcounter.cpp** - Main instrumentation library that tracks function calls
- **resolver.py** - Post-processing tool to convert raw addresses to function names using debug symbols

## How It Works

1. Compile your code with `-finstrument-functions` flag
2. Link with `callcounter.cpp` compiled as a shared library
3. Run your program - function calls are automatically tracked
4. Process the output file with `resolver.py` to get human-readable function names

## Features

- **Per-thread tracking** - Each thread maintains its own hash map using `thread_local` storage
- **Automatic cleanup** - Destructor automatically saves data when threads exit
- **Thread-safe file writing** - `std::mutex` protected output prevents corruption
- **Zero instrumentation overhead** - All profiler functions marked with `__attribute__((no_instrument_function))`
- **Configurable output** - Set output file via `CC_OUTFILE` environment variable
- **Modern C++** - Uses `std::unordered_map`, `thread_local`, `std::mutex`, and `std::thread::id`

## Building

```bash
# Build the profiler library (DO NOT use -finstrument-functions here)
g++ -c -fno-PIE callcounter.cpp -o callcounter.o
ar rcs libcallcounter.a callcounter.o

# Or build as shared library
g++ -shared -fPIC callcounter.cpp -o libcallcounter.so
```

**Important:**
- The profiler library itself should NOT be compiled with `-finstrument-functions`
- Only your application code needs `-finstrument-functions`
- The `-fno-PIE` flag is required for the resolver to work correctly. With PIE enabled (Position Independent Executable), runtime addresses are randomized by ASLR, making them unmatchable with the fixed addresses in debug symbols.

## Usage

### 1. Compile your program with instrumentation

```bash
g++ -finstrument-functions -fno-PIE -g your_program.cpp -o your_program -no-pie -L. -lcallcounter
```

**Required flags:**
- `-finstrument-functions` - Enable function call instrumentation
- `-fno-PIE` and `-no-pie` - Disable position-independent code (required for address resolution)
- `-g` - Include debug symbols (required by resolver.py)

### 2. Run your program

```bash
./your_program
# Output written to callcounter.raw by default
```

Or specify a custom output file:
```bash
CC_OUTFILE=mycalls.raw ./your_program
```

### 3. Resolve addresses to function names

**Per-thread report:**
```bash
resolver.py --binary ./your_program --input callcounter.raw --output report.txt --threaded
```

**Sum all threads:**
```bash
resolver.py --binary ./your_program --input callcounter.raw --output report.txt --sum
```

## Output Format

### Raw format (callcounter.raw)
```
<function_address> <call_count> <thread_id>
0x401234 150 140737353971456
0x401567 42 140737353971456
```

### Resolved format (report.txt with --threaded)
```
=== Thread 140737353971456 ===
Function                  File:Line                    Call Count
my_function              test.cpp:10                  150
helper_func              test.cpp:25                  42

=== Thread 140737353971457 ===
Function                  File:Line                    Call Count
my_function              test.cpp:10                  180
```

### Resolved format (report.txt with --sum)
```
=== Thread ALL_THREADS ===
Function                  File:Line                    Call Count
my_function              test.cpp:10                  330
helper_func              test.cpp:25                  42
```

**Note:** Call counts are color-coded in terminal output (red for highest, yellow for medium, green for lowest).

## Configuration

### Output File
Set via environment variable:
```bash
export CC_OUTFILE=custom_output.raw
```

## Performance Considerations

- Uses `std::unordered_map` for dynamic hash table management
- No fixed capacity limit - grows as needed
- Automatic memory management (no manual allocation/deallocation)
- Mutex lock only on thread exit (minimal contention)
- Thread-local storage eliminates lock contention during profiling

## What Gets Counted

**Instrumented (counted):**
- Functions in your source files compiled with `-finstrument-functions`
- Functions you write and compile yourself
- Static and member functions in your code

**Not instrumented (not counted):**
- Standard library functions (`printf`, `malloc`, `free`, etc.)
- System library functions (`pthread_create`, `pthread_join`, `open`, `read`, etc.)
- Functions in pre-compiled libraries (`libpthread.so`, `libc.so`, etc.)
- Inline functions (compiler may optimize away the instrumentation)
- Compiler intrinsics and built-ins

The `-finstrument-functions` flag only instruments code **at compile time**. External libraries are already compiled without instrumentation, so their functions cannot be tracked. If you need to profile library calls, consider tools like `perf`, `gprof`, or `valgrind --tool=callgrind`.

## Limitations

- Only tracks function entry (not exit timing)
- No stack depth or call graph information
- Functions must have debug symbols for name resolution
- **PIE must be disabled** - Position Independent Executables randomize addresses at runtime
- Static inline functions may not be tracked

## Implementation Details

### Thread Safety
- Each thread has its own hash map using C++11 `thread_local` storage
- Automatic cleanup via C++ destructor (RAII)
- File writes protected by `std::mutex` with `std::lock_guard`
- Thread ID obtained via `std::this_thread::get_id()`

### Recursion Prevention
- `__attribute__((no_instrument_function))` on all profiler code
- Prevents infinite recursion during initialization

### Memory Management
- `std::unordered_map` provides automatic dynamic allocation
- Thread-local objects automatically destroyed when thread exits
- No manual memory management needed

## Example

```cpp
// test.cpp
#include <pthread.h>

void worker() {
    for (int i = 0; i < 100; i++) {
        // do work
    }
}

void* thread_func(void* arg) {
    worker();
    return nullptr;
}

int main() {
    pthread_t t1, t2;
    pthread_create(&t1, nullptr, thread_func, nullptr);
    pthread_create(&t2, nullptr, thread_func, nullptr);
    pthread_join(t1, nullptr);
    pthread_join(t2, nullptr);
    return 0;
}
```

Compile and run:
```bash
g++ -finstrument-functions -fno-PIE -g test.cpp callcounter.cpp -o test -no-pie -lpthread
./test
python3 resolver.py --binary ./test --input callcounter.raw --output report.txt --threaded
```

## License

See LICENSE.txt in project root.
