# ============================================
# PANEL API — Wrapper for SMM reseller panel
# ============================================

import requests
from config import PANEL_API_URL, PANEL_API_KEY


def _post(action, **kwargs):
    """Raw POST to panel API."""
    data = {'key': PANEL_API_KEY, 'action': action}
    data.update(kwargs)
    try:
        r = requests.post(PANEL_API_URL, data=data, timeout=30)
        return r.json()
    except Exception as e:
        return {'error': str(e)}


def get_balance():
    """Get current panel balance."""
    return _post('balance')


def get_services():
    """Get all available services."""
    return _post('services')


def place_order(service_id, link, quantity):
    """Place a new order.

    Args:
        service_id: Panel service ID (int)
        link: Instagram/TikTok URL
        quantity: Number of followers/likes

    Returns:
        dict with order ID or error
    """
    return _post('add', service=service_id, link=link, quantity=quantity)


def order_status(order_id):
    """Check status of an order."""
    return _post('status', order=order_id)


def multi_status(order_ids):
    """Check status of multiple orders."""
    ids = ','.join(str(i) for i in order_ids)
    return _post('status', orders=ids)


def cancel_order(order_id):
    """Cancel an order (if service allows)."""
    return _post('cancel', orders=order_id)


def refill_order(order_id):
    """Request refill for dropped followers."""
    return _post('refill', order=order_id)
