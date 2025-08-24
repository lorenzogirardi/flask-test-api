from .utils import get_redis_connection
import json
import uuid

r = get_redis_connection()

def get_all_contexts():
    keys = r.keys('context:*')
    return [json.loads(r.get(key)) for key in keys]

def get_context_by_id(context_id):
    context = r.get(f'context:{context_id}')
    if not context:
        return None
    return json.loads(context)

def create_new_context(data):
    if 'title' not in data:
        return None
    context = {
        'id': str(uuid.uuid4()),
        'title': data['title'],
        'description': data.get('description', ""),
        'done': False
    }
    r.set(f'context:{context["id"]}', json.dumps(context))
    return context

def update_existing_context(context_id, data):
    if not r.exists(f'context:{context_id}'):
        return None
    context = json.loads(r.get(f'context:{context_id}'))
    context.update(data)
    r.set(f'context:{context["id"]}', json.dumps(context))
    return context

def delete_context_by_id(context_id):
    if not r.exists(f'context:{context_id}'):
        return False
    r.delete(f'context:{context_id}')
    return True
