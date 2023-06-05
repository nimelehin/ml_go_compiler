import subprocess
import re
import os
import glob

BENCH_LOCS = [
    "go/test/bench/go1/",
    "",
    # Include other becnhmarks here...
]

file = open('results.txt', 'a+')
for BENCH_LOC in BENCH_LOCS:
    TEST_LOC = f"$TEST_LOC/{BENCH_LOC}"
    RUN_CNT = 7
    FUNC_FROM_TOP = 7
    cmd = f"go tool pprof --text $TEST_LOC/{BENCH_LOC}/profile.out"

    def clean_go_cache():
        cmd = f"$TEST_LOC/go/bin/go clean -cache"
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, error = process.communicate()
        output_str = output.decode("utf-8")
        return output_str

    def launch_bench(location, test, cnt, name=None):
        clean_go_cache()

        pth = os.getcwd()
        fn = os.environ.get('GO_FORCE_INLINE_FUNC', 'none')
        cmd = f"GO_FORCE_INLINE_FUNC='{fn}' $TEST_LOC/go/bin/go test -run='^$' -bench={test} -count={cnt} -benchmem -cpuprofile {pth}/profile.out"
        if name is not None:
            cmd += f" > {pth}/{name}.txt"
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, cwd=location, env=os.environ)
        output, error = process.communicate()
        output_str = output.decode("utf-8")
        error_str = ""
        if error is not None:
            error_str = error.decode("utf-8")
        return (output_str, error_str)

    def find_all_benches(location):
        res, _ = launch_bench(location, ".", 1)
        fullnames = []
        for line in res.splitlines():
            if line.startswith("Benchmark"):
                benchname = line.split("-")[0]
                fullnames.append(benchname)
        return fullnames

    def find_all_functions():
        pth = os.getcwd()
        cmd = f"go tool pprof --text {pth}/profile.out"
        # Start the process and capture the output
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        output, error = process.communicate()

        # Convert the output to a string
        output_str = output.decode("utf-8")

        funcs = []
        # Print the output string
        lines = output_str.splitlines()[7:]
        for line in lines:
            parts = line.split()
            func_name = line.split()[-1]
            if (func_name == "(inline)"):
                continue
            flat = float(parts[1][:-1])
            funcs.append((func_name, flat))
        return funcs

    def compare_res(f1, f2):
        pth = os.getcwd()
        cmd = f"benchstat -format csv {pth}/{f1}.txt {pth}/{f2}.txt"
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        output, error = process.communicate()
        output_str = output.decode("utf-8")

        lines = output_str.splitlines()
        res = []
        for line in lines:
            if line.startswith("geomean"):
                percent = float(line.split(",")[-1][:-1])
                res.append(percent)
        return res

    benches = find_all_benches(TEST_LOC)
    for bench in benches:
        try:
            launch_bench(TEST_LOC, bench, RUN_CNT, bench+"_old")
            funcs = find_all_functions()
            for func, flat in funcs[:FUNC_FROM_TOP]:
                if func.startswith("runtime."):
                    continue

                print("Started working on ", func)
                os.environ["GO_FORCE_INLINE_FUNC"] = func
                _, after_compile = launch_bench(TEST_LOC, bench, RUN_CNT, bench+"_new")
                after_compile = after_compile.splitlines()
                wdata = [-1] * 7
                for line in after_compile:
                    if line.startswith("*V*Z*_force_function_done"):
                        parts = line.split()
                        wdata = parts[2:]
                if wdata[0] == -1:
                    continue

                str_wdata = ' '.join(wdata)
                res = compare_res(bench+"_old", bench+"_new")
                if res[0] < -0.5:
                    file.write(f"+ " + str(func.split("/")[-1]) + " " + str(res[0]) + " " + str(flat) + " " + str_wdata + "\n")
                    file.flush()
                if res[0] > 0.5:
                    file.write(f"- " + str(func.split("/")[-1]) + " " + str(res[0]) + " " + str(flat) + " " + str_wdata + "\n")
                    file.flush()
        except:
            pass

file.close()
