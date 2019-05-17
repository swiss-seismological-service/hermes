# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
View model for projects table in `openprojectdialog`.

"""

from RAMSIS.ui.base.table.model import TableModel, TableColumn


class ProjectsTableModel(TableModel):

    def __init__(self, projects):
        super().__init__(projects)
        self.columns = [
            TableColumn('Name', editable=True),
            TableColumn('Start', attr='starttime', editable=True),
            TableColumn('Description', editable=True),
        ]
