from slugify import slugify
from sqlalchemy import or_
from werkzeug.exceptions import (Conflict)
from ccaapi.api.caches.slugs import _clean_cache_put

def unique_slug(db, target_type, slug, target=None, id_field=None, rtype=None):
    r = db.session.query(target_type).filter(\
            or_(target_type.slug_fr==slug, target_type.slug_en==slug)\
        ).first()
    if r and getattr(r, id_field)!=getattr(target, id_field):
        raise Conflict(description=u'Another item already exists with that slug')

    if rtype:
        _clean_cache_put(rtype, slug)
    return slug

def sanitize_slug(db, target_type, slug, fallback=None, target=None, id_field=None, rtype=None):
    slug = slugify(slug) if slug else slugify(fallback) if fallback else ""
    return unique_slug(db, target_type, slug, target, id_field, rtype=rtype)
