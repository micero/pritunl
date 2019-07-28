from pritunl.constants import *
from pritunl.helpers import *
from pritunl.exceptions import *
from pritunl import settings
from pritunl import logger
from pritunl import utils
from pritunl import event
from pritunl import mongo
from pritunl import messenger

import requests

def update():
    license = settings.app.license
    collection = mongo.get_collection('settings')

    if not settings.app.id:
        settings.app.id = utils.random_name()
        settings.commit()
        
    settings.local.sub_active = True
    settings.local.sub_status = "active"
    settings.local.sub_plan = 'enterprise'
    settings.local.sub_quantity = "None"
    settings.local.sub_amount = "250"
    settings.local.sub_period_end = None
    settings.local.sub_trial_end = None
    settings.local.sub_cancel_at_period_end = False
    settings.local.sub_balance = "250"
    settings.local.sub_url_key = None

    settings.app.license_plan = settings.local.sub_plan
    settings.commit()

    response = collection.update({
        '_id': 'subscription',
        '$or': [
            {'active': {'$ne': settings.local.sub_active}},
            {'plan': {'$ne': settings.local.sub_plan}},
        ],
    }, {'$set': {
        'active': settings.local.sub_active,
        'plan': settings.local.sub_plan,
    }})
    if response['updatedExisting']:
        if settings.local.sub_active:
            if settings.local.sub_plan == 'premium':
                event.Event(type=SUBSCRIPTION_PREMIUM_ACTIVE)
            elif settings.local.sub_plan == 'enterprise':
                event.Event(type=SUBSCRIPTION_ENTERPRISE_ACTIVE)
            elif settings.local.sub_plan == 'enterprise_plus':
                event.Event(type=SUBSCRIPTION_ENTERPRISE_PLUS_ACTIVE)
            else:
                event.Event(type=SUBSCRIPTION_NONE_INACTIVE)
        else:
            if settings.local.sub_plan == 'premium':
                event.Event(type=SUBSCRIPTION_PREMIUM_INACTIVE)
            elif settings.local.sub_plan == 'enterprise':
                event.Event(type=SUBSCRIPTION_ENTERPRISE_INACTIVE)
            elif settings.local.sub_plan == 'enterprise_plus':
                event.Event(type=SUBSCRIPTION_ENTERPRISE_PLUS_INACTIVE)
            else:
                event.Event(type=SUBSCRIPTION_NONE_INACTIVE)

    return True

def dict():
    if settings.app.demo_mode:
        url_key = 'demo'
    else:
        url_key = settings.local.sub_url_key

    return {
        'active': settings.local.sub_active,
        'status': settings.local.sub_status,
        'plan': settings.local.sub_plan,
        'quantity': settings.local.sub_quantity,
        'amount': settings.local.sub_amount,
        'period_end': settings.local.sub_period_end,
        'trial_end': settings.local.sub_trial_end,
        'cancel_at_period_end': settings.local.sub_cancel_at_period_end,
        'balance': settings.local.sub_balance,
        'url_key': url_key,
    }

def update_license(license):
    settings.app.license = license
    settings.app.license_plan = None
    settings.commit()
    valid = update()
    messenger.publish('subscription', 'updated')
    if not valid:
        raise LicenseInvalid('License key is invalid')
