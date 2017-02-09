import os
import sys

sys.path.append(os.path.abspath('ramsis'))

from ramsis.main import main as run_ramsis  # NOQA


def main():
    run_ramsis()


if __name__ == '__main__':
    main()
