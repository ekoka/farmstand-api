from .routes.routing import api_url, json_abort, hal
from ..service import images as img_srv
from .utils import run_or_abort

def post_source_image(domain, image=None):
    # api
    try:
        source_file = image[0]
    except IndexError:
        json_abort(400, {'error': 'No file uploaded'})
    source_image_fnc = lambda: img_srv.save_source_image(domain.domain_id, source_file)
    source_image_record = run_or_abort(source_image_fnc)
    main_image_fnc = lambda: img_srv.generate_main_copy(source_image_record)
    main_image_record = run_or_abort(main_image_fnc)
    rv = hal()
    source_image_id = source_image_record.image_id
    base_image_id = main_image_record.base_image_id
    rv._k('source_image_id', source_image_id)
    #rv._l('source_image', api_url('api.get_source_image', image_id=image_id))
    if main_image_record:
        rv._k('image_id', base_image_id)
        rv._l('image', api_url('api.get_image', image_id=base_image_id))
    return rv.document, 200, ()

def get_images(domain, params):
    # api
    fnc = lambda: img_srv.get_images(domain.domain_id)
    images = run_or_abort(fnc)
    rv = hal()
    rv._l('self',api_url('api.get_images', **params))
    image_collection = [_image_resource(img, **params).document for img in images]
    rv._embed('images', image_collection)
    return rv.document, 200, []

def _image_resource(image, **params):
    # api
    try:
        aspect_ratios = img_srv.get_aspect_ratios(image, params)
    except:
        aspect_ratios = None
    rv = hal()
    rv._k('image_id', image.base_image_id)
    rv._l('self', api_url('api.get_image', image_id=image.base_image_id))
    rv._k('aspect_ratios', aspect_ratios)
    return rv

def get_image(image_id, domain):
    # api
    fnc = lambda: img_srv.get_image(imageid, domain_id)
    image = run_or_abort(fnc)
    rv = _image_resource(image)
    return rv.document, 200, []

def get_product_images(product_id, domain, params):
    # api
    fnc = lambda: img_srv.get_product_images(product_id, domain.domain_id)
    product_images = run_or_abort(fnc)
    rv = hal()
    rv._l('self', api_url('api.get_product_images', product_id=product_id))
    images = [_image_resource(pi.image).document for pi in product_images]
    rv._embed('images', images)
    return rv.document, 200, []

def put_product_images(product_id, domain, data):
    # api
    fnc = lambda: img_srv.update_product_images(product_id, domain.domain_id, data)
    run_or_abort(fnc)
    return {}, 200, []

# NOTE: might not be useful
def post_source_image_meta(data):
    # api
    fnc = lambda: img_srv.save_source_image_data(data)
    source_image = run_or_abort(fnc)
    image_id = source_image.source_image_id
    rv = {
        "href": api_url('api.get_source_image', image_id=image_id),
        "contents": api_url('api.patch_source_image_contents', image_id=image_id)
    }
    redirect_url = api_url('api.get_source_image', image_id=image_id)
    return rv, 201, [('Location', redirect_url)]
