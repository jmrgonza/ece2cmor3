import logging
import time
from ece2cmor3.postproc import message

# Post-processing operator abstract base class

log = logging.getLogger(__name__)


class operator_base(object):

    stats = {}

    def __init__(self):

        self.values = None
        self.targets = []
        self.mask_values = None
        self.mask_targets = []
        self.mask_key = None
        self.store_var_values = None
        self.store_var_targets = []
        self.store_var_key = None
        self.cached_properties = [message.variable_key,
                                  message.datetime_key,
                                  message.timebounds_key,
                                  message.leveltype_key,
                                  message.levellist_key,
                                  message.resolution_key]
        self.property_cache = {}
        operator_base.stats[self.__class__.__name__] = {"n_recv" : 0, "t_recv": 0., "n_snd" : 0, "t_snd" : 0.}

    def receive_msg(self, msg):
        if not self.accept_msg(msg):
            return False
        if self.cache_is_full():
            self.clear_cache()
        if self.cache_is_empty():
            self.property_cache = {}
        for key in self.cached_properties:
            if key in self.property_cache:
                if not msg.get_field(key) == self.property_cache[key]:
                    log.error("Operator of type %s: message property %s changed during cache filling from %s to %s" %
                              (str(type(self)), key, self.property_cache[key], msg.get_field(key)))
                    self.print_state()
                    return False
            else:
                self.property_cache[key] = msg.get_field(key)
        start = time.clock()
        self.fill_cache(msg)
        stop = time.clock()
        self.update_stats("recv", stop - start)
        if self.cache_is_full():
            self.send_msg()
        return True

    def print_state(self):
        print self.property_cache

    def send_msg(self):
        start = time.clock()
        msg = self.create_msg()
        stop = time.clock()
        self.update_stats("snd", stop - start)
        for target in self.mask_targets:
            target.receive_mask(msg)
        for target in self.store_var_targets:
            target.receive_store_var(msg)
        for target in self.targets:
            target.receive_msg(msg)

    def accept_msg(self, msg):
        return True

    def receive_mask(self, msg):
        self.mask_values = msg.get_values()
        if self.cache_is_full():
            self.send_msg()

    def receive_store_var(self, msg):
        self.store_var_values = msg.get_values()
        if self.cache_is_full():
            self.send_msg()

    def create_msg(self):
        return message.memory_message(variable=self.property_cache[message.variable_key],
                                      timestamp=self.property_cache[message.datetime_key],
                                      timebounds=self.property_cache[message.timebounds_key],
                                      leveltype=self.property_cache[message.leveltype_key],
                                      levels=self.property_cache[message.levellist_key],
                                      resolution=self.property_cache[message.resolution_key],
                                      values=self.values)

    def fill_cache(self, msg):
        self.values = msg.get_values()
        return self.values is not None

    def clear_cache(self):
        self.values = None

    def cache_is_full(self):
        has_values = self.values is not None
        has_mask_values = True if self.mask_key is None else self.mask_values is not None
        has_store_values = True if self.store_var_key is None else self.store_var_values is not None
        return has_values and has_mask_values and has_store_values

    def cache_is_empty(self):
        return self.values is None

    def get_all_operators(self):
        result = [self]
        for operator in self.targets + self.mask_targets + self.store_var_targets:
            result.extend(operator.get_all_operators())
        return result

    def update_stats(self, param, dt):
        vals = operator_base.stats[self.__class__.__name__]
        vals["n_" + param] += 1
        vals["t_" + param] += dt


def write_stats(fname):
    cols = ["n_recv", "t_recv", "n_snd", "t_snd"]
    with open(fname, 'wb') as ofile:
        ofile.write("operator" + "\t\t" + '\t'.join(cols) + '\n')
        for record in operator_base.stats:
            statistics = operator_base.stats[record]
            ofile.write(record + "\t\t" + '\t'.join([str(statistics[c]) for c in cols]) + '\n')