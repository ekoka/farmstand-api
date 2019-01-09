import io
import itertools as itools
import uuid
import hashlib
import os
from PIL import Image as pilimage
from libthumbor import CryptoURL
from flask import g, current_app as app, url_for
from sqlalchemy import exc
from sqlalchemy.orm import exc as orm_exc

from b2bapi.db.models.images import SourceImage, BaseImage, ImageUtil
from b2bapi.db import db
from b2bapi.utils.uuid import clean_uuid
from b2bapi.utils.randomstr import randomstr

from ._route import route, url_for, json_abort, hal

@route('/source-images', methods=['POST'], expects_files=['image'],
       expects_tenant=True)
def post_source_image(tenant, image=None):
    #record = _get_source_image(image_id)
    # TODO: move this initialization inside POSTing of SourceImage
    source_file = image[0]
    config = app.config['IMAGE']
    try:
        source_image = ImageUtil(
            source_file, config=config, context='source')
        image_id = source_image.blob_signature
        try:
            record = _get_source_image(image_id)
        except:
            # exception was raised, meaning new record
            # hence new file
            source_image.save()
            srcimg_record = SourceImage(
                source_image_id=image_id,
                tenant_id=tenant['tenant_id'],
                meta=get_image_data(source_image),
            )

            # generate the main copy
            main_copy = source_image.thumbnail(config['WEB_MAX_LENGTH'],
                                            context='web')
            main_copy.save()
            main_base = BaseImage(
                tenant_id = tenant['tenant_id'],
                base_image_id = main_copy.blob_signature,
                meta = get_image_data(main_copy),
                source=srcimg_record,
            )
            set_aspect_ratios(main_base)
            
            db.session.add(srcimg_record)
            db.session.flush()
    except (IOError, TypeError) as e:
        db.session.rollback()
        raise
        #TODO: more elaborate message
        json_abort(405, {})

    rv = hal()
    rv._k('source_image_id', image_id)
    rv._k('image_id', main_base.base_image_id)
    rv._l('source_image', url_for('api.get_source_image', image_id=image_id))
    rv._l('image', url_for('api.get_image', image_id=main_base.base_image_id))
    
    return rv.document, 200, ()

@route('images', expects_tenant=True)
def get_images(tenant):
    rv = hal() 
    rv._l('self',url_for('api.get_images'))
    rv._embed('images', [hal()._k('image_id', i.base_image_id)
                ._l('self', url_for('api.get_image', image_id=i.base_image_id))
                .document
                for i in BaseImage.query.filter_by(
                    tenant_id=tenant['tenant_id']).all()]
    )
    return rv.document, 200, []


@route('/images/<image_id>', expects_tenant=True)
def get_image(image_id, tenant):
    try:
        image = BaseImage.query.get((image_id, tenant['tenant_id']))
    except orm_exc.NoResultFound as e:
        json_abort(404, {'error':'Image not Found'})
    thumbor_base = 'http://127.0.0.1:9001'
    aspect_ratios = {}
    crypto = CryptoURL(key='MY_SECURE_KEY')

    largest = 'width' if image.meta['width'] >= image.meta['height'] else 'height'
    try:
        for ar in itools.chain([{'name':'0:0'}], image.meta.get('aspect_ratios', [])):
            base_options = dict(image_url=image.meta['filename'])
            if ar['name']!='0:0':
                base_options['crop'] = ((ar['A'], ar['B']),(ar['C'], ar['D']))
            for size_name, size  in dict(
                large=0, medium=700, small=300, thumb=100).items():
                options = dict(**base_options)
                if size:
                    options[largest] = min(size, ar.get(largest, image.meta[largest]))
                url = crypto.generate(**options)
                aspect_ratios.setdefault(ar['name'], {})[size_name] = f'{thumbor_base}{url}'
    except Exception as e:
        app.logger.info(e)
        raise

    #image_url = crypto.generate(
    #    #width=300,
    #    #height=200,
    #    #smart=True,
    #    image_url=image.meta['filename']
    #)


    rv = hal() 
    rv._k('image_id', image_id)
    rv._l('self', url_for('api.get_image', image_id=image_id))
    rv._k('aspect_ratios', aspect_ratios)
    return rv.document, 200, []

# NOTE: might not be useful
@route('/source-images-meta', methods=['POST'], expects_data=True)
def post_source_image_meta(data):
    data = add_source_image.validate(data)
    src_img = SourceImage(**data)
    try:
        db.session.add(src_img)
        db.session.flush()
        image_id = src_img.source_image_id
    except orm_exc.IntegrityError:
        json_abort(400)

    rv = {
        "href": APIUrl('api.get_source_image', image_id=image_id),
        "contents": APIUrl('api.patch_source_image_contents', image_id=image_id)
    }
    redirect_url = APIUrl('api.get_source_image', image_id=image_id)
    return rv, 201, [('Location', redirect_url)]


def _get_source_image(image_id, tenant_id):
    try:
        if image_id is None:
            raise orm_exc.NoResultFound()
        return SourceImage.query.filter_by(
            source_image_id=image_id, tenant_id=tenant_id).one()
    except orm_exc.NoResultFound as e:
        json_abort(404, {'error':'Image not found'})

@route('/source-images/<image_id>', expects_tenant=True)
def get_source_image(image_id, tenant):
    record = _get_source_image(image_id, tenant['tenant_id'])
    return rv, 200, ()

def get_image_data(image):
    rv = dict(
        #original_name=image.original_name,
        format=image.image.format,
        extension=image.extension,
        width = image.image.width,
        height = image.image.height,
        filename = image.filename,
        filesize = image.filesize,
        filepath = image.filepath,
    )
    return rv

def crop_to_aspect_ratio(aspect_ratio, current):
    ar = [int(i) for i in aspect_ratio.split(':')]
    rv = dict(name=aspect_ratio)
    horizontal = current['width']>=current['height']
    target = {}
    # calculate the goal ratio 
    target_ratio = ar[0]/ar[1]

    if horizontal:
        width, height, a,b,c,d = 'width', 'height', 'A','B','C','D'
    # flip coordinates if vertical
    else:
        width, height, a,b,c,d = 'height', 'width', 'B','A','D','C'

    current_ratio = current[width]/current[height]

    crop = {}
    # calculate the difference to crop
    if target_ratio > current_ratio:
        # cropping height
        target[width] = current[width]
        target[height] = current[width]/target_ratio
        crop[a] = 0
        crop[b] = (current[height] - target[height])/2
        crop[c] = target[width]
        crop[d] = crop[b] + target[height]
    else: 
        # cropping width
        target[height] = current[height]
        target[width] = current[height] * target_ratio
        crop[a] = (current[width] - target[width])/2
        crop[b] = 0
        crop[c] = crop[a] + target[width]
        crop[d] = target[height]

    rv.update({k:int(round(float(v))) for k,v in crop.items()})
    rv[width] = int(round(target[width]))
    rv[height] = int(round(target[height]))

    rv['AxB'] = f'{rv[a]}x{rv[b]}'
    rv['CxD'] = f'{rv[c]}x{rv[d]}'
    rv['AxB:CxD'] = f'{rv["AxB"]}:{rv["CxD"]}'

    return rv


def set_aspect_ratios(base_image):
    aspect_ratios = ['1:1', '5:4', '4:3', '3:2', '16:9', '3:1']
    base_image.meta['aspect_ratios'] = [
        crop_to_aspect_ratio(ar, base_image.meta) for ar in aspect_ratios]

#def generate_main_image(source_image):
#    aspect_ratios = ['1:1', '5:4', '4:3', '3:2', '16:9', '3:1']
#    current = source_image.meta['web']
#    # calculate the current ratio
#    if current['orientation']=='horizontal':
#        width, height, a,b,c,d = 'width', 'height', 'a','b','c','d'
#    else:
#        width, height, a,b,c,d = 'height', 'width', 'b','a','d','c'
#
#    current_ratio = current[width]/current[height]
#
#    target = {}
#
#    # calculate the goal ratio 
#    target['ratio'] = ar[0]/ar[1]
#    crop = {}
#
#    # calculate the difference to crop
#    if target['ratio'] > current_ratio:
#        # cropping height
#        target[width] = current[width]
#        target[height] = current[width]/target['ratio']
#        #if current['orientation']=='horizontal':
#        #    crop['a'] = 0
#        #    crop['b'] = (current[height] = target[height])/2
#        #    crop['c'] = target[width]
#        #    crop['d'] = crop['b'] + target[height]
#        #else: 
#        #    crop['a'] = (current[height] = target[height])/2
#        #    crop['b'] = 0
#        #    crop['c'] = crop['a'] + target[height]
#        #    crop['d'] = target[width]
#
#        crop[a] = 0
#        crop[b] = (current[height] - target[height])/2
#        crop[c] = target[width]
#        crop[d] = crop[b] + target[height]
#    else: 
#        # cropping width
#        target[height] = current[height]
#        target[width] = current[height] * target['ratio']
#        crop[a] = (current[width] - target[width])/2
#        crop[b] = 0
#        crop[c] = crop[a] + target[width]
#        crop[d] = target[height]

    

    


#@route('/source-images/<image_id>/contents', methods=['PATCH'], 
#       expects_files=['image'])
#def patch_source_image_contents(image_id, image=None):
#    record = _get_source_image(image_id)
#    # TODO: move this initialization inside POSTing of SourceImage
#    source_file = image[0]
#    config = app.config['IMAGE']
#    try:
#        source_image = ImageUtil(
#            source_file, config=config, context='source')
#        web_image = source_image.thumbnail(config['WEB_MAX_LENGTH'],
#                                           context='web')
#        source_image.save()
#        web_image.save()
#        record.meta = get_image_data(source_image, web_image)
#        db.session.flush()
#    except (IOError, TypeError) as e:
#        #TODO: more elaborate message
#        json_abort(400)
#    rv = {
#        'status': APIUrl('api.get_source_image_contents', image_id=image_id)
#    }
#    return rv, 200, ()

