import math
from decimal import Decimal as dec
from werkzeug.exceptions import (Unauthorized, NotFound, Forbidden, 
                                PreconditionFailed, BadRequest, Conflict)
from sqlalchemy import or_
from ccaapi.api import APIUrl, api_call
from ccaapi.db.models import unaccent
    
def paging(params, url, query, resource, default_ordering_key, 
        default_ordering_dir="asc", search_params=None):
    metadata = dict()
    next_page = None
    page = int(params.get('page', 0))
    search = params.get('search', None)
    page_size = int(params.get('page_size', 20))
    ordering = params.get('ordering', None)
    ordering_column = params.get('ordering_column', None)
    previous_page=None
    next_page=None
    first_page=None
    last_page=None
    total_count = query.count()
    filtered_count = None
   
    if ordering_column:
        ordering_column = getattr(resource, ordering_column)
    else:
        ordering_column = default_ordering_key
    
    if not ordering:
        ordering = default_ordering_dir
    if ordering=='asc':
        query = query.order_by(ordering_column)
    elif ordering=='desc':
        query = query.order_by(ordering_column.desc())
    
    if search and search_params:
        conditions = []
        for sp in search_params:
            if not isinstance(sp, tuple):
                conditions.append(unaccent(sp).ilike("%"+unaccent(search)+"%"))
            else:
                conditions.append(sp[1][0].in_(sp[1][1].filter(unaccent(sp[0])\
                          .ilike("%"+unaccent(search)+"%")).subquery()))

        extra_conditions = []
        exploded_search = search.split("+")
        for s in exploded_search:
            if s.strip():
                for sp in search_params:
                    if not isinstance(sp, tuple):
                        extra_conditions.append(unaccent(sp).ilike(
                            "%"+unaccent(s.strip())+"%"))
                    else:
                        extra_conditions.append(sp[1][0].in_(sp[1][1].filter(
                            unaccent(sp[0]).ilike(
                                "%"+unaccent(s.strip())+"%")).subquery()))
        if conditions:
            query = query.filter(
                or_(*(conditions+extra_conditions)))
    
    filtered_count = query.count()
    nb_of_page = int(math.ceil(dec(filtered_count) / dec(page_size)))-1
    if nb_of_page < 0: 
        nb_of_page = 0
        
    if page_size > 0 and page_size <= 100:
        if page_size <= filtered_count:
            if page > nb_of_page and filtered_count > 0:
                raise NotFound('The requested page does not exist (paging)')
            query = query.limit(page_size)
            if page >= 0:
                query = query.offset(page*page_size)
            else: raise BadRequest('Invalid page number (paging)')   
            first_page = APIUrl(url, page=0, page_size=page_size, 
                                ordering=ordering, **_get_clean_args(params))
            if page < nb_of_page:
                next_page = APIUrl(
                    url, page=page+1, page_size=page_size, ordering=ordering,
                    **_get_clean_args(params))
            if page > 0:
                previous_page = APIUrl(
                    url, page=page-1, page_size=page_size, ordering=ordering,
                    **_get_clean_args(params))
            last_page = APIUrl(
                    url, page=nb_of_page, page_size=page_size, 
                    ordering=ordering, **_get_clean_args(params))  
        elif page > nb_of_page:
            raise NotFound('The requested page does not exist (paging)')         
    else: raise BadRequest('Invalid page size. Page size must be between 1 '
                           'and 100 (paging)') 
    
    self=APIUrl(url, page=page, page_size=page_size, ordering=ordering,
                **_get_clean_args(params))

    link = "<" + str(self) + ">;rel=self"
    if first_page and previous_page:
        link += ",<" + str(first_page) + ">;rel=first"
    if previous_page: 
        link += ",<" + str(previous_page) + ">;rel=previous"
    if next_page:
        link += ",<" + str(next_page) + ">;rel=next"
    if last_page and next_page:
        link += ",<" + str(last_page) + ">;rel=last"    
    
    headers = {
        'Link':link,
        'Total-Count':total_count,
        'Total-Filtered-Count':filtered_count,
        'Paging-Current-Page':page + 1,
        'Paging-Total-Page':nb_of_page + 1,
    }

    if params.get('_embed_paging'):
        metadata = dict(
            _paging = dict(
                page=page,
                page_size=page_size,
                ordering=ordering,
                total_count=total_count,
                filtered_count=filtered_count,
                next_page=next_page,
                previous_page=previous_page,
                first_page=first_page,
                last_page=last_page,
                self=self,
                total_page=nb_of_page + 1,
                current_page=page + 1
            )
        )
    
    return query, headers, metadata

def _get_clean_args(args):
    clean_args = dict(**args)
    clean_args.pop("page", None)
    clean_args.pop("page_size", None)
    clean_args.pop("ordering", None)
    return clean_args
