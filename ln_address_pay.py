#!/usr/bin/env python3
"""Pay to a lightning address
"""

from pyln.client import Plugin
from pyln.client.lightning import RpcError
import requests
import secrets
import re

plugin = Plugin()

class LnServiceConfigResponse():
    callback: str
    max_sendable: int
    min_sendable: int
    metadata: str
    comment_allowed: int
    withdraw_link: str
    tag: str

@plugin.init()
def init(options: dict, configuration: dict, plugin: Plugin, **kwargs):
    plugin.log("Plugin ln-address-pay initialized")
    return {}

@plugin.method("lnaddresspay")
def pay_to_lightning_address(plugin, ln_address: str, msatoshi: int, label=None, riskfactor=None,
                maxfeepercent=None, retry_for=None, maxdelay=None, exemptfee=None):
    """This method sends msats to a lightning address.

    First argument is the address to send to, e.g. address@domain.com
    Second argument is the amount in msats to send

    Other arguments are optional and are passed to the pay method of the lightningd RPC
    """

    if not is_valid_ln_address(ln_address):
        return build_error_message(f"Invalid lightning address: {ln_address}")
    
    if not isinstance(msatoshi, int) or msatoshi <= 0:
        return build_error_message(f"Invalid amount in msatoshis: {msatoshi}")

    config = retrieve_ln_service_config(ln_address)
    if not config:
        return build_error_message(f"Could not download lightning address configuration for {ln_address} - is it valid?")
    
    if msatoshi < config.min_sendable or msatoshi > config.max_sendable:
        return build_error_message(f"Amount {msatoshi} is not within the allowed range of the lightning adress service: {config.min_sendable} - {config.max_sendable}")

    payment_invoice = retrieve_invoice(config, msatoshi)
    if not payment_invoice:
        return build_error_message(f"Could not retrieve an invoice for {ln_address}")
    
    try:
        payment_result = plugin.rpc.pay(bolt11=payment_invoice, label=label,
                riskfactor=riskfactor, maxfeepercent=maxfeepercent,
                retry_for=retry_for, maxdelay=maxdelay, exemptfee=exemptfee)
    except RpcError as e:
        return e.error
    except Exception as e:
        return build_error_message(f"An error occurred while processing the payment: {e}")
    
    return payment_result
    

def retrieve_ln_service_config(url) -> LnServiceConfigResponse:
    domain = url.split("@")[1]
    user = url.split("@")[0]
    ln_service_url = f"https://{domain}/.well-known/lnurlp/{user}"
    try:
        res = requests.get(ln_service_url)
        if res.status_code == 200:
            ln_service_config = LnServiceConfigResponse()
            ln_service_config.callback = res.json().get("callback")
            ln_service_config.max_sendable = res.json().get("maxSendable")
            ln_service_config.min_sendable = res.json().get("minSendable")
            ln_service_config.metadata = res.json().get("metadata")
            ln_service_config.comment_allowed = res.json().get("commentAllowed")
            ln_service_config.withdraw_link = res.json().get("withdrawLink")
            ln_service_config.tag = res.json().get("tag")
            return ln_service_config
    except Exception as e:
        return None

def retrieve_invoice(ln_service_config: LnServiceConfigResponse, amount: str) -> str:
    url = ln_service_config.callback
    data = {
        "amount": amount,
        "nonce": secrets.token_hex(8),
    }
    try:
        res = requests.get(url, params=data)
        if res.status_code == 200:
            return res.json().get("pr")
    except Exception as e:
        return None

def is_valid_ln_address(ln_address: str) -> bool:
    regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
    if re.match(regex, ln_address):
        return True
    return False

def build_error_message(error_message: str) -> str:
    return {
        "status": "failed",
        "message": error_message
    }

plugin.run()