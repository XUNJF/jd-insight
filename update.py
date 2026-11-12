import subprocess
import sys
import time
import os


STEPS = [
    ("抓取","collect.py"),
    ("抽取","extract.py"),
]
BASE = os.path.dirname(os.path.abspath(__file__))

def run_step(name, script):
    print(f"\n{'=' * 50}")
    print(f"  {name}:{script}")
    print(f"{'=' * 50}")
    result = subprocess.run([sys.executable, os.path.join(BASE,script)], cwd=BASE)
    if result.returncode != 0:
        print(f"\n  ✗ {name} 失败（退出码{result.returncode}）,中止")
        return False
    print(f"  ✓ {name}完成")
    return True


def main():
    start = time.time()
    for name, script in STEPS:
        if not run_step(name, script):
            return 1

    cost = time.time() - start
    print(f"\n{'=' * 50}")
    print(f"  全部完成，耗时{cost:.1f}秒")
    print(f"{'=' * 50}")
    return 0

if __name__ == "__main__":
    sys.exit(main())