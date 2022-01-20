import argparse
from ramsis.datamodel import Status, EStatus, Project
from RAMSIS.core.store import Store


def parse_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'db_url', type=str, metavar='URL',
        help=('DB URL indicating the database dialect and connection '
              'arguments.'))
    parser.add_argument(
        '-project_name', type=str,
        help=('name of project to reset statuses for'))
    parser.add_argument(
        '-reset_error_status_only', type=bool, default=False,
        help=('Only reset statuses that are set to ERROR'
              'back to pending. COMPLETE/DISPATCHED '
              'Statuses are not updated.'))

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_cli()

    store = Store(args.db_url)

    if args.project_name:
        statuses = []
        project = store.session.query(Project).filter(
            Project.name == args.project_name).one_or_none()
        assert project, "Project name does not exist"
        for forecast in project.forecasts:
            statuses.append(forecast.status)
            for scenario in forecast.scenarios:
                statuses.append(scenario.status)
                for stage in scenario.stages:
                    statuses.append(stage.status)
                    for run in stage.runs:
                        statuses.append(run.status)

    else:
        statuses = store.session.query(Status).all()
    for s in statuses:
        if args.reset_error_status_only:
            if s.state == EStatus.ERROR:
                s.state = EStatus.PENDING
            else:
                continue
        else:
            s.state = EStatus.PENDING
    store.save()
    store.close()
