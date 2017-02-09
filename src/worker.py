import sys

from workers.rj.main import main as run_rj


def main():
    commands = ['rj', 'etas', 'shapiro']
    validate(commands)
    run(commands)


def validate(commands):
    valid = True
    if len(sys.argv) != 2:
        valid = False
    if sys.argv[1] not in commands:
        valid = False
    if not valid:
        print 'usage: worker.py [{}]'.format('|'.join(commands))
        sys.exit()


def run(commands):
    arg = sys.argv[1]
    if arg == commands[0]:
        run_rj()
    elif arg == commands[1]:
        print 'todo'
        sys.exit()
    elif arg == commands[2]:
        print 'todo'
        sys.exit()


if __name__ == '__main__':
    main()
