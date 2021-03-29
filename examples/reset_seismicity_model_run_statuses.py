import argparse
from ramsis.datamodel.status import Status, EStatus
from RAMSIS.core.store import Store


def parse_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'db_url', type=str, metavar='URL',
        help=('DB URL indicating the database dialect and connection '
              'arguments.'))

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_cli()

    store = Store(args.db_url)

    statuses = store.session.query(Status).all()

    for s in statuses:
        s.state = EStatus.PENDING
    store.save()
    store.close()
