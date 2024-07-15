import os
from pyln.testing.fixtures import *

plugin_path = os.path.join(os.path.dirname(__file__), "ln_address_pay.py")

def test_ln_address_pay(node_factory):
    l1 = node_factory.get_node()
    # Test dynamically
    l1.rpc.plugin_start(plugin_path)
    l1.rpc.plugin_stop(plugin_path)
    l1.rpc.plugin_start(plugin_path)
    l1.stop()
    # Then statically
    l1.daemon.opts["plugin"] = plugin_path
    l1.start()
    l1.daemon.logsearch_start = 0
    l1.daemon.wait_for_logs(["Plugin ln-address-pay initialized",
                             "Plugin ln-address-pay initialized",
                             "Plugin ln-address-pay initialized"])
    l1.rpc.plugin_stop(plugin_path)

