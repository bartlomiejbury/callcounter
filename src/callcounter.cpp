#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <mutex>
#include <thread>
#include <unordered_map>

static const char *outfile = "callcounter.raw";
static std::mutex file_mutex;

// Thread-local map with automatic cleanup
struct ThreadCallMap {
    std::unordered_map<void*, unsigned long> map;

    ~ThreadCallMap() {
        if (map.empty()) return;

        std::lock_guard<std::mutex> lock(file_mutex);
        FILE *f = fopen(outfile, "a");
        if (f) {
            auto tid = std::this_thread::get_id();
            size_t tid_num = std::hash<std::thread::id>{}(tid);
            for (const auto& [key, value] : map) {
                fprintf(f, "%p %lu %zu\n", key, value, tid_num);
            }
            fclose(f);
        }
    }
};

static thread_local ThreadCallMap thread_call_map;

// ===================
// Constructor / Destructor
// ===================
static void cc_constructor(void) __attribute__((constructor, no_instrument_function));
static void cc_constructor(void) {
    const char *env = getenv("CC_OUTFILE");
    if (env) outfile = env;
    // Clear file at program start
    FILE *f = fopen(outfile, "w");
    if (f) fclose(f);
}

// ===================
// Instrumentation functions
// ===================
extern "C" void __cyg_profile_func_enter(void *func, void *caller) {
    // Use operator[] which inserts with default value (0) if not found
    thread_call_map.map[func]++;
}

extern "C" void __cyg_profile_func_exit(void *func, void *caller) {
}
