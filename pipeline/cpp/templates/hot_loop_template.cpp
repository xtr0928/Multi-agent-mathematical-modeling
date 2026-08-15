// hot_loop_template.cpp —— C++ OpenMP 确定性重算模板（开发文档 §3.6）
//
// 铁律：
//  1. 确定性归约：固定分块 + 固定归约树，同任务 10 连跑结果 SHA-512 全等（A8）
//  2. 双精度输出：%.17g（D12/A9，解析端逐字节恢复 double 位模式）
//  3. 任务协议：stdin 读任务 JSON，stdout 回结果 JSON（§3.2/§3.3）
//  4. 平局显式 ε 规则；struct 交换用 '=' 前缀（既有实战教训）
//
// 编译：g++ -O3 -fopenmp -march=native -std=c++17 hot_loop_template.cpp -o hot_loop

#include <cstdio>
#include <cstring>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>
#include <numeric>
#include <random>
#include <omp.h>

// ---------- 任务 JSON 解析（极简：只解析模板需要的字段） ----------
static std::string g_json;
static size_t g_pos = 0;

static void skip_ws() { while (g_pos < g_json.size() && (g_json[g_pos]==' '||g_json[g_pos]=='\n'||g_json[g_pos]=='\t'||g_json[g_pos]=='\r')) g_pos++; }

static long long read_int() {
    skip_ws();
    bool neg = false;
    if (g_json[g_pos]=='-') { neg=true; g_pos++; }
    long long v = 0;
    while (g_pos < g_json.size() && g_json[g_pos]>='0' && g_json[g_pos]<='9') { v = v*10 + (g_json[g_pos]-'0'); g_pos++; }
    return neg ? -v : v;
}

// ---------- 确定性归约：pairwise 求和（固定归约树，与线程数无关） ----------
static double pairwise_sum(const std::vector<double>& v) {
    std::vector<double> cur = v;
    while (cur.size() > 1) {
        std::vector<double> nxt((cur.size()+1)/2, 0.0);
        #pragma omp parallel for schedule(static)
        for (size_t i = 0; i < cur.size(); i += 2) {
            nxt[i/2] = cur[i] + (i+1 < cur.size() ? cur[i+1] : 0.0);
        }
        cur = nxt;
    }
    return cur.empty() ? 0.0 : cur[0];
}

// ---------- counter-based RNG（splitmix64）：随机流只依赖迭代序号 i，与线程数无关 ----------
// 铁律：结果必须线程数无关（8 线程 vs 2 线程结果逐位一致），否则"可复现断言"失效
static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9E3779B97F4A7C15ULL;
    x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;
    x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;
    return x ^ (x >> 31);
}
static inline double u01_from(uint64_t x) {
    return (double)(x >> 11) * (1.0 / 9007199254740992.0);
}

// ---------- 用户计算区：蒙特卡洛 π 估计（占位示例，替换为实际 hot loop） ----------
static double mc_pi_est(long long n_iter, uint64_t seed) {
    std::vector<double> partial_hits;
    partial_hits.resize(omp_get_max_threads(), 0.0);
    // 固定分块 + 每迭代独立随机流：结果与线程数、调度方式均无关
    #pragma omp parallel
    {
        int tid = omp_get_thread_num();
        int nt = omp_get_num_threads();
        long long start = (long long)n_iter * tid / nt;
        long long end = (long long)n_iter * (tid + 1) / nt;
        double hits = 0.0;
        for (long long i = start; i < end; ++i) {
            double x = u01_from(splitmix64((uint64_t)i * 2 + seed));
            double y = u01_from(splitmix64((uint64_t)i * 2 + 1 + seed));
            if (x*x + y*y <= 1.0) hits += 1.0;
        }
        partial_hits[tid] = hits;
    }
    return pairwise_sum(partial_hits) / (double)n_iter * 4.0;
}

int main() {
    // 1. 读任务 JSON（stdin）
    std::string line, all;
    while (std::getline(std::cin, line)) all += line;
    g_json = all;

    // 2. 解析字段：n_iter / seed
    g_pos = g_json.find("\"n_iter\"");
    if (g_pos == std::string::npos) { printf("{\"status\":\"failed\",\"error\":\"missing n_iter\"}"); return 1; }
    g_pos += 9;  // 跳过 "n_iter":
    long long n_iter = read_int();
    g_pos = g_json.find("\"seed\"");
    unsigned seed = 1;
    if (g_pos != std::string::npos) { g_pos += 7; seed = (unsigned)read_int(); }

    // 3. 计算（占位：π 估计。实际任务替换此函数，保持确定性归约纪律）
    double result = mc_pi_est(n_iter, seed);

    // 4. 回结果 JSON：%.17g 双精度输出（D12/A9）
    //    结果哈希由 Python 端在 stdout 落盘后计算
    printf("{\"status\":\"success\",\"results\":{\"pi_estimate\":%.17g,\"n_iter\":%lld},\"thread_count\":%d}\n",
           result, n_iter, omp_get_max_threads());
    return 0;
}
