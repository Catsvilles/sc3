"""Model.sc

TODO: REEMPLAZAR DEPENDANCY.PY EN SYNTH DESC POR NOTIFICATIONCENTER,
AMBAS CLASES HACEN LO MISMO Y DEPENDANCY ES INTRUSIVA.
"""

import collections


# BUG: o es clase privada o no va acá.
class dendrite():
    # TODO: no tiene toda la funcionalidad de MultiLevelIdentityDictionary
    # solo lo necesario para guardar y recuperar llaves como paths.

    def __init__(self):
        self.dictionary = dict()

    def __getitem__(self, path):
        path_lst = self._as_path(path)
        last = path_lst.pop()
        sub = self.dictionary
        for key in path_lst:
            if key in sub:
                sub = sub[key]
            else:
                raise KeyError(tuple(path))
        err = None
        try:
            return sub[last]
        except KeyError as e:
            err = e
        if err:
            raise KeyError(tuple(path))

    def _as_path(self, value):
        # TODO: o restringir a que sea solo una tupla
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, collections.Hashable):
            return [value]
        raise KeyError('{} is not a valid path'.format(type(value).__name__))

    def __setitem__(self, path, value):
        path_lst = self._as_path(path)
        last = path_lst.pop()
        sub = self.dictionary
        prev_sub = sub
        prev_key = None
        for key in path_lst:
            if isinstance(sub, dict):
                if key in sub:
                    prev_sub = sub
                    prev_key = key
                    sub = sub[key]
                else:
                    sub[key] = dict()
                    sub = sub[key]
            else:
                prev_sub[prev_key] = dict()
                sub = prev_sub[prev_key]
                sub[key] = dict()
                sub = sub[key]
        sub[last] = value

    def __delitem__(self, path):
        path_lst = self._as_path(path)
        last = path_lst.pop()
        sub = self.dictionary
        for key in path_lst:
            if key in sub:
                sub = sub[key]
            else:
                raise KeyError(tuple(path))
        del sub[last]

    def __contains__(self, path):
        path_lst = self._as_path(path)
        sub = self.dictionary
        for key in path_lst:
            if key in sub:
                return True
            else:
                return False

    def __repr__(self):
        msg = self.__class__.__name__ + '('
        msg += self.dictionary.__repr__() + ')'
        return msg

    def __str__(self):
        sub = self.dictionary
        self._msg = ''
        self._make_str(sub, 0)
        return self._msg

    def _make_str(self, sub, level):
        for key in sub:
            if isinstance(sub[key], dict):
                self._msg += ('  ' * level) + str(key) + ': ' + '\n'
                self._make_str(sub[key], level + 1)
            else:
                self._msg += ('  ' * level) + str(key) + ': ' + str(sub[key]) + '\n'


class SimpleController():
    def __init__(self, model):
        self.model = model
        self.model.add_dependant(self)
        self.actions = dic()

    def put(self, what, action):
        self.actions[what] = action

    def update(self, changer, what, *args):
        if len(self.actions) > 0 and what in self.actions:
            self.actions[what](changer, what, *args)

    def remove(self):
        self.model.remove_dependant(self)

    def remove_at(self, what):
        if len(self.actions) > 0 and what in self.actions:
            del self.actions[what]


#class TestDependant(): pass # BUG: no sé para qué es esta clase.


class NotificationCenter():
    registrations = dendrite()

    @classmethod
    def notify(cls, obj, msg, *args):
        if (obj, msg) in cls.registrations:
            for action in cls.registrations[obj, msg].copy().values():
                action(*args)

    @classmethod
    def register(cls, obj, msg, listener, action):
        cls.registrations[obj, msg, listener] = action
        return NotificationRegistration(obj, msg, listener)

    @classmethod
    def unregister(cls, obj, msg, listener):
        try:
            del cls.registrations[obj, msg, listener]
        except KeyError as e:
            raise KeyError('no registration found') from e
        if len(cls.registrations[obj, msg]) == 0:
            del cls.registrations[obj, msg]
            if len(cls.registrations[obj]) == 0:
                del cls.registrations[obj]

    @classmethod
    def register_one_shot(cls, obj, msg, listener, action):
        def shot(*args):
            action(*args)
            cls.unregister(obj, msg, listener)
        return cls.register(obj, msg, listener, shot)

    @classmethod
    def registration_exists(cls, obj, msg, listener):
        return (obj, msg, listener) in cls.registrations

    # @classmethod
    # def remove_for_listener(cls, listener):
    #     #del cls.registrations[] # BUG: no entiendo cómo puede ser que funcione la implementación en sclang
    #     pass

    @classmethod
    def clear(cls):
        cls.registrations = dendrite()


class NotificationRegistration():
    def __init__(self, obj, msg, listener):
        self.obj = obj
        self.msg = msg
        self.listener = listener

    def remove(self):
        NotificationCenter.unregister(self.obj, self.msg, self.listener)