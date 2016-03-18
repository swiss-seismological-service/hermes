from PyQt4 import QtCore


class ModelResultsLayer(QtCore.QObject):
    layer_changed = QtCore.pyqtSignal(dict)

    def __init__(self, store, entity, date_time_attr='date_time'):
        QtCore.QObject.__init__(self)
        self.store = store
        self.entity = entity
        self.date_attr = date_time_attr
        self._items = []

    def reload_from_store(self):
        """
        Reloads all items from the persistent store.

        """
        self._items = self.store.read_all(self.entity, order=self.date_attr)

    def clear(self):
        """
        Delete all data from the db

        """
        self.store.purge_entity(self.entity)
        self._items = []
        self._emit_change_signal({})

    def all_items(self):
        return self._items

    def add(self, it, persist=False):
        """
        Add one or more items to the layer (and store)

        :param it: item or list of items

        """
        try:
            it_list = [i for i in it]
        except TypeError:
            it_list = [it]
        self._items += it_list
        if persist:
            self.store.add(it_list)
        self._emit_change_signal({})

    def __getitem__(self, item):
        return self._items[item]

    def __len__(self):
        return len(self._items)

    def _emit_change_signal(self, change_dict):
        default_dict = {'layer': self}
        d = dict(default_dict.items() + change_dict.items())
        self.layer_changed.emit(d)
