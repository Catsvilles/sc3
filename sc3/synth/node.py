"""Node.sc"""

import logging

from ..base import utils as utl
from ..base import responsedefs as rdf
from ..base import functions as fn
from ..base import model as mdl
from ..base import stream as stm
from ..base import clock as clk
from . import server as srv
from . import synthdesc as sdc
from . import _graphparam as gpp


__all__ = ['Group', 'ParGroup', 'Synth']


_logger = logging.getLogger(__name__)


class Node(gpp.NodeParameter):
    add_actions = {
        'addToHead': 0,
        'addToTail': 1,
        'addBefore': 2,
        'addAfter': 3,
        'addReplace': 4,
        'h': 0,
        't': 1,
        # // valid action numbers should stay the same
        0: 0, 1: 1, 2: 2, 3: 3, 4: 4
    }

    _register_all = False

    def __init__(self):
        super(gpp.NodeParameter, self).__init__(self)

    def _init_register(self, register):
        self._is_playing = None  # None (not watched/no info), True or False
        self._is_running = None  # None (not watched/no info), True or False
        if register or Node._register_all:
            self.register()

    @property
    def is_playing(self):
        return self._is_playing

    @property
    def is_running(self):
        return self._is_running

    @classmethod
    def basic_new(cls, server=None, node_id=None):
        obj = cls.__new__(cls)  # basic_new doesn't send therefore can't call __init__
        super(gpp.NodeParameter, obj).__init__(obj)
        obj.server = server or srv.Server.default
        if node_id is None:
            obj.node_id = obj.server.next_node_id()
        else:
            obj.node_id = node_id
        obj.group = None
        obj._is_playing = None  # None (not watched/no info), True or False
        obj._is_running = None  # None (not watched/no info), True or False
        return obj

    @classmethod
    def action_number_for(cls, add_action): # ='addToHead'): BUG: en sclang, semánticamente no tiene sentido el valor por defecto
        return cls.add_actions[add_action]

    def free(self, send_flag=True):
        if send_flag:
            self.server.send_msg('/n_free', self.node_id) # 11
        self.group = None

    def free_msg(self):
        return ('/n_free', self.node_id) # 11

    def run(self, flag=True):
        self.server.send_msg('/n_run', self.node_id, int(flag)) # 12

    def run_msg(self, flag=True):
        return ('/n_run', self.node_id, int(flag)) # 12

    def map(self, *args):
        bundle = self.map_msg(*args)
        if isinstance(bundle[0], str):
            self.server.send_bundle(None, bundle)
        else:
            self.server.send_bundle(None, *bundle)

    def map_msg(self, *args):
        kr_values = []
        ar_values = []
        result = []
        for control, bus in utl.gen_cclumps(args, 2):
            # No as_bus cast, Bus object is required for all
            # rate cases because the method joins /m_mapan.
            if bus.rate == 'control':
                kr_values.extend([
                    gpp.node_param(control)._as_control_input(),
                    bus.index,
                    bus.num_channels
                ])
            elif bus.rate == 'audio':
                ar_values.extend([
                    gpp.node_param(control)._as_control_input(),
                    bus.index,
                    bus.num_channels
                ])
            # // no default case, ignore others
        if len(kr_values) > 0:
            result.append(['/n_mapn', self.node_id] + kr_values)
        if len(ar_values) > 0:
            result.append(['/n_mapan', self.node_id] + ar_values)
        if len(result) < 2:
            result = utl.flatten(result)
        return result

    def mapn(self, *args):
        self.server.send_msg(
            '/n_mapn', # 48
            self.node_id,
            *gpp.node_param(args)._as_control_input()
        )

    def mapn_msg(self, *args):
        return ['/n_mapn', self.node_id]\
            + gpp.node_param(args)._as_control_input() # 48

    def set(self, *args):
        self.server.send_msg(
            '/n_set', # 15
            self.node_id,
            *gpp.node_param(args)._as_osc_arg_list()
        )

    def set_msg(self, *args):
        return ['/n_set', self.node_id]\
            + gpp.node_param(args)._as_osc_arg_list() # 15

    def setn(self, *args):
        self.server.send_msg(*self.setn_msg(*args))

    @classmethod
    def setn_msg_args(cls, *args):
        nargs = []
        args = gpp.node_param(args)._as_control_input()
        for control, more_vals in utl.gen_cclumps(args, 2):
            if isinstance(more_vals, list): # BUG: ídem acá arriba, more_vals TIENE QUE SER LISTA
                nargs.extend([control, len(more_vals)] + more_vals)
            else:
                nargs.extend([control, 1, more_vals])
        return nargs

    def setn_msg(self, *args):
        return ['/n_setn', self.node_id] + Node.setn_msg_args(*args) # 16

    def fill(self, cname, num_controls, value, *args):
        self.server.send_msg(
            '/n_fill', self.node_id, # 17
            cname, num_controls, value,
            *gpp.node_param(args)._as_control_input()
        )

    def fill_msg(self, cname, num_controls, value, *args):
        return ['n_fill', self.node_id, cname, num_controls, value]\
            + gpp.node_param(args)._as_control_input() # 17

    def release(self, release_time=None):
        self.server.send_msg(*self.release_msg(release_time))

    def release_msg(self, release_time=None):
        # // assumes a control called 'gate' in the synth
        if release_time is not None:
            if release_time <= 0:
                release_time = -1
            else:
                release_time = -(release_time + 1)
        else:
            release_time = 0
        return ['/n_set', self.node_id, 'gate', release_time] # 15

    def trace(self):
        self.server.send_msg('/n_trace', self.node_id) # 10

    def query(self, action=None):
        if action is None:
            def action(cmd, node_id, parent, prev, next,
                       is_group, head=None, tail=None):
                group = is_group == 1
                node_type = 'Group' if group else 'Synth'
                msg = (f'{node_type}: {node_id}'
                       f'\n   parent: {parent}'
                       f'\n   prev: {prev}'
                       f'\n   next: {next}')
                if group:
                    msg += (f'\n   head: {head}'
                            f'\n   tail: {tail}')
                print(msg)

        rdf.OscFunc(
            lambda msg, *_: action(*msg),
            '/n_info', self.server.addr,
            arg_template=[self.node_id]).one_shot()
        self.server.send_msg('/n_query', self.node_id)

    def register(self, playing=True, running=True):
        self.server._node_watcher.register(self, playing, running)

    def unregister(self):
        self.server._node_watcher.unregister(self)

    def on_free(self, action):
        def action_wrapper():
            fn.value(action, self)
            mdl.NotificationCenter.unregister(self, '/n_end', self)

        self.register()
        mdl.NotificationCenter.register(self, '/n_end', self, action_wrapper)

    def wait_for_free(self):
        condition = stm.Condition()
        self.on_free(lambda: condition.unhang())
        condition.hang()

    def move_before(self, node):
        self.group = node.group
        self.server.send_msg('/n_before', self.node_id, node.node_id) # 18

    def move_before_msg(self, node):
        self.group = node.group # TODO: estos msg podrían tener un parámetros update=True por defecto, pero no sé dónde se usan estas funciones aún.
        return ['/n_before', self.node_id, node.node_id] # 18

    def move_after(self, node):
        self.group = node.group
        self.server.send_msg('/n_after', self.node_id, node.node_id) # 19

    def move_after_msg(self, node):
        self.group = node.group
        return ['/n_after', self.node_id, node.node_id] # 19

    def move_to_head(self, group=None):
        group = group or self.server.default_group
        group.move_node_to_head(self) # se implementa en AbstractGroup

    def move_to_head_msg(self, group=None):
        group = group or self.server.default_group
        return group.move_node_to_head_msg(self) # se implementa en AbstractGroup

    def move_to_tail(self, group=None):
        group = group or self.server.default_group
        group.move_node_to_tail(self) # se implementa en AbstractGroup

    def move_to_tail_msg(self, group=None):
        group = group or self.server.default_group
        return group.move_node_to_tail_msg(self) # se implementa en AbstractGroup

    def order_nodes_msg(self, nodes):
        msg = ['/n_after'] # 19
        for first, to_move_after in utl.pairwise(nodes):
            msg.append(to_move_after.node_id)
            msg.append(first.node_id)
        return msg

    # TODO: VER:
    # ==
    # hash
    # printOn


    ### Node parameter interface ###

    def _as_control_input(self):
        return self.node_id

    def _as_target(self):
        return self


# // common base for Group and ParGroup classes
class AbstractGroup(Node):
    def __init__(self, target=None, add_action='addToHead', register=False):
        # // Immediately sends.
        super().__init__()
        target = gpp.node_param(target)._as_target()
        self.server = target.server
        self.node_id = self.server.next_node_id()
        add_action_id = type(self).add_actions[add_action]
        if add_action_id < 2:
            self.group = target
        else:
            self.group = target.group
        self._init_register(register)
        self.server.send_msg(
            self.creation_cmd(), self.node_id,
            add_action_id, target.node_id)

    def new_msg(self, target=None, add_action='addToHead'):
        # // if target is nil set to default group of server specified when basicNew was called
        target = gpp.node_param(target)._as_target()
        add_action_id = type(self).add_actions[add_action]
        if add_action_id < 2:
            self.group = target
        else:
            self.group = target.group
        return [self.creation_cmd(), self.node_id,
                add_action_id, target.node_id]

    # // for bundling
    def add_to_head_msg(self, group=None):
        # // if group is nil set to default group of server specified when basicNew was called
        self.group = group or self.server.default_group
        return [self.creation_cmd(), self.node_id, 0, self.group.node_id]

    def add_to_tail_msg(self, group=None):
        # // if group is nil set to default group of server specified when basicNew was called
        self.group = group or self.server.default_group
        return [self.creation_cmd(), self.node_id, 1, self.group.node_id]

    def add_after_msg(self, node):
        self.group = node.group
        return [self.creation_cmd(), self.node_id, 3, self.group.node_id]

    def add_before_msg(self, node):
        self.group = node.group
        return [self.creation_cmd(), self.node_id, 2, self.group.node_id]

    def add_replace_msg(self, node_to_replace):
        self.group = node_to_replace.group
        return [self.creation_cmd(), self.node_id, 4, node_to_replace.node_id]

    @classmethod
    def after(cls, node):
        return cls(node, 'addAfter')

    @classmethod
    def before(cls, node):
        return cls(node, 'addBefore')

    @classmethod
    def head(cls, group):
        return cls(group, 'addToHead')

    @classmethod
    def tail(cls, group):
        return cls(group, 'addToTail')

    @classmethod
    def replace(cls, node_to_replace):
        return cls(node_to_replace, 'addReplace')

    # // move Nodes to this group

    def move_node_to_head(self, node):
        node.group = self
        self.server.send_msg('/g_head', self.node_id, node.node_id) # 22

    def move_node_to_head_msg(self, node):
        node.group = self
        return ['/g_head', self.node_id, node.node_id] # 22

    def move_node_to_tail(self, node):
        node.group = self
        self.server.send_msg('/g_tail', self.node_id, node.node_id) # 23

    def move_node_to_tail_msg(self, node):
        node.group = self
        return ['/g_tail', self.node_id, node.node_id] # 23

    def free_all(self):
        # // free my children, but this node is still playing
        self.server.send_msg('/g_freeAll', self.node_id) # 24

    def free_all_msg(self):
        # // free my children, but this node is still playing
        return ['/g_freeAll', self.node_id] # 24

    def deep_free(self):
        self.server.send_msg('/g_deepFree', self.node_id) # 50

    def deep_free_msg(self):
        return ['/g_deepFree', self.node_id] # 50

    # // Introspection

    def dump_tree(self, post_controls=False):
        self.server.send_msg('/g_dumpTree', self.node_id, int(post_controls))

    def query_tree(self, query_controls=False, timeout=3):
        done = False

        def resp_func(msg, *_):
            i = 2
            tabs = 0
            if msg[1] != 0:
                print_controls = True
            else:
                print_controls = False
            outstr = f'NODE TREE Group {msg[2]}\n'
            if msg[3] > 0:
                def dump_func(num_children):
                    nonlocal i, tabs, outstr
                    tabs += 1
                    for _ in range(num_children):
                        if msg[i + 1] >= 0:
                            i += 2
                        else:
                            if print_controls:
                                i += msg[i + 3] * 2 + 1
                            i += 3
                        outstr += '   ' * tabs + f'{msg[i]}' # // nodeID
                        if msg[i + 1] >= 0:
                            outstr += ' group\n'
                            if msg[i + 1] > 0:
                                dump_func(msg[i + 1])
                        else:
                            outstr += f' {msg[i + 2]}\n' # // defname
                            if print_controls:
                                if msg[i + 3] > 0:
                                    outstr += ' ' + '   ' * tabs
                                j = 0
                                for _ in range(msg[i + 3]):
                                    outstr += ' '
                                    if type(msg[i + 4 + j]) is str:
                                        outstr += f'{msg[i + 4 + j]}: '
                                    outstr += f'{msg[i + 5 + j]}'
                                    j += 2
                                outstr += '\n'
                    tabs -= 1

                dump_func(msg[3])

            print(outstr)
            nonlocal done
            done = True

        resp = rdf.OscFunc(resp_func, '/g_queryTree.reply', self.server.addr)
        resp.one_shot()

        def timeout_func():
            if not done:
                resp.free()
                _logger.warning(
                    f"server '{self.server.name}' failed to respond "
                    f"to '/g_queryTree' after {timeout} seconds")

        self.server.send_msg('/g_queryTree', self.node_id, int(query_controls))
        clk.SystemClock.sched(timeout, timeout_func)

    @staticmethod
    def creation_cmd():
        raise NotImplementedError()


class Group(AbstractGroup):
    @staticmethod
    def creation_cmd():
        return '/g_new' # 21


class ParGroup(AbstractGroup):
    @staticmethod
    def creation_cmd():
        return '/p_new' # 63


class RootNode(Group):
    roots = dict()

    def __new__(cls, server=None):
        server = server or srv.Server.default
        if server.name in cls.roots:
            return cls.roots[server.name]
        else:
            obj = super(gpp.NodeParameter, cls).__new__(cls)
            obj.server = server
            obj.node_id = 0
            obj._is_playing = True  # Always true even if not watched.
            obj._is_running = True  # Always true even if not watched.
            obj.group = obj
            cls.roots[obj.server.name] = obj
            return obj

    def __init__(self, _=None):
        super(gpp.NodeParameter, self).__init__(self)

    def run(self):
        _logger.warning('run has no effect on RootNode')

    def free(self):
        _logger.warning('free has no effect on RootNode')

    def move_before(self):
        _logger.warning('moveBefore has no effect on RootNode')

    def move_after(self):
        _logger.warning('move_after has no effect on RootNode')

    def move_to_head(self):
        _logger.warning('move_to_head has no effect on RootNode')

    def move_to_tail(self):
        _logger.warning('move_to_tail has no effect on RootNode')

    @classmethod
    def free_all_roots(cls):  # renamed because collision with instance method
        for rn in cls.roots.values():
            rn.free_all()


class Synth(Node):
    def __init__(self, def_name, args=None, target=None,
                 add_action='addToHead', register=False):
        # // Immediately sends.
        super().__init__()
        target = gpp.node_param(target)._as_target()
        self.server = target.server
        self.node_id = self.server.next_node_id()
        add_action_id = type(self).add_actions[add_action]
        if add_action_id < 2:
            self.group = target
        else:
            self.group = target.group
        self.def_name = def_name
        self._init_register(register)
        self.server.send_msg(
            '/s_new', # 9
            self.def_name, self.node_id,
            add_action_id, target.node_id,
            *gpp.node_param(args or [])._as_osc_arg_list()
        )

    # // does not send (used for bundling)
    @classmethod
    def basic_new(cls, def_name, server=None, node_id=None):
        obj = super().basic_new(server, node_id)
        obj.def_name = def_name
        return obj

    @classmethod
    def new_paused(cls, def_name, args=None, target=None, add_action='addToHead'):
        target = gpp.node_param(target)._as_target()
        server = target.server
        add_action_id = cls.add_actions[add_action]
        synth = cls.basic_new(def_name, server)
        if add_action_id < 2:
            synth.group = target
        else:
            synth.group = target.group
        synth.server.send_bundle(
            0,
            [
                '/s_new', # 9
                synth.def_name, synth.node_id,
                add_action_id, target.node_id,
                *gpp.node_param(args or [])._as_osc_arg_list()
            ],
            [
                '/n_run', # 12
                synth.node_id, 0
            ]
        )
        return synth

    @classmethod
    def new_replace(cls, node_to_replace, def_name, args=None, same_id=False): # BUG: renombrado porque no pueden haber métodos de instancia y clase con el mismo nombre.
        if same_id:
            new_node_id = node_to_replace.node_id
        else:
            new_node_id = None
        server = node_to_replace.server
        synth = cls.basic_new(def_name, server, new_node_id)
        synth.server.send_msg(
            '/s_new', # 9
            synth.def_name, synth.node_id,
            4, node_to_replace.node_id, # 4 -> 'addReplace'
            *gpp.node_param(args or [])._as_osc_arg_list()
        )
        return synth

    # node_id -1
    @classmethod # TODO: este tal vez debería ir arriba
    def grain(cls, def_name, args=None, target=None, add_action='addToHead'):
        target = gpp.node_param(target)._as_target()
        server = target.server
        server.send_msg(
            '/s_new', # 9
            def_name.as_def_name(), -1, # BUG: as_def_name no está implementado puede ser método de Object
            cls.add_actions[add_action], target.node_id,
            *gpp.node_param(args or [])._as_osc_arg_list()
        )

    def new_msg(self, target=None, args=None, add_action='addToHead'):
        add_action_id = self.add_actions[add_action]
        target = gpp.node_param(target)._as_target()
        if add_action_id < 2:
            self.group = target
        else:
            self.group = target.group
        return ['/s_new', self.def_name, self.node_id, add_action_id,
                target.node_id, *gpp.node_param(args or [])._as_osc_arg_list()] # 9

    @classmethod
    def after(cls, node, def_name, args=None):
        return cls(def_name, args or [], node, 'addAfter')

    @classmethod
    def before(cls, node, def_name, args=None):
        return cls(def_name, args or [], node, 'addBefore')

    @classmethod
    def head(cls, group, def_name, args=None):
        return cls(def_name, args or [], group, 'addToHead')

    @classmethod
    def tail(cls, group, def_name, args=None):
        return cls(def_name, args or [], group, 'addToTail')

    def replace(self, def_name, args=None, same_id=False):
        return type(self).new_replace(self, def_name, args or [], same_id)

    # // for bundling
    def add_to_head_msg(self, group, args):
        # // if aGroup is nil set to default group of server specified when basicNew was called
        if group is not None:
            self.group = group
        else:
            self.group = self.server.default_group
        return ['/s_new', self.def_name, self.node_id, 0,
                self.group.node_id, *gpp.node_param(args)._as_osc_arg_list()] # 9

    def add_to_tail_msg(self, group, args):
        # // if aGroup is nil set to default group of server specified when basicNew was called
        if group is not None:
            self.group = group
        else:
            self.group = self.server.default_group
        return ['/s_new', self.def_name, self.node_id, 1,
                self.group.node_id, *gpp.node_param(args)._as_osc_arg_list()] # 9

    def add_after_msg(self, node, args=None):
        self.group = node.group
        return ['/s_new', self.def_name, self.node_id, 3,
                node.node_id, *gpp.node_param(args or [])._as_osc_arg_list()] # 9

    def add_before_msg(self, node, args=None):
        self.group = node.group
        return ['/s_new', self.def_name, self.node_id, 2,
                node.node_id, *gpp.node_param(args or [])._as_osc_arg_list()] # 9

    def add_replace_msg(self, node_to_replace, args):
        self.group = node_to_replace.group
        return ['/s_new', self.def_name, self.node_id, 4,
                node_to_replace.node_id, *gpp.node_param(args)._as_osc_arg_list()] # 9

    def get(self, index, action):
        def resp_func(msg, *_):
            # // The server replies with a message of the
            # // form: [/n_set, node ID, index, value].
            # // We want 'value' which is at index 3.
            fn.value(action, msg[3])

        rdf.OscFunc(
            resp_func, '/n_set', self.server.addr,
            arg_template=[self.node_id, index]).one_shot()

        self.server.send_msg('/s_get', self.node_id, index)  # 44

    def get_msg(self, index):
        return ['/s_get', self.node_id, index] # 44

    def getn(self, index, count, action):
        def resp_func(msg, *_):
            # // The server replies with a message of the form
            # // [/n_setn, node ID, index, count, *values].
            # // We want '*values' which are at indexes 4 and above.
            fn.value(action, msg[4:])

        rdf.OscFunc(
            resp_func, '/n_setn', self.server.addr,
            arg_template=[self.node_id, index]).one_shot()

        self.server.send_msg('/s_getn', self.node_id, index)  # 45

    def getn_msg(self, index, count):
        return ['/s_getn', self.node_id, index, count] # 45

    def seti(self, *args): # // args are [key, index, value, key, index, value ...]
        osc_msg = []
        synth_desc = sdc.SynthDescLib.at(self.def_name)
        if synth_desc is None:
            msg = 'message seti failed, because SynthDef {} was not added'
            _logger.warning(msg.format(self.def_name))
            return
        for key, offset, value in utl.gen_cclumps(args, 3):
            if key in synth_desc.control_dict:
                cname = synth_desc.control_dict[key]
                if offset < cname.num_channels:
                    osc_msg.append(cname.index + offset)
                    if isinstance(value, list):
                        osc_msg.append(value[:cname.num_channels - offset]) # keep
                    else:
                        osc_msg.append(value)
        self.server.send_msg(
            '/n_set', self.node_id,
            *gpp.node_param(osc_msg)._as_osc_arg_list()
        )

    # TODO, VER
    #printOn
