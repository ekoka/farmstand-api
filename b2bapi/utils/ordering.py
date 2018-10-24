from ccaapi.api import APIUrl
from ccaapi.api import reload_resource, delete_resource

def reorganize(db, target_type, target=None, position=None, group_fields=None,
               position_field="position", routes_cache_clean=None, reload_async=True):
    query = db.session.query(target_type)
    if group_fields is not None:
        for g in group_fields:
            query = query.filter(g[0]==g[1])
    if position == None: 
        position = query.count()
    items = query.filter(getattr(target_type, position_field)>=position)\
                 .order_by(getattr(target_type, position_field)).all()
    if items:
        ordering=position+1
        for item in items:
            setattr(item, position_field, ordering)
            ordering = ordering + 1
        db.session.commit()  
        clean_items_routes(items, routes_cache_clean, reload_async=reload_async)
    if target:
        setattr(target, position_field, position)
        db.session.commit()  
        clean_items_routes([target], routes_cache_clean, reload_async=reload_async)
       
    clean_ordering(
        db, target_type, group_fields=group_fields, 
        position_field=position_field, routes_cache_clean=routes_cache_clean)

def clean_ordering(db, target_type, group_fields=None,
                   position_field="position", routes_cache_clean=None, reload_async=True):
    query = db.session.query(target_type)
    if group_fields is not None:
        for g in group_fields:
            query = query.filter(g[0]==g[1])
    items = query.order_by(getattr(target_type, position_field)).all()
    if items:
        ordering=0
        for item in items:
            setattr(item, position_field, ordering)
            ordering = ordering + 1
        db.session.commit() 
        clean_items_routes(items, routes_cache_clean, reload_async=reload_async)

def swap_with(db, target, target_type, direction, group_fields=None, 
              position_field="position", routes_cache_clean=None, reload_async=True):
    status = True
    try:
        query = db.session.query(target_type)    
        if group_fields is not None:
            for g in group_fields:
                query = query.filter(g[0]==g[1])
        if direction == 'up':
            query = query.filter(
                getattr(target_type, position_field)>getattr(
                    target, position_field)).order_by(
                getattr(target_type, position_field))
        else:
            if direction == 'down':
                query = query.filter(
                    getattr(target_type, position_field)<getattr(
                        target, position_field)).order_by(
                    getattr(target_type, position_field).desc())
            else:
                if direction == 'top':
                    query = query.order_by(
                        getattr(target_type, position_field))
                else:
                    query = query.order_by(
                        getattr(target_type, position_field).desc())
        swap = query.first()

        target_position = getattr(target, position_field)
        setattr(target, position_field, getattr(swap, position_field))
        setattr(swap, position_field, target_position)
        db.session.commit()
        clean_items_routes([target, swap], routes_cache_clean, reload_async=reload_async)
    except:
        status = False
    db.session.flush()
    clean_ordering(db, target_type, group_fields=group_fields, 
                   position_field=position_field, 
                   routes_cache_clean=routes_cache_clean)
    return status

def clean_items_routes(items, routes_cache_clean, reload_async=True): 
    if routes_cache_clean:
        for i in items:
            for f, params in routes_cache_clean:
                item_params = dict()
                for p in params:
                    item_params[p] = getattr(i, p)
                if reload_async:
                    reload_resource.delay(f, attr=item_params)
                else:
                    reload_resource(f, attr=item_params)
