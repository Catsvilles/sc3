"""InOut.sc"""

import logging

from .. import ugen as ugn
from .. import _global as _gl
from .. import utils as utl
from .. import graphparam as gpp


_logger = logging.getLogger(__name__)


### Controls ###

class ControlName():
    def __init__(self, name, index, rate, default_value, arg_num, lag=None):
        self.name = name
        self.index = index
        self.rate = rate
        self.default_value = default_value
        self.arg_num = arg_num
        self.lag = lag or 0.0

    def num_channels(self):
        return len(utl.as_list(self.default_value))

    #def print_on(self, stream):
    def __str__(self):
        string = 'ControlName P ' + str(self.index)
        if self.name is not None: string += ' ' + self.name
        if self.rate is not None: string += ' ' + self.rate
        if self.default_value is not None: string += ' ' + str(self.default_value)
        return string


class Control(ugn.MultiOutUGen):
    def __init__(self):
        super().__init__()
        self.values = []

    @classmethod
    def names(cls, names):
        synthdef = _gl.current_synthdef
        index = synthdef.control_index
        names = utl.as_list(names)
        for i, name in enumerate(names):
            synthdef.add_control_name(
                ControlName(
                    name, index + i, 'control',
                    None, synthdef.all_control_names
                )
            )

    @classmethod
    def ir(cls, values):
        return cls._multi_new_list(['scalar'] + utl.as_list(values))

    @classmethod
    def kr(cls, values):
        return cls._multi_new_list(['control'] + utl.as_list(values))

    def _init_ugen(self, *values):
        self.values = list(values)
        if self.synthdef is not None:
            self.special_index = len(self.synthdef.controls) # TODO: VER, esto se relaciona con _Symbol_SpecialIndex como?
            self.synthdef.controls.extend(self.values)

            ctl_names = self.synthdef.control_names
            if len(ctl_names) > 0:
                # // current control is always the last added, so:
                last_control = ctl_names[-1]
                if last_control.default_value is None:
                    # // only write if not there yet:
                    last_control.default_value = utl.unbubble(self.values)

            self.synthdef.control_index += len(self.values)
        return self._init_outputs(len(self.values), self.rate)

    @classmethod
    def is_control_ugen(cls):
        return True


class AudioControl(ugn.MultiOutUGen):
    def __init__(self):
        super().__init__()
        self.values = []

    @classmethod
    def names(cls, names):
        synthdef = _gl.current_synthdef # VER: lo mimso que arriba, es local, luego _init_ugen llama a self.synthdef, supongo que se inicializa en las subclases.
        index = synthdef.control_index
        names = utl.as_list(names)
        for i, name in enumerate(names):
            synthdef.add_control_name(
                ControlName(
                    name, index + i, 'audio',
                    None, synthdef.all_control_names
                )
            )

    @classmethod
    def ar(cls, values):
        return cls._multi_new_list(['audio'] + utl.as_list(values))

    def _init_ugen(self, *values):
        self.values = list(values)
        if self.synthdef is not None:
            self.special_index = len(self.synthdef.controls) # TODO: VER, esto se relaciona con _Symbol_SpecialIndex como?
            self.synthdef.controls.extend(self.values)
            self.synthdef.control_index += len(self.values)
        return self._init_outputs(len(self.values), self.rate)

    @classmethod
    def is_audio_control_ugen(cls):
        return True

    @classmethod
    def is_control_ugen(cls):
        return True


class TrigControl(Control):
    pass  # Empty.


class LagControl(Control):
    @classmethod
    def ir(cls, values):
        raise NotImplementedError(
            f'{cls.__name__} should not implemet ir constructor')

    @classmethod
    def kr(cls, values, lags):
        values = utl.as_list(values)
        if isinstance(lags, (int, float)): # isNumber
            lags = [lags] * len(values)
        else:
            lags = utl.as_list(lags)

        if len(values) != len(lags):
            _logger.warning(f'{cls.__name__} len(values) is not len(lags), '
                            f'{cls.__name__}.kr returns None')
            return None

        n = 16
        values = [values[i:i + n] for i in range(0, len(values), n)]  # values.clump(16)
        lags = [lags[i:i + n] for i in range(0, len(lags), n)]  # lags.clump(16)
        outputs = []
        for i in range(len(values)):
            outputs.extend(cls._multi_new_list(['control'] + values[i] + lags[i]))
        return outputs

    @classmethod
    def ar(cls, values, lags):
        return AudioControl.ar(values).lag(lags)

    def _init_ugen(self, *stuff):
        # *** BUG: in sclang, lags variable not used.
        size = len(stuff)
        size2 = size >> 1  # size // 2
        self.values = list(stuff)[size2:size]
        if self.synthdef is not None:
            self.special_index = len(self.synthdef.controls) # TODO: VER, esto se relaciona con _Symbol_SpecialIndex como?
            self.synthdef.controls.extend(self.values)
            self.synthdef.control_index += len(self.values)
        return self._init_outputs(len(self.values), self.rate)


### Inputs ###

class AbstractIn(ugn.MultiOutUGen):
    @classmethod
    def is_input_ugen(self):
        return True


class In(AbstractIn):
    @classmethod
    def ar(cls, bus=0, num_channels=1):
        return cls._multi_new('audio', num_channels, bus)

    @classmethod
    def kr(cls, bus=0, num_channels=1):
        return cls._multi_new('control', num_channels, bus)

    def _init_ugen(self, num_channels, *arg_bus):
        self._inputs = list(arg_bus)
        return self._init_outputs(num_channels, self.rate)


class LocalIn(AbstractIn):
    @classmethod
    def ar(cls, num_channels=1, default=0.0):
        return cls._multi_new('audio', num_channels, *utl.as_list(default))

    @classmethod
    def kr(cls, num_channels=1, default=0.0):
        return cls._multi_new('control', num_channels, *utl.as_list(default))

    def _init_ugen(self, num_channels, *default):
        self._inputs = list(utl.wrap_extend(list(default), num_channels))
        return self._init_outputs(num_channels, self.rate)


class LagIn(AbstractIn):
    @classmethod
    def kr(cls, bus=0, num_channels=1, lag=0.1):
        return cls._multi_new('control', num_channels, bus, lag)

    def _init_ugen(self, num_channels, *inputs):
        self._inputs = list(inputs)
        return self._init_outputs(num_channels, self.rate)


class InFeedback(AbstractIn):
    @classmethod
    def ar(cls, bus=0, num_channels=1):
        return cls._multi_new('audio', num_channels, bus)

    def _init_ugen(self, num_channels, *arg_bus):
        self._inputs = list(arg_bus)
        return self._init_outputs(num_channels, self.rate)


class InTrig(AbstractIn):
    @classmethod
    def kr(cls, bus=0, num_channels=1):
        return cls._multi_new('control', num_channels, bus)

    def _init_ugen(self, num_channels, *arg_bus):
        self._inputs = list(arg_bus)
        return self._init_outputs(num_channels, self.rate)


### Outputs ###

class AbstractOut(ugn.UGen):
    def num_outputs(self):
        return 0

    def write_output_specs(self, file):
        pass # Se define como no hacer nada porque las ugens que escriben a buses no tienen señales de salida (cables internos). Es interfaz de polimorfismo desde UGen.

    def check_inputs(self):
        if self.rate == 'audio':
            for i in range(type(self).num_fixed_args(), len(self.inputs)):
                if gpp.ugen_param(self.inputs[i]).as_ugen_rate() != 'audio':
                    return (f'{type(self).__name__}: input at index '
                            f'{i} ({type(self.inputs[i]).__name__}) '
                            'is not audio rate')
        elif len(self.inputs) <= type(self).num_fixed_args():
            return 'missing input at index 1'
        return self.check_valid_inputs()

    @classmethod
    def is_output_ugen(cls):
        return True

    @classmethod
    def num_fixed_args(cls):
        raise NotImplementedError('subclass responsibility')

    def num_audio_channels(self):
        return len(self.inputs) - type(self).num_fixed_args()

    def writes_to_bus(self):
        raise NotImplementedError('subclass responsibility')


class Out(AbstractOut):
    @classmethod
    def ar(cls, bus, output):
        output = gpp.ugen_param(utl.as_list(output))
        output = output.as_ugen_input(cls)
        output = cls.replace_zeroes_with_silence(output)
        cls._multi_new_list(['audio', bus] + output)
        # return 0.0  # // Out has no output.

    @classmethod
    def kr(cls, bus, output):
        cls._multi_new_list(['control', bus] + utl.as_list(output))
        # return 0.0  # // Out has no output.

    @classmethod
    def num_fixed_args(cls):
        return 1

    def writes_to_bus(self):
        return True


class ReplaceOut(Out):
    pass  # Empty.


class OffsetOut(Out):
    @classmethod
    def kr(cls, bus, output):
        raise NotImplementedError(
            f'{cls.__name__} should not implement kr constructor')


class LocalOut(AbstractOut):
    @classmethod
    def ar(cls, output):
        output = gpp.ugen_param(utl.as_list(output))
        output = output.as_ugen_input(cls)
        output = cls.replace_zeroes_with_silence(output)
        cls._multi_new_list(['audio'] + output)
        # return 0.0  # // LocalOut has no output.

    @classmethod
    def kr(cls, output):
        output = utl.as_list(output)
        cls._multi_new_list(['audio'] + output)
        # return 0.0  # // LocalOut has no output.

    @classmethod
    def num_fixed_args(cls):
        return 0

    def writes_to_bus(self):
        return False


class XOut(AbstractOut):
    @classmethod
    def ar(cls, bus, xfade, output):
        output = gpp.ugen_param(utl.as_list(output))
        output = output.as_ugen_input(cls)
        output = cls.replace_zeroes_with_silence(output)
        cls._multi_new_list(['audio', bus, xfade] + output)
        # return 0.0  # // XOut has no output.

    @classmethod
    def kr(cls, bus, xfade, output):
        output = utl.as_list(output)
        cls._multi_new_list(['control', bus, xfade] + output)
        # return 0.0  # // XOut has no output.

    @classmethod
    def num_fixed_args(cls):
        return 2

    def writes_to_bus(self):
        return True
